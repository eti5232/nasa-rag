# תיעוד הפרויקט: מערכת RAG על מסמכי NASA

מסמך זה מתעד את כל מה שנבנה, כולל הקוד המלא וההסברים. **עיצוב הממשק (צבעים, רקע, גופנים, מסכי דמה) לא מתועד כאן**, לפי בקשה.

## 1. מה המערכת עושה

מקבלת שאלה בעברית או באנגלית, מחפשת במאגר של 73 מסמכים מהאתר nasa.gov את הקטעים הקרובים ביותר למשמעות השאלה, ומעבירה אותם למודל שפה (Gemini) שמנסח תשובה **רק מהם**, בשפת השאלה. בצ'אט עצמו לא מוצגים המקורות (החלטה של בעלת הפרויקט); הם נשמרים רק בקוד ובדוח הבדיקות `test_results.md`. כשאין במאגר מידע מתאים, המערכת אומרת זאת ולא מנחשת.

**הזרימה:**

```
הכנה (פעם אחת):
  מסמכי טקסט ← Documents ← חלוקה לקטעים (Nodes) ← Embeddings (Gemini) ← Chroma (בדיסק)

שאלה (בכל פעם):
  שאלה ← Embedding לשאלה ← 8 הקטעים הקרובים ב-Chroma ← פרומפט + מודל שפה ← תשובה + הצעות להמשך (המקורות נשמרים בקוד ובדוח הבדיקות בלבד)
```

**בחירות טכנולוגיות:**

| רכיב | בחירה | למה |
|---|---|---|
| ספריית RAG | LlamaIndex | נדרש בתרגיל, ומספקת רכיב מוכן לכל שלב |
| Embeddings | `gemini-embedding-001` | רב-לשוני: שאלה בעברית מוצאת טקסט באנגלית. בדקנו: דמיון 0.756 למשפט הנכון מול 0.553 למשפט לא קשור |
| מודל שפה | `gemini-3.1-flash-lite` | מהיר, ומכסה חינמית נדיבה יחסית |
| מסד וקטורי | ChromaDB | נשמר בדיסק, מתאים לפרויקט קטן |
| ממשק | Chainlit (גרסה 2.1.2) | ממשק צ'אט מוכן עם תמיכה בשלבים גלויים וכפתורים |

ה-Embeddings וה-LLM הם **שני מודלים נפרדים**. אין חובה שיהיו מאותו ספק, והם רק במקרה מאותה חברה.

## 2. מבנה התיקייה

```
RAG/
├─ data/                 70 מסמכי הטקסט (מקור: nasa.gov)
├─ chroma_db/            האינדקס הווקטורי (210 קטעים), נוצר ע"י build_index.py
├─ build_index.py        שלבים 3-6: טעינה, חלוקה, Embeddings, שמירה ב-Chroma
├─ common.py             הגדרות משותפות וטעינת האינדקס
├─ query.py              שלבים 7-9: אחזור, תשובה, מקורות
├─ run_tests.py          שלב 10: שבע בדיקות להגשה, שמור ב-test_results.md
├─ chat_app.py           שלב 11: ממשק Chainlit
├─ test_results.md       תוצאות הבדיקות האחרונות
├─ requirements.txt      רשימת החבילות המדויקת
├─ .env                  GOOGLE_API_KEY (סודי, לא משתפים)
├─ PLAN.md               תוכנית העבודה
└─ old_code/             קוד מוקדם שנשמר בצד, כולל download_docs.py שאסף את המסמכים
```

## 3. התקנה והרצה

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

בקובץ `.env` צריכה להיות שורה אחת: `GOOGLE_API_KEY=...`

| מה | פקודה |
|---|---|
| לבנות את האינדקס (פעם אחת, כ-5 דקות) | `python build_index.py` |
| שאלות לדוגמה בטרמינל | `python query.py` |
| בדיקות ההגשה | `python run_tests.py` |
| הצ'אט בדפדפן | `chainlit run chat_app.py -w` ואז http://localhost:8000 (`-w` מרענן את השרת אחרי כל שינוי בקוד) |

**הערות:**
- טעינת הצ'אט הראשונה לוקחת כ-15 שניות, כי היא טוענת את האינדקס והמודלים.
- אם האינדקס כבר קיים, `build_index.py` מדלג על הבנייה ומדפיס רק `בבסיס הנתונים יש קטעים: 210`.
- אם הבנייה נפסקה באמצע, צריך למחוק את התיקייה `chroma_db` ולהריץ שוב, אחרת תישאר אינדקס חלקי.

## 4. שלב 0: איסוף המסמכים

**מה:** 70 עמודי מידע מ-nasa.gov ו-science.nasa.gov, שנשמרו כקבצי טקסט בתיקייה `data`. כל קובץ מתחיל בשתי שורות: כותרת, ואחריה `Source: <כתובת העמוד המקורי>`. את הכותרת והכתובת קוראים בהמשך כדי להציג מקורות.

**למה לא ויקיפדיה:** מסנן האינטרנט ברשת חסם את ויקיפדיה (גם את ה-API וגם את העמודים), לכן עברנו לאתר הרשמי של NASA.

**איך:** הסקריפט `old_code/download_docs.py` (הוא תלוי ב-`old_code/config.py`) ירד מרשימה של **עמודי ליבה** שנקבעו ידנית, ואחריהם עמודים נוספים שהוא גילה בעצמו. התוכן כולל: על NASA והיסטוריה, 12 משימות אפולו, מעבורת החלל, תחנת החלל, ארטמיס, האבל, ווב, וויאג'ר, קאסיני, מאדים וכוכבי לכת.

```python
"""אוסף עמודי מידע מהאתר הרשמי של NASA ושומר אותם כקבצי טקסט בתיקיית data."""
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config import DATA_DIR

HUBS = [
    "https://www.nasa.gov/missions/",
    "https://www.nasa.gov/a-to-z-of-nasa-missions/",
    "https://www.nasa.gov/humans-in-space/",
    "https://www.nasa.gov/humans-in-space/artemis/",
    "https://www.nasa.gov/international-space-station/",
    "https://www.nasa.gov/history/",
    "https://science.nasa.gov/missions/",
    "https://science.nasa.gov/mars/",
    "https://science.nasa.gov/solar-system/",
]
ALLOWED_PREFIXES = (
    "https://www.nasa.gov/humans-in-space/",
    "https://www.nasa.gov/international-space-station/",
    "https://www.nasa.gov/history/",
    "https://www.nasa.gov/mission",
    "https://science.nasa.gov/mission/",
    "https://science.nasa.gov/mars/",
    "https://science.nasa.gov/solar-system/",
    "https://science.nasa.gov/astrophysics/",
)
BLOCKED_PARTS = ("/es/", "/news", "/blogs/", "/image", "/video", "/tag/", "/event")
# עמודי ליבה שיורדים תמיד, לפני העמודים שהסקריפט מגלה בעצמו
CORE_PAGES = [
    "https://www.nasa.gov/about/",
    "https://www.nasa.gov/history/",
    "https://www.nasa.gov/centers-and-facilities/",
    "https://www.nasa.gov/directorates/",
    "https://www.nasa.gov/missions/",
    "https://www.nasa.gov/a-to-z-of-nasa-missions/",
    "https://www.nasa.gov/apollo/",
    *[f"https://www.nasa.gov/mission/apollo-{n}/" for n in (1, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17)],
    "https://www.nasa.gov/space-shuttle/",
    "https://www.nasa.gov/international-space-station/",
    "https://www.nasa.gov/humans-in-space/artemis/",
    "https://science.nasa.gov/mission/hubble/",
    "https://science.nasa.gov/mission/webb/",
    "https://science.nasa.gov/mission/voyager/",
    "https://science.nasa.gov/mission/mars-2020-perseverance/",
    "https://science.nasa.gov/mission/cassini/",
    "https://science.nasa.gov/mission/new-horizons/",
    "https://science.nasa.gov/mission/juno/",
    "https://science.nasa.gov/mars/",
    "https://science.nasa.gov/mars/facts/",
    "https://science.nasa.gov/mission/msl-curiosity/",
    "https://science.nasa.gov/mission/maven/",
    "https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/",
    "https://science.nasa.gov/solar-system/",
    "https://science.nasa.gov/solar-system/planets/",
    "https://science.nasa.gov/moon/",
    "https://science.nasa.gov/earth/",
    "https://science.nasa.gov/sun/",
    "https://science.nasa.gov/universe/",
]
EXTRA_PAGES = 30
MAX_PAGES = len(CORE_PAGES) + EXTRA_PAGES
MIN_CHARS = 2000
HEADERS = {"User-Agent": "Mozilla/5.0 (nasa-rag-student-project)"}


def get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    return BeautifulSoup(r.text, "html.parser")


def collect_links() -> list[str]:
    found: dict[str, None] = {}
    for hub in HUBS:
        soup = get(hub)
        if not soup:
            print("מרכז לא נגיש:", hub)
            continue
        for a in soup.find_all("a", href=True):
            url = a["href"].split("#")[0].split("?")[0]
            if not url.startswith(ALLOWED_PREFIXES):
                continue
            if any(part in url for part in BLOCKED_PARTS):
                continue
            if url.rstrip("/") in [h.rstrip("/") for h in HUBS]:
                continue
            found[url] = None
    return list(found)


def extract_text(soup: BeautifulSoup) -> tuple[str, str]:
    title = soup.find("h1")
    title = title.get_text(" ", strip=True) if title else ""
    root = soup.find("main") or soup
    parts = [
        el.get_text(" ", strip=True)
        for el in root.find_all(["h2", "h3", "p", "li"])
    ]
    parts = [p for p in parts if len(p) > 40]
    return title, "\n\n".join(parts)


def main():
    out = Path(DATA_DIR)
    out.mkdir(exist_ok=True)
    discovered = [u for u in collect_links() if u not in CORE_PAGES]
    links = CORE_PAGES + discovered
    print("עמודי ליבה:", len(CORE_PAGES), "| נוספים שנמצאו:", len(discovered))
    saved = 0
    for url in links:
        if saved >= MAX_PAGES:
            break
        soup = get(url)
        if not soup:
            continue
        title, text = extract_text(soup)
        if len(text) < MIN_CHARS:
            continue
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("nasa.gov/")[-1]).strip("_")[:80]
        (out / f"{slug}.txt").write_text(
            f"{title}\nSource: {url}\n\n{text}", encoding="utf-8"
        )
        saved += 1
        print(f"נשמר ({saved}):", title or slug, len(text), "תווים")
        time.sleep(0.5)
    print("סה\"כ קבצים:", saved)


if __name__ == "__main__":
    main()
```

**הסבר:**
- `get` מוריד עמוד ומחזיר אותו כעץ HTML, או `None` אם נכשל.
- `collect_links` עובר על עמודי "מרכז" ואוסף קישורים רלוונטיים, ומסנן חדשות, תמונות, וידאו ועמודים בספרדית.
- `extract_text` מוציא מכל עמוד כותרת וטקסט (כותרות משנה, פסקאות ורשימות), ומתעלם משורות קצרות מ-40 תווים כדי לדלג על תפריטים.
- `MIN_CHARS = 2000` דוחה עמודים עם מעט תוכן.
- `CORE_PAGES` מבטיח שעמודים בסיסיים (על NASA, היסטוריה, כל משימות אפולו) יהיו במאגר תמיד.
- **תרגום ידני:** אחד העמודים שהסקריפט הוריד היה בספרדית (עדכון על תוכנית ארטמיס). הוא תורגם לאנגלית (על ידי Claude) לקובץ `data/humans_in_space_nasa_strengthens_artemis_adds_a_mission.txt` (בראשו הערה שזה תרגום). המקור נשמר ב-`old_code/spanish_original`.

## 5. `build_index.py`: שלבים 3 עד 6

```python
# שלב 3 - טעינת המסמכים
from llama_index.core import SimpleDirectoryReader

docs = SimpleDirectoryReader("data").load_data()

print("נטענו מסמכים:", len(docs))
print("שם הקובץ:", docs[0].metadata["file_name"])
print("אורך הטקסט:", len(docs[0].text))
print(docs[0].text[:300])


# שלב 4 - חלוקה לקטעים
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
nodes = splitter.get_nodes_from_documents(docs)

print("נוצרו קטעים:", len(nodes))
print("קטע לדוגמה מתוך:", nodes[5].metadata["file_name"])
print(nodes[5].text)


# שלב 5 - Embeddings
import truststore
from dotenv import load_dotenv
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

truststore.inject_into_ssl()
load_dotenv()

embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-001")

vector = embed_model.get_text_embedding(nodes[5].text)
print("אורך הווקטור:", len(vector))
print("5 המספרים הראשונים:", vector[:5])

# האם עברית ואנגלית "נפגשות"? משווים שאלה בעברית לשני משפטים באנגלית
question = embed_model.get_query_embedding("מי היה האדם הראשון על הירח?")
about_moon = embed_model.get_text_embedding("Neil Armstrong was the first person to walk on the Moon.")
about_hubble = embed_model.get_text_embedding("The Hubble Space Telescope takes pictures of distant galaxies.")

print("דמיון לשאלה, משפט על הירח:", embed_model.similarity(question, about_moon))
print("דמיון לשאלה, משפט על האבל:", embed_model.similarity(question, about_hubble))


# שלב 6 - שמירה ב-Chroma
import time

import chromadb
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

Settings.embed_model = embed_model

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection("nasa")
vector_store = ChromaVectorStore(chroma_collection=collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

if collection.count() == 0:
    builder = VectorStoreIndex([], storage_context=storage_context)
    BATCH = 15
    for i in range(0, len(nodes), BATCH):
        builder.insert_nodes(nodes[i : i + BATCH])
        print(f"נשמרו {min(i + BATCH, len(nodes))}/{len(nodes)}")
        time.sleep(20)

index = VectorStoreIndex.from_vector_store(vector_store)
print("בבסיס הנתונים יש קטעים:", collection.count())
```

### שלב 3: טעינה
`SimpleDirectoryReader("data")` קורא כל קובץ בתיקייה ויוצר מהם רשימת `Document`: אחד לכל קובץ. ל-Document יש `text` (הטקסט המלא) ו-`metadata` (למשל `file_name`). הקוד מדפיס כמה נטענו (70) ומציג דוגמה.

### שלב 4: חלוקה
- **למה לחלק:** מסמך שלם עוסק בכמה נושאים, וקטע קטן מדבר בדרך כלל על אחד, ולכן קל יותר למצוא אותו. בנוסף, שליחת מסמך שלם בכל שאלה היא יקרה ורועשת.
- `SentenceSplitter` חותך בגבולות משפטים. `chunk_size=512` הוא האורך המרבי ב**טוקנים** (טוקן הוא בערך 0.75 מילה באנגלית, כך ש-512 הם בערך 380 מילים). `chunk_overlap=50` הוא חפיפה בין קטעים סמוכים, כדי שמשפט על הגבול לא יאבד הקשר.
- התוצאה: רשימת `Node`ים (קטעים). כל Node יורש את ה-metadata של המסמך שלו. מתקבלים **210 קטעים**.
- 512 ו-50 הן נקודת התחלה מקובלת ולא ערכים "נכונים", ואפשר לכוונן אותם.

### שלב 5: Embeddings
- **Embedding** הוא רשימת מספרים (וקטור באורך 3072) שמייצגת את **המשמעות** של טקסט. טקסטים בעלי משמעות דומה מקבלים וקטורים קרובים, גם בשפות שונות.
- `truststore.inject_into_ssl()` גורם לפייתון להשתמש בתעודות האבטחה של Windows. בלעדיו, מסנן האינטרנט ברשת גורם לשגיאות SSL.
- `load_dotenv()` טוען את `GOOGLE_API_KEY` מקובץ `.env`, כדי שהמפתח לא יופיע בקוד.
- `get_text_embedding` מיועד לטקסטים שמחפשים בהם, ו-`get_query_embedding` לשאלות. `similarity` מחשב קרבה בין שני וקטורים.
- **הוכחה שעברית ואנגלית נפגשות:** השאלה בעברית "מי היה האדם הראשון על הירח?" קיבלה דמיון **0.756** למשפט האנגלי על ארמסטרונג, ו-**0.553** למשפט על טלסקופ האבל.

### שלב 6: שמירה ב-Chroma
- `PersistentClient(path="chroma_db")` פותח מסד נתונים שנשמר בדיסק, כך שהחישוב נעשה פעם אחת ובכל הרצה הבאה רק טוענים.
- `collection` הוא "טבלה" בשם `nasa`. `ChromaVectorStore` ו-`StorageContext` מחברים אותה ל-LlamaIndex.
- **השורה החשובה:** `if collection.count() == 0:`. אם כבר יש קטעים, לא בונים שוב. בלי זה כל הרצה הייתה מחשבת הכול מחדש ומוסיפה כפילויות.
- הלולאה שולחת **15 קטעים בכל פעם** ומחכה 20 שניות, בגלל מגבלות הקצב של Gemini החינמי (טוקנים לדקה ובקשות לדקה). בלי ההמתנה הבנייה נכשלה בשגיאה `429`.
- `VectorStoreIndex.from_vector_store(...)` טוען אינדקס מוכן **בלי חישוב**.

## 6. `common.py`: הגדרות משותפות

```python
import chromadb
import truststore
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

truststore.inject_into_ssl()
load_dotenv()

Settings.embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-001")


def get_index():
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_collection("nasa")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(vector_store)
```

**למה קובץ נפרד:** `build_index.py` מכין את האינדקס פעם אחת, וכל השאר (`query.py` והצ'אט) צריכים רק לטעון אותו ולשאול. במקום להעתיק את ההגדרות, הן במקום אחד.
`get_collection` (ולא `get_or_create`) גורם לשגיאה ברורה אם האינדקס חסר, ולא ליצירה שקטה של אינדקס ריק.
*הערה:* `build_index.py` עדיין מכיל עותק של אותן הגדרות, וניתן למזג בעתיד.

## 7. `query.py`: שלבים 7 עד 9

```python
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
    "I have', 'המידע שבידי', 'המידע מציין', 'לא מצוין', 'בטקסטים שסופקו', 'במסמכים', "
    "'המידע מכסה' or 'the provided text'. Never describe what your information covers or "
    "its limits. Answer as if you simply know.\n"
    "If part of the question cannot be answered, say so in the first person, in the "
    "language of the question: for an English question write 'I don't have information "
    "about X'; for a Hebrew question write 'אין לי מידע על X'. Never say that "
    "'the information does not mention' or 'the text does not state'. When the information "
    "answers only part of the question, or only mentions the subject in passing, answer the "
    "supported part, then add one plain sentence saying exactly what you do not have "
    "information about. Never turn a missing detail into a denial: if you do not have "
    "information about whether something happened, do not say that it did not happen.\n"
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
    "- Never add a question that is not in the message. You may only replace pronouns and "
    "references ('he', 'it', 'there', 'הוא', 'זה', 'שם') with the names they refer to in the "
    "conversation. Add the assistant's offer only when the message begins with an agreement.\n"
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


def is_multi(q):
    return q.count("?") + q.count("؟") >= 2 or any(w in f" {q} " for w in MULTI_WORDS)


def starts_with_affirmation(q):
    return re.split(r"[\s,.!?]+", q.strip().lower(), maxsplit=1)[0] in AFFIRMATIONS


def needs_planning(history, question):
    """האם ההודעה דורשת הבנת הקשר: כמה שאלות בהודעה אחת, או הודעת המשך ("כן", הודעה קצרה)."""
    q = question.strip()
    multi = is_multi(q)
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
    # רשת ביטחון: הודעה עם שאלה אחת שלא פותחת ב"כן" נשארת שאלה אחת, גם אם המתכנן הוסיף שאלות
    if not is_multi(question) and not starts_with_affirmation(question):
        lines = lines[:1]
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


# ניסוחים שמעידים שהמודל מדבר על "המידע/הטקסט" שקיבל. אם נמצא אחד, מנסחים את התשובה מחדש פעם אחת
STRONG_LEAKS = re.compile(
    r"שסופק|שניתנו|שניתן לי|במסמכים|בטקסט|המסמכים|המקורות|"
    r"המידע (הקיים|הזמין|שבידי|מכסה|מתמקד|מציין|מראה|מצביע)|מגבלות המידע|"
    r"\b(provided|the text|the documents|the sources|according to the)\b|"
    r"the information (provided|given|available|I have|does not|doesn't)",
    re.I,
)


def compose_answer(q, nodes):
    """שלב ב: מנסח תשובה מהקטעים. מחזיר (טקסט, האם נמצאה תשובה, הצעות להמשך)."""
    for _ in range(2):
        response = query_engine.synthesize(QueryBundle(q), nodes)
        text = str(response).strip()
        if not STRONG_LEAKS.search(text):
            break
    if is_no_answer(text):
        return "", False, []
    text, followups = split_followups(strip_leaks(text))
    return text, True, followups


# שאלות על הצ'אט עצמו (יכולות, יוצר, פרטים טכניים): עונים עליהן בטקסט קבוע, בלי חיפוש במאגר ובלי מודל,
# כי מודל שמתאר את הידע שלו חושף שיש לו "מידע" ו"מסמכים", ולפרטים טכניים אסור לענות בכלל
SECRET_WORDS = re.compile(r"\bapi\b|\bkey\b|מפתח|סיסמ|פרומפט|\bprompt\b|טוקן|\btoken\b", re.I)
ABOUT_BOT = re.compile(r"אתה|אתם|שלך|אותך|שלכם|\byou\b|\byour\b", re.I)
CREATOR_QUESTION = re.compile(
    r"מי (יצר|בנה|פיתח|כתב|תכנת|עשה) (אותך|אתכם)|מי אתה\b|מי אתם\b|איזה מודל (אתה|אתם|שפה|בינה)|"
    r"(מי|מיהו|מיהי|מיהם).{0,40}(יצר|בנה|פיתח|כתב|תכנת|עשה|לכתוב|לבנות|לפתח|ליצור).{0,20}(ה?צ'אט|ה?בוט|ה?אתר הזה|ה?אפליקציה הזאת)|"
    r"(ה?צ'אט|ה?בוט) (הזה|הזאת)? ?(נכתב|נוצר|נבנה|פותח) על ידי|"
    r"\bwho (made|created|built|developed|wrote|programmed) (this|the) (chat|chatbot|bot|app|system|website)\b|"
    r"\bwho (made|created|built|developed|wrote|programmed) you\b|\bwho are you\b|"
    r"\bwhich model (are|do) you\b",
    re.I,
)
CAPABILITY_QUESTION = re.compile(
    r"מה אתה (יודע|יכול)|על מה (אפשר|ניתן|אני יכול|אני יכולה) לשאול|לא תדע|לא תוכל לענות|"
    r"\bwhat (can|do) you (know|do)\b|\bwhat can i ask\b|\bwhat (questions )?(won't|can't|couldn't) you\b",
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
}


def system_reply(q):
    """אם השאלה היא על הצ'אט עצמו מחזיר תשובה קבועה בשפת השאלה, אחרת None."""
    if SECRET_WORDS.search(q) and ABOUT_BOT.search(q):
        kind = "secret"
    elif CREATOR_QUESTION.search(q):
        kind = "creator"
    elif CAPABILITY_QUESTION.search(q):
        kind = "capability"
    else:
        return None
    he, en = SYSTEM_REPLIES[kind]
    return he if is_hebrew(q) else en


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
```

### שלב 7: אחזור
- `as_retriever(similarity_top_k=TOP_K)` יוצר "מחפש" שמחזיר את **6** הקטעים הקרובים ביותר לשאלה (`TOP_K = 8`; התחלנו ב-4 והגדלנו כדי שהמודל יראה יותר חומר ויכתוב תשובות מלאות ועשירות יותר, למשל כששם האסטרונאוט מופיע רק בקטע חמישי או שישי). `retrieve(q)` מחשב Embedding לשאלה, משווה לכל 210 הקטעים ומחזיר את הקרובים עם `score`.
- **הציון הוא קרבה יחסית, לא הסתברות לנכונות.** ערכים סביב 0.5 תקינים למודל הזה. מה שחשוב הוא הסדר.
- **מה למדנו:** בדיקה של 10 תוצאות לשאלה "מי היה האדם הראשון על הירח?" הראתה שחמש התוצאות הראשונות מכילות את המשפט על ארמסטרונג. אבל ההדפסה הראתה רק את 120 התווים הראשונים של כל קטע, שנראו כרשימת ניווט, ולכן נראה בטעות שהאחזור לא טוב. **שופטים אחזור לפי תוכן הקטע, לא לפי תחילתו או הציון.** עברית ואנגלית החזירו את אותם קבצים.

### שלב 8: תשובה
- `GoogleGenAI(model=..., temperature=0.6)` הוא מודל השפה. `temperature` שולט ב"יצירתיות". **בהתחלה היה 0.1, וכך אותה שאלה החזירה תשובה זהה מילה במילה** (דמיון של 100% בין הרצות). ב-0.6 אותה שאלה נותנת תשובות שונות (דמיון 18%–52%), בלי שנפגעו הדיוק, הדליפות והשפה (נבדק). ערך גבוה יותר מגדיל את הסיכון להמצאות ולשגיאות כתיב, ולכן לא עלינו מעבר.
- **הפרומפט** הוא לב השלב:
  1. `ONLY the information below` מחייב את המודל להסתמך על הקטעים. זה מה שהופך את המערכת ל-RAG ולא לצ'אט כללי.
  2. **אסור להזכיר את המידע שהמודל קיבל** ("הטקסט המסופק", "המסמכים", "לפי המקורות"). בלי ההוראה הזו המודל חשף פרטים פנימיים, ונשמע כמו מערכת שמדווחת על עצמה. המודל צריך לענות כאילו הוא פשוט יודע.
  2א. **כשחסר חלק מהמידע, המודל אומר זאת בגוף ראשון** ("אין לי מידע על X"), ולא בניסוח של דיווח על טקסט ("המידע שסופק אינו מציין"). ההוראה הראשונה לבדה לא הספיקה: המודל מציית לאיסור רק כשיש לו תשובה מלאה, וכשחסר משהו הוא עבר לדווח על המצב. הדוגמה ניתנת בשפת השאלה, כי דוגמה בעברית בלבד גרמה למודל לענות בעברית גם על שאלה באנגלית.
  3. **"החברה", "הסוכנות" או "הארגון" בלי שם הם NASA.** בלי זה, שאלה כמו "מי אחראי על החברה?" לא נענתה, כי המודל לא ידע לאיזו חברה הכוונה.
  4. `[NO_ANSWER]`: כשאין תשובה, המודל עונה **רק** בסימון הזה, בלי הסבר. הקוד מזהה אותו ומציג במקומו הודעה קבועה וקצרה (`no_answer_text`) בשפת השאלה. סימון קבוע אמין יותר מניסיון לזהות ניסוחים כמו "לא הצלחתי למצוא" בכל שפה, והודעה קבועה לא יכולה לחשוף פרטים פנימיים.
  4א. **תשובה עשירה, צבעונית ומגוונת (200–350 מילים):** כותרת עם אימוג'י, משפט ישיר שעונה על השאלה, שניים או שלושה סעיפים שמסבירים צעד אחר צעד עם שמות, תאריכים ומספרים, שורת "✨ הידעת?" עם עובדה מפתיעה מהמידע, ומשפט סיום מזמין. אימוג'ים במידה (3–6), הדגשות בטקסט, וטון של סיפור. גם שאלה פשוטה מקבלת קודם תשובה ישירה ואז הקשר מהמידע. המודל מתבקש לגוון סגנון בין תשובות (לא לפתוח תמיד באותו אופן ולהבליט פרטים שונים), ובעברית לא לפנות בלשון זכר או נקבה (למשל "רוצים לשמוע עוד על...?" ולא "האם תרצה...?").
  **חשוב:** ההסבר של מושגים מוגבל למה שהמסמכים עצמם מסבירים. כשהתירו למודל להסביר "מהידע שלו", הוא הוסיף הגדרות שלא נמצאות במאגר (למשל הגדרה של חור שחור). הדרך להעשיר את הידע של המשתמש בלי להמציא היא להוסיף עוד תוכן למאגר, ולא להרפות את הכללים. כדי שהתשובות יהיו עשירות יותר, מספר הקטעים שנשלחים למודל עלה ל-8 (`TOP_K = 8`).
  4ב. **הצעות להמשך (`FOLLOW_UPS:`):** אחרי התשובה המודל כותב 2–3 שאלות המשך שאפשר לענות עליהן מהמידע, מופרדות ב-`|`. `split_followups` מפריד אותן מהתשובה, והצ'אט מציג אותן ככפתורים. בלחיצה השאלה נשלחת. כך הקורא נמשך לשאול הלאה, ובלי להבטיח נושאים שהמערכת לא יודעת.
  5. `IMPORTANT: ... same language as the question` מופיע **אחרון** בפרומפט, כי מודלים נוטים לציית יותר להוראה האחרונה. זה פתר באג (ראו בעיות).
- `{context_str}` ו-`{query_str}` הם מקומות שמורים שבהם LlamaIndex מכניסה את הקטעים ואת השאלה.
- `as_query_engine(...)` מחבר אחזור ותשובה לחוליה אחת.

### שלב 9: מקורות
- `read_header` קורא רק את שתי השורות הראשונות של הקובץ (כותרת וכתובת).
- `clean_excerpt` מנקה שורת `Source:` ומקצר קטע ל-600 תווים (בלי לחתוך באמצע מילה).
- `build_sources` בונה לכל קטע שנשלף: כותרת, קישור, ציון וקטע מצוטט.

### הבנת הקשר: "כן" והודעות עם כמה שאלות
**הבעיה:** כל הודעה נשלחה למערכת לבדה. כשהתשובה הסתיימה ב"רוצים לשמוע עוד על המשימות של אפולו?" והמשתמשת ענתה "כן, ומה התוכנית הגדולה ביותר של החברה?", המערכת ענתה רק על השאלה החדשה והתעלמה מה"כן".

**הפתרון (ב-`query.py` וב-`chat_app.py`):**
- `needs_planning` מחליטה אם ההודעה דורשת הבנת הקשר: יש בה כמה שאלות, או שיש שיחה קודמת וההודעה פותחת במילת הסכמה או קצרה (עד 4 מילים). הודעה רגילה לא עוברת תהליך נוסף ולכן אין עלות זמן או מכסה.
- `plan_questions` שולחת למודל נפרד (טמפרטורה 0, לתוצאה יציבה) את סוף השיחה ואת ההודעה, ומקבלת רשימה של עד 3 שאלות עצמאיות. השאלה המפורשת בהודעה באה ראשונה, ואחריה מה שהמשתמשת אישרה. "החברה" בלי שם מפוענחת כ-NASA.
- `search_many` מחפשת לכל שאלה בנפרד ומאחדת את הקטעים (לכל קטע נשמר הציון הגבוה ביותר).
- `compose_text` שולחת למודל את השאלות, אחת בכל שורה, **בלי מספור**, והפרומפט מורה לענות על כל שאלה בנפרד, בסדר, תחת כותרת תיאורית משלה עם אימוג'י ובלי מספרים. (בגרסה הראשונה שלחנו רשימה ממוספרת, והמודל העתיק את המספרים לכותרות: "1. מי הקים את נאס"א?". זה נראה מכני, ולכן הוסר.)
- **"✨ הידעת?" חייבת להיות קשורה לנושא השאלה** (לשאלה על היסטוריה, עובדה היסטורית; לשאלה על משימה, עובדה על אותה משימה; לשאלה על אדם, עובדה עליו). אם אין במידע עובדה מפתיעה על הנושא המדויק, השורה מושמטת. בגרסה הראשונה שאלה על הקמת הסוכנות קיבלה "הידעת?" על מקור המילה "אסטרונאוט".
- בצ'אט, `remember` שומרת את הסיבוב האחרון ב-`cl.user_session`, ושלב "הבנת ההקשר" מוצג כשההודעה פוענחה מחדש, כך שרואים איך המערכת הבינה את הבקשה.

**אימות:** "כן, מה היה התוכנית הגדולה ביותר של החברה?" פוצלה ל"מה הייתה התוכנית הגדולה ביותר של נאס"א?" ול"אילו משימות מרתקות היו בתוכנית אפולו?", והתשובה כיסתה את שתיהן. "כן" לבדה, "yes please" והודעה עם שתי שאלות פוענחו נכון, ושאלה רגילה לא עברה תהליך נוסף.

### שינוי בשלב 11: פיצול ל-`search` ו-`compose_answer`
הממשק נדרש להציג את שני השלבים בנפרד (חיפוש ואז ניסוח), ולכן `query_engine.query(q)` פוצל: `search` מחזיר קטעים, ו-`compose_answer` מנסח מהם תשובה בעזרת `query_engine.synthesize`. כך אין אחזור כפול. `answer_question` נשאר עם אותו ממשק, ולכן הבדיקות לא השתנו.

## 8. `run_tests.py`: שלב 10

```python
# שלב 10 - בדיקות להגשה
import time

from query import answer_question

tests = [
    ("מי היה האדם הראשון על הירח?", "יש תשובה"),
    ("מה קרה באפולו 13?", "יש תשובה"),
    ("באיזו שנה הוקמה נאס״א?", "יש תשובה"),
    ("כמה אסטרונאוטים יש בדרך כלל בתחנת החלל הבינלאומית?", "יש תשובה (ניסוח שונה מהמסמך)"),
    ("What is the James Webb Space Telescope?", "יש תשובה (באנגלית)"),
    ("מה המתכון לעוגת שוקולד?", "אין תשובה במאגר"),
    ("Who won the 2022 World Cup?", "אין תשובה במאגר (באנגלית)"),
]

lines = ["# תוצאות בדיקות\n"]

for i, (question, expected) in enumerate(tests, 1):
    answer, sources = answer_question(question)

    print(f"\n=== בדיקה {i}: {question}")
    print("מצופה:", expected)
    print("תשובה:", answer)
    for s in sources:
        print(f"   מקור: {s['title']} | {s['url']} | {s['score']:.2f}")

    lines.append(f"## בדיקה {i}: {question}\n")
    lines.append(f"- **מצופה:** {expected}")
    lines.append("- **תשובה:**")
    lines.extend("  > " + ln if ln.strip() else "  >" for ln in answer.splitlines())
    lines.append("- **מקורות שנשלפו:**")
    for s in sources:
        lines.append(f"  - {s['title']} ({s['url']}), דמיון {s['score']:.2f}")
    lines.append("")

    time.sleep(4)

with open("test_results.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\nהתוצאות נשמרו בקובץ test_results.md")
```

**הסבר:** שבע שאלות שמכסות ישירה, ניסוח שונה מהמסמך, אנגלית, ושתי שאלות בלי תשובה במאגר (אחת בכל שפה). כל בדיקה מדפיסה תשובה ומקורות ונשמרת ב-`test_results.md`. `time.sleep(4)` נועד לא לחרוג ממגבלת הקצב.

**תוצאות (הרצה אחרונה):** כל שבע הבדיקות עברו.

| # | שאלה | תוצאה |
|---|---|---|
| 1 | מי היה האדם הראשון על הירח? | ניל ארמסטרונג |
| 2 | מה קרה באפולו 13? | תשובה מפורטת |
| 3 | באיזו שנה הוקמה נאס״א? | 1958 |
| 4 | כמה אסטרונאוטים בתחנת החלל? | שבעה |
| 5 | What is the James Webb Space Telescope? | תשובה באנגלית |
| 6 | מה המתכון לעוגת שוקולד? | "לא הצלחתי למצוא מידע..." בעברית |
| 7 | Who won the 2022 World Cup? | "I could not find information..." באנגלית |

**הערה:** כל בדיקה היא הרצה אחת, והמודל אינו דטרמיניסטי לגמרי, ולכן הניסוח משתנה קצת בין הרצות.

## 9. `chat_app.py`: ממשק Chainlit (החלק הפונקציונלי)

```python
# שלב 11 - ממשק Chainlit
import chainlit as cl

from query import (
    compose_answer,
    compose_text,
    is_hebrew,
    no_answer_text,
    plan_questions,
    search_many,
    system_reply,
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
                compose_text(questions), nodes
            )
            step.output = "התשובה נוסחה מהקטעים שנמצאו"
    except Exception as error:
        await send_error(question, error)
        return

    remember(question, text if found else no_answer_text(question))
    if found:
        await cl.Message(
            content=text,
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
```

**הסבר, לפי חלקים:**

- **`@cl.on_message` ו-`respond`:** בכל הודעה שהמשתמשת שולחת, `respond` מריצה את התהליך המלא.
- **`cl.make_async(...)`:** הקריאות ל-`search` ול-`compose_answer` איטיות וחוסמות (מחכות לרשת). בלי העטיפה השרת היה "קופא" לכל המשתמשים בזמן ההמתנה. העטיפה מריצה אותן ברקע.
- **`cl.Step`: שלבים גלויים.** "חיפוש במאגר" ו"ניסוח תשובה" מוצגים בצ'אט עם תוצאה של כל שלב (למשל "נמצאו 4 קטעים מתוך 2 מסמכים"). זה מתאר את מה שקורה בפועל, לא אנימציה גנרית.
- **הצעות להמשך:** `compose_answer` מחזירה גם את שאלות ההמשך, והן מוצגות ככפתורים מתחת לתשובה (`cl.Action`). לחיצה משתמשת באותה פונקציית `example` ששולחת את השאלה.
- **זיהוי "אין תשובה":** `is_no_answer` מזהה גם את הסימון `[NO_ANSWER]` וגם משפט קצר שמתחיל ב"אין לי מידע" או "I don't have information" (הניסוח שהפרומפט מכתיב). בלי זה, כשהמודל ענה "אין לי מידע" בלי הסימון, הצ'אט הציג מתחתיו רשימת מקורות והצעות המשך כאילו נמצאה תשובה.
- **מקורות לא מוצגים בצ'אט:** בעלת הפרויקט ביקשה שהמשתמשים לא יראו את מקורות התשובה. `build_sources` ממשיכה להתקיים ב-`query.py` ובה משתמש `run_tests.py` לדוח הבדיקות, אבל `chat_app.py` לא מציג רשימת מקורות, קישורים או קטעים צדדיים.
- **מצב "אין מידע":** כש-`compose_answer` מחזירה `found=False` (המודל ענה `[NO_ANSWER]`), מוצגת כותרת והודעה קבועה וקצרה בשפת השאלה (`no_answer_message`), ושני כפתורים עם שאלות שהמערכת יודעת לענות עליהן. **לא משתמשים בטקסט של המודל** כדי שלא יחשוף פרטים פנימיים.
- **מצבי שגיאה:** `is_rate_limit` מזהה מכסה שנגמרה, עומס או פסק זמן (לפי `429`, `RESOURCE_EXHAUSTED`, `503` ועוד). כל שגיאה אחרת מקבלת הודעה כללית. בשני המקרים מוצג כפתור **"נסו שוב"** ששולח את אותה שאלה מחדש דרך `@cl.action_callback("retry")`.
- **`@cl.action_callback("example")`:** לחיצה על שאלה מוצעת מציגה אותה כהודעת משתמש ומריצה אותה.

**הגדרות Chainlit חשובות** (ב-`.chainlit/config.toml`):
- `enable_telemetry = false`: Chainlit שולחת נתוני שימוש החוצה כברירת מחדל, וכיביתי זאת.
- `spontaneous_file_upload.enabled = false`: המערכת לא משתמשת בקבצים שמועלים.
- `cot = "full"`: מציג את השלבים (`Step`) בצ'אט.

**בדיקות שבוצעו בדפדפן:** שאלה בעברית, שאלה באנגלית, פתיחת קטע מצוטט בלוח הצדדי, שאלה בלי תשובה (מצב "אין מידע"), שגיאה (בשרת זמני שדימה שגיאת מכסה, ללא שינוי בקוד הפרויקט), לחיצה על "נסו שוב", ובדיקת מובייל (375 פיקסלים: אין גלישה אופקית, השאלות והשדה בתוך המסך).

## 10. בעיות שנתקלנו בהן ואיך פתרנו

1. **מסנן אינטרנט חסם את ויקיפדיה** (גם ה-API וגם העמודים). ← עברנו לאתר הרשמי של NASA, שפתוח.
2. **שגיאת תעודת SSL בכל חיבור לרשת.** המסנן מחליף תעודות. ← `truststore.inject_into_ssl()` גורם לפייתון להשתמש בתעודות של Windows (ולא כיבוי אימות האבטחה).
3. **מגבלות קצב של Gemini החינמי** (30,000 טוקנים בדקה ו-100 בקשות בדקה ל-Embeddings, ו-5 עד 15 בקשות בדקה למודלי השפה). ← הבנייה בקבוצות של 15 קטעים עם המתנה של 20 שניות.
4. **מאגר שחסרו בו מידע בסיסי.** שאלה על שנת הקמת NASA לא נענתה, כי הסקריפט הוריד עמודים לפי סדר הופעתם באתר (בעיקר משימות לפי א"ב). ← רשימת `CORE_PAGES` שיורדת תמיד.
5. **Apollo 13 נחתך מהמאגר** כשהוספנו עמודי ליבה. ← כל 12 משימות אפולו נוספו ל-`CORE_PAGES`.
6. **תשובה באנגלית ניתנה בספרדית.** בשאלה בלי תשובה באנגלית, החיפוש החזיר "הכי קרוב שיש", שהיה עמוד ספרדי, והמודל ענה בשפת הקטע למרות ההוראה. ← הקשחת הפרומפט (הוראת השפה אחרונה, גם אם המידע בשפה אחרת) ותרגום העמוד הספרדי לאנגלית.
7. **שיפוט שגוי של האחזור.** חשבנו שהאחזור לא טוב כי ההדפסה הציגה רק תחילת קטעים (רשימות ניווט). בדיקת התוכן המלא הראתה שהתשובה נמצאת בקטעים. ← לשפוט לפי תוכן.
8. **זיהוי "אין תשובה" שביר.** המודל מנסח "לא נמצא מידע" בכל מיני ניסוחים ושפות. ← סימון קבוע `[NO_ANSWER]` שהקוד מזהה ומסיר.
9. **ההתקנה של Chainlit העדכנית נכשלה** (עמוד החבילה `mcp` ב-PyPI הגיע משובש ברשת, שגיאת `InvalidChunkLength`). ← גרסה `chainlit<2.2` (2.1.2) שלא תלויה בה, והתקנה עם `--no-build-isolation`. זו שגיאת העברה ולא חסימה, ולא נעשה ניסיון לעקוף אותה.
11. **התשובה חשפה פרטים פנימיים, והשאלה "מי אחראי על החברה?" לא נענתה.** המודל כתב "בטקסט המסופק לא מצאתי..." (חושף שהוא מקבל קטעי טקסט), ולא הבין ש"החברה" היא NASA. הסיבה: כשכתבתי מחדש את הפרומפט לשלב 11, ההוראה האוסרת להזכיר את המידע אבדה. ← הוחזרה, נוספה הוראה ש"החברה" היא NASA, וההודעה על "אין מידע" הפכה לקבועה ולא מגיעה מהמודל. נבדק: שום תשובה לא מזכירה "הטקסט" או "המידע", ו"מי אחראי על החברה?" נענית (ג'ארד אייזקמן).
14. **המערכת התעלמה מ"כן".** משתמשת ענתה "כן" להצעה בסוף תשובה והוסיפה שאלה חדשה, והמערכת ענתה רק על השאלה החדשה. הסיבה: אין זיכרון של השיחה, וכל הודעה נשלחת לבדה. הצעות להמשך בלי הבנה של "כן" הן מלכודת, והיה צריך לטפל בזה כשהוספנו אותן. ← הבנת הקשר (פרק "הבנת הקשר" למעלה).
16. **כותרות ממוספרות ו"הידעת?" לא קשורה.** בהודעה עם שלוש שאלות, התשובה כללה כותרות "1. 2. 3." (המודל העתיק את המספור שנשלח אליו), ו"הידעת?" עסקה במילה "אסטרונאוט", בלי קשר לשאלה על הקמת NASA. ← שליחת השאלות בלי מספור, הוראה לכותרות תיאוריות, והוראה ש"הידעת?" תהיה על הנושא המדויק או תושמט. נבדק על ארבע הודעות: אין כותרות ממוספרות, אין מספרים שלא נמצאים במסמכים, והעובדות קשורות לנושא.
15. **שרת ישן המשיך לרוץ אחרי עדכוני קוד.** Chainlit לא טוען קוד מחדש מעצמו, ולכן הצ'אט הציג גרסה ישנה (תשובה קצרה, שני מקורות, תשובה זהה). ← הרצה במצב `chainlit run chat_app.py -w` שמרענן אחרי כל שינוי בקוד. **לקח: לבדוק תמיד שהשרת שרץ הופעל אחרי השינוי האחרון (השוואת זמן הפעלה לזמן עדכון הקובץ).**
13. **אותה שאלה החזירה תשובה זהה מילה במילה.** הטמפרטורה של המודל הייתה 0.1, ולכן הוא היה כמעט דטרמיניסטי (דמיון 100% בין שתי הרצות). ← טמפרטורה 0.6, הוראה לגוון פתיחה ומבנה, והצעות המשך. אחרי התיקון: דמיון 18%–52% בין הרצות של אותה שאלה, ושאלות שונות מקבלות תשובות שונות (12%–14%).
12. **הדליפה חזרה בשאלות עם מידע חלקי.** אחרי התיקון ב-11 בדקתי שאלות עם תשובה מלאה ולא ראיתי דליפה, אבל בשאלה משולבת ("האם מישהו השקיע בחברה? מהם הסכנות בטיסה לירח?") המודל כתב שוב "המידע שסופק אינו מציין". ← הוראה לומר "אין לי מידע על X" בגוף ראשון. התיקון הראשון שלי יצר באג חדש (שאלה באנגלית קיבלה תשובה בעברית, בגלל דוגמה בעברית בלבד), ולכן הדוגמה ניתנת עכשיו בשתי השפות. **לקח: בודקים גם שאלות עם תשובה חלקית ושאלות באנגלית, ולא רק את המקרים הנוחים.**
10. **הודעה מיותרת `'Avatar'` בצ'אט** כשניסינו להגדיר אווטאר. ← הוסר, כי הוא גם הסתיר את שאלות הדוגמה.

## 11. מגבלות ידועות

- **המכסה החינמית של Gemini** מגבילה: מודלים חזקים יותר נגמרים אחרי כמה שאלות. בשימוש כבד תופיע הודעת מגבלה עם כפתור "נסו שוב".
- **ההיסטוריה של שיחות** לא נתמכת (נדרשת שכבת נתונים שלא הוגדרה). כל שיחה חדשה מתחילה מאפס.
- **הזיכרון של השיחה קיים רק בזמן שהדף פתוח** (עד 4 הסיבובים האחרונים, ב-`cl.user_session`). ברענון הדף השיחה נשכחת. היסטוריית שיחות שנשמרת בין הפעלות לא נבנתה.
- **זיהוי הודעות המשך הוא היוריסטי:** ההודעה נשלחת להבנת הקשר רק אם היא מתחילה במילת הסכמה ("כן", "בטח", "yes"), אם היא קצרה (עד 4 מילים) כשיש שיחה קודמת, או אם יש בה כמה שאלות. הודעה ארוכה שמתייחסת לשיחה קודמת בלי מילת הסכמה עלולה לא להיות מובנת.
- **שאלות על נושאים שלא במאגר** (למשל חורים שחורים, ירח אירופה) ייענו "אין מידע", כי 70 המסמכים לא מכסים אותם.
- **דוחות מחקר מלאים** לא נכללים במאגר, רק עמודי מידע.
- **תמונות שאלות הדוגמה** נטענות ישירות מ-nasa.gov ולא נשמרות מקומית.
- **תוצאות הבדיקות** הן הרצה אחת, והמודל לא דטרמיניסטי לגמרי.
- **התרגום של העמוד הספרדי** נעשה אוטומטית על ידי Claude ולא נבדק על ידי אדם.
- **נתוני הקטעים** כוללים לפעמים רעש של האתר (רשימות ניווט, קישורים), כי החילוץ מבוסס על תגיות HTML.
- **פרויקט עצמאי:** אינו מוצר רשמי של NASA. התשובות נוצרות על ידי מודל שפה ועלולות להכיל שגיאות.

17. **שאלה על ג'מיני 8 נענתה חלקית ומטעה.** במאגר לא היה עמוד על תוכנית ג'מיני, רק אזכורים צדדיים, והתשובה אמרה "אין לי מידע על אבדות" ונקראה כאילו אין אסון. ← נוספו למאגר שלושה עמודים רשמיים (`gemini.txt`, `mission_gemini_viii.txt`, כתבת ההיסטוריה על ג'מיני 8) באמצעות `add_pages.py`, שמוסיף עמודים לאינדקס הקיים בלי לבנות אותו מחדש (224 קטעים במקום 210). בנוסף נוספה לפרומפט הוראה: כשהמידע עונה רק על חלק מהשאלה, עונים על החלק הנתמך ואומרים במשפט אחד מה חסר, ואסור להפוך חוסר מידע להכחשה. **לקח: חוסר מידע במאגר ו"לא קרה" הם שני דברים שונים.**
