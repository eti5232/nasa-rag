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
