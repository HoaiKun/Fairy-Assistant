import uuid
import os
from datetime import datetime
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

# 1. Khởi tạo Embeddings & Kết nối ChromaDB
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="fairy_master_memory",
    embedding_function=embeddings,
    persist_directory="./Database/ChromaDB_Data" # DB sẽ được tạo tại đây
)

# 2. Các hàm tương tác Database thuần
def search_memory(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Tìm kiếm trí nhớ liên quan đến câu chat hiện tại"""
    # Trả về các Document kèm điểm số (càng gần 1 càng tốt)
    results = vector_store.similarity_search_with_relevance_scores(query, k=limit)
    
    formatted_results = []
    for doc, score in results:
        # Lọc bớt các kết quả không liên quan (điểm quá thấp)
        if score < 0.3:
            continue
            
        formatted_results.append({
            "doc_id": doc.metadata.get("id"),
            "content": doc.page_content,
            "category": doc.metadata.get("category"),
            "timestamp": doc.metadata.get("timestamp"),
            "score": round(score, 3)
        })
    return formatted_results

def insert_memory(content: str, category: str = "general") -> str:
    """Thêm trí nhớ mới"""
    doc_id = str(uuid.uuid4())
    doc = Document(
        page_content=content,
        metadata={
            "id": doc_id, 
            "timestamp": datetime.now().isoformat(), 
            "category": category
        }
    )
    vector_store.add_documents([doc], ids=[doc_id])
    return doc_id

def update_memory_doc(doc_id: str, new_content: str, category: str = "general") -> bool:
    """Ghi đè trí nhớ cũ bằng ID"""
    doc = Document(
        page_content=new_content,
        metadata={
            "id": doc_id, 
            "timestamp": datetime.now().isoformat(), 
            "category": category,
            "is_updated": True
        }
    )
    vector_store.update_document(document_id=doc_id, document=doc)
    return True

def delete_memory_doc(doc_id: str) -> bool:
    """Xóa hoàn toàn một trí nhớ"""
    vector_store.delete(ids=[doc_id])
    return True