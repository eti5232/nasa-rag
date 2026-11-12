# שלב 11 - ממשק Chainlit
import chainlit as cl

from guards import answer_style, image_note, is_hebrew, system_reply
from query import (
    compose_answer,
    compose_text,
    no_answer_text,
    plan_questions,
    search_many,
)

STARTERS = [
    (
        "מה קרה באפולו 13?",
        "https://www.nasa.gov/wp-content/uploads/2022/05/Aldrin_Apollo_11-1.jpeg",
    ),
    (
        "מה המטרה של תוכנית ארטמיס?",
        "https://www.nasa.gov/wp-content/uploads/2022/12/art002e021110large.jpg",
    ),
    (
        "מה ידוע על מאדים?",
        "https://assets.science.nasa.gov/content/dam/science/psd/mars/resources/detail_files/7/7668_Mars-viking-2-orbiter-global-view-partial-valles-marinares-PIA04304-full2.jpg/jcr:content/renditions/cq5dam.web.1280.1280.jpeg",
    ),
    (
        "What makes the Voyager spacecraft special?",
        "https://science.nasa.gov/wp-content/uploads/2023/12/voyager-banner-blue.jpg",
    ),
]

# שאלות שמוצעות כשאין תשובה במאגר
FALLBACK_QUESTIONS = ["מה קרה באפולו 13?", "מה ידוע על מאדים?"]


@cl.set_starters
async def set_starters():
    return [cl.Starter(label=q, message=q, icon=icon) for q, icon in STARTERS]


def no_answer_message(question):
    heading = "### לא מצאתי תשובה" if is_hebrew(question) else "### No answer found"
    return f"{heading}\n{no_answer_text(question)}"


def is_rate_limit(error):
    text = f"{type(error).__name__} {error}".lower()
    markers = ("429", "resource_exhausted", "503", "unavailable", "timeout")
    return any(m in text for m in markers)


async def send_error(question, error):
    if is_rate_limit(error):
        content = (
            "### הגענו למגבלת השימוש\n"
            "מודל השפה הגיע כרגע למכסה החינמית שלו. המכסה מתאפסת בדרך כלל תוך דקה "
            "עד כמה דקות. השאלה נשמרה, ואפשר לנסות שוב בעוד רגע."
        )
    else:
        content = (
            "### משהו השתבש\n"
            "האחזור או ניסוח התשובה נכשלו. לרוב זו תקלה זמנית, ושליחה מחדש פותרת אותה."
        )
    await cl.Message(
        content=content,
        actions=[
            cl.Action(
                name="retry", payload={"question": question}, label="נסו שוב"
            )
        ],
    ).send()


def remember(question, answer):
    """שומר את הסיבוב האחרון בשיחה, כדי שהודעת המשך כמו "כן" תובן."""
    history = cl.user_session.get("history") or []
    history += [
        {"role": "user", "text": question},
        {"role": "assistant", "text": answer},
    ]
    cl.user_session.set("history", history[-8:])


async def respond(question):
    history = cl.user_session.get("history") or []
    reply = system_reply(question)
    if reply:
        remember(question, reply)
        await cl.Message(
            content=reply,
            actions=[
                cl.Action(name="example", payload={"question": q}, label=q)
                for q in FALLBACK_QUESTIONS
            ],
        ).send()
        return
    try:
        questions = await cl.make_async(plan_questions)(history, question)
        if questions != [question]:
            async with cl.Step(name="הבנת ההקשר", type="tool") as step:
                step.input = question
                step.output = "\n".join(f"{i}. {q}" for i, q in enumerate(questions, 1))

        async with cl.Step(name="חיפוש במאגר", type="retrieval") as step:
            step.input = " | ".join(questions)
            nodes = await cl.make_async(search_many)(questions)
            step.output = f"נמצאו {len(nodes)} קטעים רלוונטיים"

        async with cl.Step(name="ניסוח תשובה", type="llm") as step:
            text, found, followups = await cl.make_async(compose_answer)(
                compose_text(questions), nodes, answer_style(question)
            )
            step.output = "התשובה נוסחה מהקטעים שנמצאו"
    except Exception as error:
        await send_error(question, error)
        return

    remember(question, text if found else no_answer_text(question))
    if found:
        await cl.Message(
            content=image_note(question) + text,
            actions=[
                cl.Action(name="example", payload={"question": q}, label=q)
                for q in followups
            ],
        ).send()
    else:
        await cl.Message(
            content=no_answer_message(question),
            actions=[
                cl.Action(name="example", payload={"question": q}, label=q)
                for q in FALLBACK_QUESTIONS
            ],
        ).send()


@cl.on_message
async def main(message: cl.Message):
    await respond(message.content)


@cl.action_callback("retry")
async def on_retry(action: cl.Action):
    await respond(action.payload["question"])


@cl.action_callback("example")
async def on_example(action: cl.Action):
    question = action.payload["question"]
    await cl.Message(content=question, type="user_message").send()
    await respond(question)
