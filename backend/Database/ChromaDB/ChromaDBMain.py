import uuid
import os
import math
from datetime import datetime
from typing import List, Dict, Any
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
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
def search_memory(
    query: str, 
    category: Optional[str] = None, 
    limit: int = 5, 
    min_score: float = 0.25,
    apply_time_decay: bool = True
) -> List[Dict[str, Any]]:
    """
    Truy vấn vector store kết hợp lọc metadata và tính trọng số thời gian (recency).
    """
    # 1. Chuẩn bị metadata filter cho Chroma
    chroma_filter = {"category": category} if category and category != "all" else None

    # Fetch rộng hơn limit một chút để sau khi re-rank theo thời gian vẫn đủ top kết quả
    fetch_k = min(limit * 2, 20)
    
    try:
        results = vector_store.similarity_search_with_relevance_scores(
            query=query,
            k=fetch_k,
            filter=chroma_filter
        )
    except Exception:
        docs = vector_store.similarity_search(query=query, k=limit, filter=chroma_filter)
        results = [(doc, 0.5) for doc in docs]

    now = datetime.now()
    ranked_memories = []

    for doc, sim_score in results:
        if sim_score < min_score:
            continue

        raw_timestamp = doc.metadata.get("timestamp")
        final_score = sim_score

        # 2. Time-decay: Giảm nhẹ điểm của thông tin quá cũ nếu cùng độ khớp ngữ nghĩa
        # Công thức: score * exp(-decay_rate * days_passed)
        if apply_time_decay and raw_timestamp:
            try:
                mem_time = datetime.fromisoformat(raw_timestamp)
                days_passed = max((now - mem_time).total_seconds() / 86400.0, 0.0)
                # Hệ số phân rã chậm (sau ~180 ngày điểm giảm ~10%)
                decay = math.exp(-0.0006 * days_passed)
                final_score = sim_score * decay
            except Exception:
                pass

        ranked_memories.append({
            "doc_id": doc.metadata.get("id"),
            "content": doc.page_content,
            "category": doc.metadata.get("category", "general"),
            "timestamp": raw_timestamp,
            "raw_score": round(sim_score, 3),
            "final_score": round(final_score, 3)
        })

    # 3. Sắp xếp lại theo điểm tổng hợp
    ranked_memories.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked_memories[:limit]

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