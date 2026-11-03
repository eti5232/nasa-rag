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
