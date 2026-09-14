from Database.ChromaDB.ChromaDB_Handler import save_memory, search_memory
from dotenv import load_dotenv
from openai import AsyncOpenAI
import json
load_dotenv()

MemoryHandler = AsyncOpenAI()

def get_dynamic_memories(search_query: str, limit: int = 20):
    search_temp = search_memory(query=search_query, limit=limit)
    print(f"Search results:   {search_temp}")
    return search_temp