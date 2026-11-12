# שכבת הגנות: בדיקות פשוטות בקוד, בלי מודל ובלי חיפוש במאגר.
# הן עוסקות במה שהמודל לא מצליח לעשות באופן אמין לבד: לא לחשוף פרטים פנימיים,
# לכבד בקשות אורך, ולהודות במה שהצ'אט לא יכול לעשות.
import re


def is_hebrew(text):
    return any("֐" <= ch <= "׿" for ch in text)


# שאלות על הצ'אט עצמו: עונים בטקסט קבוע, כי מודל שמתאר את הידע שלו חושף שיש לו "מידע" ו"מסמכים",
# ולפרטים טכניים (מפתחות, הוראות) אסור לענות בכלל
SECRET_WORDS = re.compile(r"\bapi\b|\bkey\b|מפתח|סיסמ|פרומפט|\bprompt\b|טוקן|\btoken\b", re.I)
ABOUT_BOT = re.compile(r"אתה|אתם|שלך|אותך|שלכם|\byou\b|\byour\b", re.I)
CREATOR_QUESTION = re.compile(
    r"מי (יצר|בנה|פיתח|כתב|תכנת|עשה) (אותך|אתכם)|מי אתה\b|מי אתם\b|איזה מודל (אתה|אתם|שפה|בינה)|"
    r"(מי|מיהו|מיהי|מיהם).{0,40}(יצר|בנה|פיתח|כתב|תכנת|עשה|לכתוב|לבנות|לפתח|ליצור).{0,20}"
    r"(ה?צ'אט|ה?בוט|ה?אתר הזה|ה?אפליקציה הזאת)|(ה?צ'אט|ה?בוט) (הזה|הזאת)? ?(נכתב|נוצר|נבנה|פותח) על ידי|"
    r"\bwho (made|created|built|developed|wrote|programmed) (you|this (chat|chatbot|bot|app|system|website))\b|"
    r"\bwho are you\b|\bwhich model (are|do) you\b",
    re.I,
)
CAPABILITY_QUESTION = re.compile(
    r"מה אתה (יודע|יכול)|על מה (אפשר|ניתן|אני יכול|אני יכולה) לשאול|לא תדע|לא תוכל לענות|"
    r"\bwhat (can|do) you (know|do)\b|\bwhat can i ask\b|\bwhat (questions )?(won't|can't|couldn't) you\b",
    re.I,
)
# שאלה על הקלטה בקול (המשתמשת רוצה להקליט, לא שואלת על הקלטות של משימות): קצרה, בלי מושא ("להקליט את ה...")
RECORDING_QUESTION = re.compile(
    r"(אפשר|ניתן|אני רוצה|רוצה|יש אפשרות).{0,30}(להקליט(?! את )|הקלטה|לדבר|בקול)|מיקרופון|"
    r"\bcan i (record|speak|talk|use (my )?(voice|microphone))\b|\bvoice input\b|\bmicrophone\b",
    re.I,
)
# ניסיון לשנות את התנהגות הצ'אט או להכתיב לו מה לכתוב
OVERRIDE_ATTEMPT = re.compile(
    r"תכתוב לי (בתשובה )?את המילים|תגיד לי את המילים|תחזור אחרי|תעשה מה ש(אני|אנחנו) (אומר|אומרת)|"
    r"התעלם מ(כל )?ה?(הוראות|כללים)|שכח (את )?ה?הוראות|"
    r"\brepeat after me\b|\bignore (all |the )?(previous|above|your) (instructions|rules)\b|"
    r"\bforget your instructions\b",
    re.I,
)
SYSTEM_REPLIES = {
    "secret": (
        "אין לי אפשרות לשתף פרטים טכניים פנימיים כמו מפתחות, הגדרות או הוראות. "
        "אפשר לשאול אותי על משימות, חלליות, אסטרונאוטים וגילויים של NASA.",
        "I can't share internal technical details such as keys, settings or instructions. "
        "You can ask me about NASA missions, spacecraft, astronauts and discoveries.",
    ),
    "creator": (
        "אני צ'אט לימודי שעונה על שאלות על NASA. זה פרויקט עצמאי של סטודנטית, ולא מוצר רשמי של NASA. "
        "אפשר לשאול אותי על משימות, חלליות, אסטרונאוטים וגילויים.",
        "I'm an educational chat that answers questions about NASA. This is an independent student "
        "project, not an official NASA product. Ask me about missions, spacecraft, astronauts and discoveries.",
    ),
    "capability": (
        "אפשר לשאול אותי על משימות וחלליות (אפולו, ארטמיס, וויאג'ר, האבל, ווב), אסטרונאוטים, "
        "תחנת החלל הבינלאומית, מאדים, הירח, מערכת השמש וההיסטוריה של NASA. "
        "שאלות על נושאים אחרים אני לא יכול לענות.",
        "You can ask me about missions and spacecraft (Apollo, Artemis, Voyager, Hubble, Webb), astronauts, "
        "the International Space Station, Mars, the Moon, the solar system and NASA's history. "
        "I can't answer questions about other topics.",
    ),
    "recording": (
        "יש כפתור מיקרופון בתיבת השאלה, משמאל לחץ השליחה. לוחצים עליו, מדברים, ולוחצים שוב כדי לעצור. "
        "הכפתור שלידו מחליף בין עברית לאנגלית. ההקלטה עובדת ב-Chrome וב-Edge.",
        "There is a microphone button inside the question box, to the left of the send arrow. Click it, "
        "speak, and click again to stop. The button next to it switches between Hebrew and English. "
        "Recording works in Chrome and Edge.",
    ),
    "override": (
        "אפשר לשאול אותי רק שאלות על NASA, למשל על משימות, חלליות, אסטרונאוטים וגילויים.",
        "You can only ask me questions about NASA, for example about missions, spacecraft, astronauts and discoveries.",
    ),
}


def system_reply(q):
    """אם ההודעה היא על הצ'אט עצמו מחזיר תשובה קבועה בשפת ההודעה, אחרת None."""
    if OVERRIDE_ATTEMPT.search(q):
        kind = "override"
    elif SECRET_WORDS.search(q) and ABOUT_BOT.search(q):
        kind = "secret"
    elif CREATOR_QUESTION.search(q):
        kind = "creator"
    elif CAPABILITY_QUESTION.search(q):
        kind = "capability"
    elif RECORDING_QUESTION.search(q) and len(q.split()) <= 10:
        kind = "recording"
    else:
        return None
    he, en = SYSTEM_REPLIES[kind]
    return he if is_hebrew(q) else en


# בקשה לתמונה או לסרטון: הצ'אט מציג טקסט בלבד, ולכן אומרים זאת בפתיחת התשובה
IMAGE_REQUEST = re.compile(r"תמונה|תמונות|סרטון|סרטונים|צילום של|\b(photo|photos|picture|pictures|image|images|video|videos)\b", re.I)


def image_note(q):
    if not IMAGE_REQUEST.search(q):
        return ""
    if is_hebrew(q):
        return "אין לי אפשרות להציג תמונות או סרטונים, אבל הנה מה שאפשר לספר:\n\n"
    return "I can't show images or videos, but here is what I can tell you:\n\n"


# בקשות לאורך או לצורת תשובה ("תענה קצר", "כן או לא", "בת 3 מילים"): הפרומפט הרגיל דורש תשובה
# עשירה של 200 מילים, ולכן את הבקשה מזהים בקוד ומעבירים למודל פרומפט קצר נפרד
NUMBER_WORDS = {
    "אחת": 1, "אחד": 1, "שתי": 2, "שתיים": 2, "שני": 2, "שלוש": 3, "שלושה": 3, "ארבע": 4,
    "ארבעה": 4, "חמש": 5, "חמישה": 5, "שש": 6, "שישה": 6, "שבע": 7, "שמונה": 8, "תשע": 9,
    "עשר": 10, "עשרה": 10,
}
YES_NO_REQUEST = re.compile(
    r"כן או לא|בכן ו?לא|בכן בלבד|תענה (לי )?בכן|\byes (or|/) ?no\b|\banswer (with )?(only )?(yes|no)\b",
    re.I,
)
WORDS_REQUEST = re.compile(
    r"(\d+|" + "|".join(NUMBER_WORDS) + r")\s*(?:מילים|מילה|words?)\b", re.I
)
SHORT_REQUEST = re.compile(
    r"תענה (לי )?(קצר|בקצרה)|ענה (לי )?(קצר|בקצרה)|תשובה קצרה|בקצרה|תמציתי|בתמצית|ענייני|עניני|"
    r"בשורה אחת|משפט אחד|\bbriefly\b|\bshort answer\b|\bin one sentence\b|\bin short\b|"
    r"\bconcise(ly)?\b|\bto the point\b|\bquickly\b",
    re.I,
)
SHORT_WORD_LIMIT = 40


def answer_style(q):
    """מחזיר None לתשובה רגילה, או (סוג, מגבלת מילים) כשהמשתמשת ביקשה תשובה קצרה."""
    if YES_NO_REQUEST.search(q):
        return ("yes_no", 1)
    m = WORDS_REQUEST.search(q)
    if m:
        raw = m.group(1)
        n = int(raw) if raw.isdigit() else NUMBER_WORDS[raw]
        return ("words", max(1, n))
    if SHORT_REQUEST.search(q):
        return ("short", SHORT_WORD_LIMIT)
    return None


# ניסוחים שמעידים שהמודל מדבר על "המידע/הטקסט" שקיבל. הרשימה מורחבת בכל פעם שנמצא ניסוח חדש בצ'אט
STRONG_LEAKS = re.compile(
    r"שסופק|שסופקו|שניתנו|שניתן לי|במסמכים|המסמכים|בטקסט|מקורות המידע|במקורות (המידע|שסופקו|שניתנו|הקיימים|שבידי)|"
    r"המידע (הקיים|הזמין|שבידי|שלי|מכסה|מתמקד|מציין|מראה|מצביע|מפרט|אינו|אינה|לא|שנמסר)|"
    r"מגבלות המידע|אינו מפורט|אינה מפורטת|לא מפורט|לא מפורטת|אינם מפורטים|"
    r"הנתונים (הקיימים|שבידי|מתמקדים|אינם|אינן|לא)|"
    r"provided (text|texts|information|context|documents|passages)|"
    r"the (provided )?(text|texts|documents|context|passages)\b|"
    r"the information (provided|given|available|i have|does not|doesn't|mentions)|according to the",
    re.I,
)
# ניסוחים שאפשר למחוק בלי לפגוע בדקדוק של המשפט
LEAK_OPENERS = re.compile(
    r"(המידע( שבידי)? (מציין|מראה|מצביע על)|על פי המידע|לפי המידע|בהתאם למידע)[,:]?\s*(כי\s+|ש)?"
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
MIN_WORDS_AFTER_CUT = 60


def has_leak(text):
    return bool(STRONG_LEAKS.search(text))


def strip_leaks(text):
    """מוחק פתיחות כמו "המידע מציין כי" ומשאיר את שאר המשפט."""
    return LEAK_OPENERS.sub("", text)


def drop_leaking_sentences(text):
    """רשת ביטחון אחרונה: מוחק משפטים שעדיין מכילים ניסוח חושף, בתנאי שנשארת תשובה מספיק ארוכה."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#") or not has_leak(line):
            out.append(line)
            continue
        prefix = re.match(r"\s*([*\-•]\s+)?", line).group(0)
        kept = [s for s in SENTENCE_SPLIT.split(line[len(prefix):]) if not has_leak(s)]
        if kept:
            out.append(prefix + " ".join(kept))
    cut = "\n".join(out)
    return cut if len(cut.split()) >= MIN_WORDS_AFTER_CUT else text
