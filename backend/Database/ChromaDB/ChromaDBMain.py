import os
import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_storage")

client  = chromadb.PersistentClient(path=DB_PATH)


embedding_func = embedding_functions.OpenAIEmbeddingFunction(
    api_key = openai_key,
    model_name="text-embedding-3-small"
)

memory_collection = client.get_or_create_collection(
    name = "fairy_episodic_memory",
    embedding_function=embedding_func,
    metadata={"hnsw:space": "cosine"}
)