# הוספת עמודים חדשים למאגר בלי לבנות את האינדקס מחדש: python add_pages.py <כתובת> [<כתובת> ...]
import re
import sys
import time
from html import unescape
from pathlib import Path

import requests
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

import common  # מגדיר SSL, מפתח ומודל embeddings

HEADERS = {"User-Agent": "Mozilla/5.0 (nasa-rag-student-project)"}


def strip_tags(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def fetch_page(url):
    """מוריד עמוד ומחזיר (כותרת, טקסט): אותן פסקאות, כותרות משנה ופריטי רשימה כמו בהורדה המקורית."""
    html = requests.get(url, headers=HEADERS, timeout=30).text
    main = re.search(r"<main.*?</main>", html, re.S)
    root = main.group(0) if main else html
    title = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    parts = [
        strip_tags(m)
        for m in re.findall(r"<(?:h2|h3|p|li)[^>]*>(.*?)</(?:h2|h3|p|li)>", root, re.S)
    ]
    return strip_tags(title.group(1)) if title else "", "\n\n".join(p for p in parts if len(p) > 40)


def save_page(url, title, text):
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url.split("nasa.gov/")[-1]).strip("_")[:80]
    path = Path("data") / f"{slug}.txt"
    path.write_text(f"{title}\nSource: {url}\n\n{text}", encoding="utf-8")
    return path


def add_to_index(paths):
    docs = [
        Document(text=p.read_text(encoding="utf-8"), metadata={"file_name": p.name})
        for p in paths
    ]
    nodes = SentenceSplitter(chunk_size=512, chunk_overlap=50).get_nodes_from_documents(docs)
    import chromadb

    collection = chromadb.PersistentClient(path="chroma_db").get_collection("nasa")
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(vector_store)
    BATCH = 15
    for i in range(0, len(nodes), BATCH):
        index.insert_nodes(nodes[i : i + BATCH])
        print(f"נשמרו {min(i + BATCH, len(nodes))}/{len(nodes)}")
        time.sleep(20)
    print("בבסיס הנתונים יש קטעים:", collection.count())


if __name__ == "__main__":
    saved = []
    for url in sys.argv[1:]:
        title, text = fetch_page(url)
        path = save_page(url, title, text)
        print("נשמר:", path, "|", title, "|", len(text), "תווים")
        saved.append(path)
    if saved:
        add_to_index(saved)
