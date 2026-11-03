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
