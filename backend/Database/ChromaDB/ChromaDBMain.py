import uuid
import math
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()

# ==========================================
# 1. CẤU HÌNH & KHỞI TẠO CƠ SỞ DỮ LIỆU
# ==========================================
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="fairy_master_memory",
    embedding_function=embeddings,
    persist_directory="./Database/ChromaDB_Data"
)

# Trọng số tính điểm Re-ranking
WEIGHTS = {
    "semantic": 0.35,       # Độ khớp ngữ nghĩa (Vector DB)
    "importance": 0.20,     # Độ quan trọng (1-10)
    "recency": 0.10,        # Thời gian (Time decay)
    "user_relevant": 0.15,  # Liên quan trực tiếp tới user (Core profile)
    "category_match": 0.05, # Trùng khớp ngữ cảnh hiện tại
    "time_match": 0.15      # Rơi đúng vào khoảng thời gian user đề cập
}

# Danh mục cố định, bao quát các khía cạnh của người dùng
USER_CATEGORIES = [
    "personal_profile",        # Thông tin cốt lõi (tên, tuổi, sở thích cơ bản)
    "tech_and_projects",       # Code, dự án, công cụ (Fairy, Unreal Engine, Web...)
    "hobbies_and_entertainment",# Game, anime, manga, cosplay, music, giải trí
    "lifestyle_and_routine",   # Thói quen sinh hoạt, gym, ăn uống, sức khỏe
    "work_and_study",          # Học tập (HEDSPI, JLPT), công việc (gia sư)
    "relationships",           # Gia đình, bạn bè, các mối quan hệ xã hội
    "general"                  # Các kiến thức chung, sự kiện ngẫu nhiên
]

# ==========================================
# 2. CÁC MODULE XỬ LÝ TRÍ NHỚ CỐT LÕI
# ==========================================

def decay_memory(timestamp_str: Optional[str], now: datetime) -> float:
    """Tính toán hệ số phân rã theo thời gian (0.0 -> 1.0)."""
    if not timestamp_str:
        return 0.0
    try:
        mem_time = datetime.fromisoformat(timestamp_str)
        days_passed = max((now - mem_time).total_seconds() / 86400.0, 0.0)
        # Giảm ~50% giá trị sau 14 ngày
        return math.exp(-0.05 * days_passed)
    except ValueError:
        return 0.0

def classify_memory(content: str) -> Dict[str, Any]:
    """
    (Mô phỏng) Gọi LLM phân loại nội dung để trích xuất Metadata trước khi lưu.
    Thực tế: Bạn dùng LLM (OpenAI JSON mode) phân tích biến `content`.
    """
    return {
        "importance": 7,                # Thang 1-10
        "category": "tech_and_projects",# Chọn 1 trong USER_CATEGORIES
        "user_relevant": True           # True nếu nội dung là về user
    }

def extract_memory(
    content: str, 
    category: str = "general", 
    importance: int = 5, 
    user_relevant: bool = False
) -> str:
    """Xử lý và lưu trí nhớ mới vào DB với Metadata được truyền trực tiếp."""
    
    # Ràng buộc chuẩn hóa dữ liệu
    valid_category = category if category in USER_CATEGORIES else "general"
    clamped_importance = max(1, min(10, int(importance))) # Đảm bảo nằm trong 1-10
    
    metadata = {
        "id": str(uuid.uuid4()),
        "category": valid_category,
        "importance": clamped_importance,
        "user_relevant": bool(user_relevant),
        "timestamp": datetime.now().isoformat(),
        "created_at_unix": time.time()
    }
    
    doc = Document(page_content=content, metadata=metadata)
    vector_store.add_documents([doc], ids=[metadata["id"]])
    return metadata["id"]

def retrieve_memory(query: str, fetch_k: int = 20) -> List[tuple]:
    """Truy xuất thô từ VectorDB (Semantic Search thuần túy)."""
    try:
        return vector_store.similarity_search_with_relevance_scores(query=query, k=fetch_k)
    except Exception:
        docs = vector_store.similarity_search(query=query, k=fetch_k)
        return [(doc, 0.5) for doc in docs]

def rerank_memory(
    raw_results: List[tuple], 
    target_category: Optional[str] = None, 
    time_range: Optional[Tuple[float, float]] = None,
    limit: int = 5, 
    min_final_score: float = 0.4
) -> List[Dict[str, Any]]:
    """Tính toán Composite Score và xếp hạng lại các trí nhớ."""
    now = datetime.now()
    ranked_memories = []

    for doc, sim_score in raw_results:
        meta = doc.metadata
        
        s_sem = max(0.0, sim_score)
        s_time = decay_memory(meta.get("timestamp"), now)
        s_imp = meta.get("importance", 5) / 10.0
        s_usr = 1.0 if meta.get("user_relevant", False) else 0.0
        s_cat = 1.0 if target_category and meta.get("category") == target_category else 0.0
        
        s_time_match = 0.0
        created_at_unix = meta.get("created_at_unix", 0.0)
        if time_range and created_at_unix:
            if time_range[0] <= created_at_unix <= time_range[1]:
                s_time_match = 1.0
        
        final_score = (
            (WEIGHTS["semantic"] * s_sem) +
            (WEIGHTS["recency"] * s_time) +
            (WEIGHTS["importance"] * s_imp) +
            (WEIGHTS["user_relevant"] * s_usr) +
            (WEIGHTS["category_match"] * s_cat) +
            (WEIGHTS["time_match"] * s_time_match)
        )
        
        if final_score >= min_final_score:
            ranked_memories.append({
                "doc_id": meta.get("id"),
                "content": doc.page_content,
                "category": meta.get("category"),
                "final_score": round(final_score, 4),
                "timestamp": meta.get("timestamp")
            })

    ranked_memories.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked_memories[:limit]

def update_memory(
    doc_id: str, 
    new_content: str, 
    category: str, 
    importance: int, 
    user_relevant: bool
) -> bool:
    """Ghi đè nội dung và metadata của một đoạn trí nhớ có sẵn."""
    valid_category = category if category in USER_CATEGORIES else "general"
    clamped_importance = max(1, min(10, int(importance)))
    
    metadata = {
        "id": doc_id,
        "category": valid_category,
        "importance": clamped_importance,
        "user_relevant": bool(user_relevant),
        "timestamp": datetime.now().isoformat(),
        "updated_at_unix": time.time(), # Đánh dấu thời điểm update
        "is_updated": True
    }
    
    doc = Document(page_content=new_content, metadata=metadata)
    try:
        vector_store.update_document(document_id=doc_id, document=doc)
        return True
    except Exception as e:
        print(f"[Error] Lỗi khi cập nhật DB: {e}")
        return False

def delete_memory(doc_id: str) -> bool:
    """Xóa vĩnh viễn một đoạn trí nhớ khỏi hệ thống."""
    try:
        vector_store.delete(ids=[doc_id])
        return True
    except Exception as e:
        print(f"[Error] Lỗi khi xóa DB: {e}")
        return False

# ==========================================
# 3. AUTO-MERGE & CONSOLIDATION
# ==========================================

def merge_memory(doc_ids_to_merge: List[str], merged_content: str) -> str:
    """Gộp nhiều trí nhớ vụn vặt thành một Core Memory."""
    if not doc_ids_to_merge:
        return ""
    new_doc_id = extract_memory(merged_content)
    vector_store.delete(ids=doc_ids_to_merge)
    return new_doc_id

def mock_llm_summarize(contents: List[str]) -> str:
    """(Mô phỏng) Gọi LLM tóm tắt danh sách các sự kiện."""
    return f"Tổng hợp {len(contents)} sự kiện: " + " | ".join([c[:20] for c in contents])

def auto_consolidate_category(category: str, max_docs: int = 15) -> bool:
    """
    Quét và gộp các trí nhớ có tầm quan trọng thấp của một category.
    Dùng làm Background Task chạy ngầm.
    """
    results = vector_store.get(where={"category": category})
    doc_ids = results.get("ids", [])
    
    if len(doc_ids) > max_docs:
        ids_to_merge = []
        contents_to_merge = []
        
        for doc_id, doc, meta in zip(doc_ids, results.get("documents", []), results.get("metadatas", [])):
            if meta.get("importance", 5) < 8:  # Chỉ gộp trí nhớ phụ
                ids_to_merge.append(doc_id)
                contents_to_merge.append(doc)
        
        if len(ids_to_merge) >= 3:
            merged_content = mock_llm_summarize(contents_to_merge)
            merge_memory(ids_to_merge, merged_content)
            return True
            
    return False