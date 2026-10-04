from typing import Optional
from Database.ChromaDB.ChromaDBMain import retrieve_memory, rerank_memory, extract_memory, update_memory, delete_memory

def memory_handler(
    action: str,
    query: Optional[str] = None,
    content: Optional[str] = None,
    doc_id: Optional[str] = None,
    category: str = "general",
    importance: int = 5,
    user_relevant: bool = True,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None
) -> str:
    """
    Công cụ ĐA NĂNG để thao tác với bộ nhớ dài hạn của trợ lý. 
    Hành động (action) quyết định công cụ này sẽ làm gì.
    
    Args:
        action (str): BẮT BUỘC chọn 1 trong: ['search', 'save', 'update', 'delete'].
        query (str): Cần thiết khi action='search'. Từ khóa tìm kiếm.
        content (str): Cần thiết khi action='save' hoặc 'update'. Sự thật/nội dung cần ghi (dùng ngôi thứ 3).
        doc_id (str): Cần thiết khi action='update' hoặc 'delete'. Lấy được ID từ action='search'.
        category (str): Phân loại. Chọn 1 trong ['personal_profile', 'tech_and_projects', 'hobbies_and_entertainment', 'lifestyle_and_routine', 'work_and_study', 'relationships', 'general'].
        importance (int): Thang điểm 1-10 về độ quan trọng của trí nhớ.
        user_relevant (bool): True nếu liên quan trực tiếp đến bản thân người dùng.
        start_time, end_time (float): UNIX timestamp để khoanh vùng tìm kiếm (chỉ dùng cho 'search').
    """
    
    # -------------------------
    # 1. TÌM KIẾM (SEARCH)
    # -------------------------
    if action == "search":
        if not query:
            return "Thất bại: action='search' yêu cầu tham số 'query'."
        
        time_range = (start_time, end_time) if start_time and end_time else None
        
        # Nếu category là general, coi như không filter khắt khe category để tìm rộng hơn
        target_cat = category if category != "general" else None 
        
        raw_docs = retrieve_memory(query, fetch_k=20)
        results = rerank_memory(raw_docs, target_category=target_cat, time_range=time_range, limit=5)
        
        if not results:
            return "Không tìm thấy ký ức nào liên quan."
            
        formatted_results = []
        for r in results:
            time_str = r['timestamp'][:10] # Chỉ lấy YYYY-MM-DD
            formatted_results.append(f"- [{time_str}] {r['content']} (Score: {r['final_score']} - ID: {r['doc_id']})")
            
        return "Ký ức tìm thấy:\n" + "\n".join(formatted_results)

    # -------------------------
    # 2. LƯU MỚI (SAVE)
    # -------------------------
    elif action == "save":
        if not content:
            return "Thất bại: action='save' yêu cầu tham số 'content'."
            
        new_id = extract_memory(
            content=content, 
            category=category, 
            importance=importance, 
            user_relevant=user_relevant
        )
        return f"Đã lưu trí nhớ thành công! [Cat: {category} | Imp: {importance}/10] - ID: {new_id}"

    # -------------------------
    # 3. CẬP NHẬT (UPDATE)
    # -------------------------
    elif action == "update":
        if not doc_id or not content:
            return "Thất bại: action='update' yêu cầu tham số 'doc_id' và 'content' mới."
            
        success = update_memory(
            doc_id=doc_id, 
            new_content=content, 
            category=category, 
            importance=importance, 
            user_relevant=user_relevant
        )
        if success:
            return f"Đã cập nhật ký ức {doc_id} thành công. Nội dung mới: {content}"
        return f"Lỗi: Không thể cập nhật ID {doc_id} (có thể ID không tồn tại)."

    # -------------------------
    # 4. XÓA BỎ (DELETE)
    # -------------------------
    elif action == "delete":
        if not doc_id:
            return "Thất bại: action='delete' yêu cầu tham số 'doc_id'."
            
        success = delete_memory(doc_id)
        if success:
            return f"Đã xóa vĩnh viễn ID {doc_id} khỏi hệ thống."
        return f"Lỗi: Không tìm thấy ID {doc_id} để xóa."

    # -------------------------
    # ERROR FALLBACK
    # -------------------------
    else:
        return f"Thất bại: Hành động '{action}' không hợp lệ. Chỉ chấp nhận 'search', 'save', 'update', 'delete'."