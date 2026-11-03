import re

from llama_index.core import PromptTemplate, QueryBundle
from llama_index.llms.google_genai import GoogleGenAI

from common import get_index

NO_ANSWER = "[NO_ANSWER]"
FOLLOW_UPS = "FOLLOW_UPS:"
TOP_K = 8  # כמה קטעים נשלחים למודל: יותר קטעים נותנים תשובה מלאה ועשירה יותר

index = get_index()

# שלב 7 - אחזור (retrieval)
retriever = index.as_retriever(similarity_top_k=TOP_K)

# שלב 8 - יצירת תשובה עם Gemini
# טמפרטורה בינונית: תשובות מגוונות בין שאלה לשאלה (ואותה שאלה לא תחזור זהה מילה במילה)
llm = GoogleGenAI(model="gemini-3.1-flash-lite", temperature=0.6)

prompt = PromptTemplate(
    "You are a friendly guide to NASA missions.\n"
    "Answer the question using ONLY the information below. Do not use outside knowledge.\n"
    "Never mention the information, text, documents, context or sources you were given, "
    "and never say 'provided' or 'according to'. Never write phrases such as 'the information "
    "I have', 'המידע שבידי', 'המידע מציין' or 'לא מצוין'. Answer as if you simply know.\n"
    "If part of the question cannot be answered, say so in the first person, in the "
    "language of the question: for an English question write 'I don't have information "
    "about X'; for a Hebrew question write 'אין לי מידע על X'. Never say that "
    "'the information does not mention' or 'the text does not state'.\n"
    "If the question refers to 'the company', 'the agency' or 'the organization' without "
    "naming it, it means NASA.\n"
    "Write a rich, vivid and well-explained answer that enriches the reader's knowledge. "
    "Format it beautifully in Markdown: open with a short catchy title line (### followed by a "
    "fitting emoji), then one clear sentence that answers the question directly, then 2 or 3 "
    "short sections with ### sub-headings or bullet points that explain the key ideas step by "
    "step with names, dates and numbers. Include one line that starts with '✨ הידעת?' (for a "
    "Hebrew question) or '✨ Did you know?' (for an English question) with a surprising fact "
    "from the information, and end with one short inviting sentence that makes the reader "
    "curious to ask more. Use emojis sparingly (about 3 to 6 in total) and Markdown **bold** "
    "for key terms, with a warm storytelling tone. Explain terms only the way the information "
    "explains them, and never add facts from your own knowledge. "
    "Length: 200 to 350 words. Even for a simple question, give the direct answer first and "
    "then enrich it with the surrounding context from the information. "
    "Tailor the answer to exactly what was asked, and vary your style: do not always open "
    "the same way, change the structure (a story, a short list, a comparison), and highlight "
    "different interesting details each time. "
    "In Hebrew, never address the reader with gendered second-person verbs or pronouns "
    "(no 'תרצה', 'תרצי', 'אתה', 'את', 'תוכל'); use plural or impersonal phrasing instead, "
    "such as 'רוצים לשמוע עוד על...?' or 'אפשר להרחיב על...'.\n"
    "If the question contains several questions (one per line), answer each one separately "
    "and in order. Give each answer its own short, descriptive ### heading written in your own "
    "words, with a fitting emoji, and never use numbers in headings. Keep each answer to about "
    "100 to 180 words, and write the '✨' fact and FOLLOW_UPS only once, at the very end.\n"
    "The '✨' fact must be about the very thing the user asked about, and match what they "
    "wanted to learn: for a question about founding or history, a fact about that history; for "
    "a question about a mission, a fact about that mission; for a question about a person, a "
    "fact about that person. Never use a fact about a different subject, even if it is "
    "interesting. Never use the origin or meaning of a word, a definition, or a general fact "
    "about astronauts or NASA as the '✨' fact; it must be a concrete event, record, date, "
    "number or name that belongs to the topic of the question itself (for a question about "
    "whether people fly to space today: a current mission, crew or record). If the information has no surprising fact on that exact topic, leave the "
    "'✨' line out completely.\n"
    "After the answer, on a new line, write FOLLOW_UPS: followed by 2 or 3 short follow-up "
    "questions that a curious reader might ask next, separated by ' | '. Every follow-up "
    "must be answerable from the information below and written in the language of the "
    "question. Do not write FOLLOW_UPS when you reply with [NO_ANSWER].\n"
    "If the information does not contain the answer, reply with exactly the token "
    "[NO_ANSWER] and nothing else.\n\n"
    "Information:\n{context_str}\n\n"
    "Question: {query_str}\n\n"
    "IMPORTANT: Write your answer in the same language as the question above "
    "(Hebrew question -> Hebrew answer, English question -> English answer), "
    "even if the information is in another language.\n"
    "Answer:"
)

query_engine = index.as_query_engine(
    llm=llm, similarity_top_k=TOP_K, text_qa_template=prompt
)

# מודל נפרד להבנת ההקשר: טמפרטורה 0, כי כאן צריך תוצאה יציבה ולא יצירתית
planner_llm = GoogleGenAI(model="gemini-3.1-flash-lite", temperature=0)

PLAN_PROMPT = (
    "Below is the end of a conversation between a user and an assistant about NASA.\n\n"
    "{conversation}\n\n"
    "The user's latest message: {question}\n\n"
    "Rewrite the latest message as a list of standalone questions, one per line, so that each "
    "question is fully understandable without reading the conversation.\n"
    "- If the message contains several questions, split them (at most 3).\n"
    "- If the message begins with an agreement such as 'כן', 'בטח', 'yes' or 'sure' (a reply to "
    "the assistant's closing offer or question), add one question that asks for what the "
    "assistant offered, written as a direct question, and keep any other question from the "
    "message. Put the explicit question from the message first.\n"
    "- If the message is only an agreement, return just the question for what the assistant "
    "offered.\n"
    "- 'the company', 'the agency' or 'the organization' without a name means NASA.\n"
    "- Write the questions in the language of the message. If the message is already a single "
    "standalone question, return it unchanged.\n"
    "Return only the questions, one per line, with no numbering and no explanations."
)
AFFIRMATIONS = ("כן", "בטח", "ברור", "בהחלט", "אשמח", "yes", "sure", "ok", "okay", "please")
# מילים שמפנות אחורה בשיחה ("הוא", "שם", "זה"): בלי ההקשר אי אפשר לחפש לפיהן במאגר
REFERENCE_WORDS = {
    "הוא", "היא", "הם", "הן", "זה", "זאת", "זו", "שם", "אותו", "אותה", "אותם", "בו", "בה",
    "שלו", "שלה", "שלהם", "לו", "לה", "אז", "הזה", "הזאת", "ההיא", "ההוא",
    "he", "she", "it", "they", "there", "that", "this", "his", "her", "its", "their", "him", "them",
}
MULTI_WORDS = (" וגם ", " ובנוסף ", " and also ")


# שלב 9 - הצגת מקורות
def read_header(file_name):
    with open(f"data/{file_name}", encoding="utf-8") as f:
        title = f.readline().strip()
        url = f.readline().replace("Source:", "").strip()
    return title, url


def clean_excerpt(text, limit=600):
    lines = [ln for ln in text.splitlines() if not ln.startswith("Source:")]
    flat = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return flat if len(flat) <= limit else flat[:limit].rsplit(" ", 1)[0] + "…"


def build_sources(nodes):
    sources = []
    for node in nodes:
        title, url = read_header(node.node.metadata["file_name"])
        sources.append(
            {
                "title": title,
                "url": url,
                "score": node.score,
                "excerpt": clean_excerpt(node.node.text),
            }
        )
    return sources


# שלב 11 - פיצול לשני שלבים כדי שהממשק יציג כל אחד בנפרד
def search(q):
    """שלב א: מוצא את הקטעים הקרובים ביותר לשאלה."""
    return retriever.retrieve(q)


NO_INFO_STARTS = ("אין לי מידע", "I don't have information")


def is_no_answer(text):
    """תשובה ריקה מתוכן: הסימון הקבוע, או משפט קצר שפותח ב"אין לי מידע" (הניסוח שהפרומפט מכתיב)."""
    if text.startswith(NO_ANSWER):
        return True
    return len(text) < 200 and text.startswith(NO_INFO_STARTS)


def split_followups(text):
    """מפריד את שורת ההצעות להמשך (FOLLOW_UPS) מגוף התשובה."""
    if FOLLOW_UPS not in text:
        return text.strip(), []
    body, _, tail = text.partition(FOLLOW_UPS)
    followups = [f.strip(" -*•\n") for f in tail.split("|")]
    return body.strip(), [f for f in followups if 5 < len(f) < 160][:3]


def needs_planning(history, question):
    """האם ההודעה דורשת הבנת הקשר: כמה שאלות בהודעה אחת, או הודעת המשך ("כן", הודעה קצרה)."""
    q = question.strip()
    multi = q.count("?") + q.count("؟") >= 2 or any(w in f" {q} " for w in MULTI_WORDS)
    first_word = re.split(r"[\s,.!?]+", q.lower(), maxsplit=1)[0]
    words = set(re.split(r"[\s,.!?\"']+", q.lower()))
    words |= {w[1:] for w in words if w.startswith("ו") and len(w) > 2}
    refers_back = bool(words & REFERENCE_WORDS)
    follow_up = bool(history) and (
        first_word in AFFIRMATIONS or len(q.split()) <= 4 or refers_back
    )
    return multi or follow_up


def plan_questions(history, question):
    """מחזיר רשימת שאלות עצמאיות: מפצל הודעה עם כמה שאלות ומפענח "כן" לפי השיחה."""
    if not needs_planning(history, question):
        return [question]
    conversation = "\n".join(
        ("User: " if m["role"] == "user" else "Assistant: ") + m["text"][-700:]
        for m in (history or [])[-4:]
    ) or "(no previous conversation)"
    try:
        raw = str(
            planner_llm.complete(
                PLAN_PROMPT.format(conversation=conversation, question=question)
            )
        )
    except Exception:
        return [question]
    lines = [re.sub(r"^[\s\-\*\d\.\)]+", "", ln).strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if len(ln) > 3][:3]
    return lines or [question]


def search_many(questions):
    """מחפש לכל שאלה בנפרד ומאחד את הקטעים, ושומר לכל קטע את הציון הגבוה ביותר."""
    best = {}
    for q in questions:
        for node in retriever.retrieve(q):
            key = node.node.node_id
            if key not in best or (node.score or 0) > (best[key].score or 0):
                best[key] = node
    nodes = sorted(best.values(), key=lambda n: n.score or 0, reverse=True)
    return nodes[: TOP_K + 2 * (len(questions) - 1)]


def compose_text(questions):
    """הטקסט שנשלח למודל: שאלה אחת כמות שהיא, או רשימה ממוספרת של שאלות."""
    if len(questions) == 1:
        return questions[0]
    # בלי הקדמה באנגלית (כדי שהמודל יענה בשפת השאלות) ובלי מספור (כדי שלא יעתיק מספרים לכותרות)
    return "\n".join(questions)


LEAK_PHRASES = re.compile(
    r"(המידע( שבידי)? (מציין|מראה|מצביע על)|על פי המידע|לפי המידע|בהתאם למידע)[,:]?\s*(כי\s+|ש)?"
)


def strip_leaks(text):
    """רשת ביטחון: מוחק ניסוחים שחושפים שיש "מידע" שנשלח למודל, גם אם הוא התעלם מהפרומפט."""
    return LEAK_PHRASES.sub("", text)


def compose_answer(q, nodes):
    """שלב ב: מנסח תשובה מהקטעים. מחזיר (טקסט, האם נמצאה תשובה, הצעות להמשך)."""
    response = query_engine.synthesize(QueryBundle(q), nodes)
    text = str(response).strip()
    if is_no_answer(text):
        return "", False, []
    text, followups = split_followups(strip_leaks(text))
    return text, True, followups


def is_hebrew(text):
    return any("֐" <= ch <= "׿" for ch in text)


def no_answer_text(q):
    """הודעה קבועה וקצרה בשפת השאלה, כשאין במאגר תשובה. לא משתמשים בטקסט של המודל כדי שלא יחשוף פרטים פנימיים."""
    if is_hebrew(q):
        return "אין לי מידע על זה. אפשר לנסח את השאלה אחרת, או לשאול על משימות, חלליות וגילויים של NASA."
    return "I don't have information on that. Try rephrasing, or ask about NASA missions, spacecraft and discoveries."


def answer_question(q):
    nodes = search(q)
    text, found, _ = compose_answer(q, nodes)
    if not found:
        text = no_answer_text(q)
    return text, build_sources(nodes)


def show_retrieval(q):
    print("\nשאלה:", q)
    for result in search(q):
        text = result.node.text[:120].replace("\n", " ")
        print(round(result.score, 3), result.node.metadata["file_name"], "|", text)


def ask(q):
    answer, sources = answer_question(q)
    print("\nשאלה:", q)
    print(answer)
    print("\nמקורות:")
    for i, s in enumerate(sources, 1):
        print(f"{i}. {s['title']} | {s['url']} | דמיון {s['score']:.2f}")


if __name__ == "__main__":
    questions = [
        "מי היה האדם הראשון על הירח?",
        "Who was the first person to walk on the Moon?",
    ]
    for q in questions:
        ask(q)
