import asyncio
from ddgs import DDGS

def _sync_multimedia_search(query: str, search_type: str, max_results: int) -> str:
    """Hàm xử lý đồng bộ chạy ngầm trong Thread"""
    try:
        with DDGS() as ddgs:
            output_lines = [f"Kết quả tìm kiếm [{search_type.upper()}] cho từ khóa: '{query}'\n"]
            count = 0

            # 1. Tìm kiếm Văn bản (Text)
            if search_type == "text":
                results = ddgs.text(query, max_results=max_results)
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    output_lines.append(f"- Tiêu đề: {title}\n  Nội dung: {body}\n  Link: {href}\n")
                    count += 1
                    
            # 2. Tìm kiếm Hình ảnh (Image)
            elif search_type == "image":
                results = ddgs.images(query, max_results=max_results)
                for r in results:
                    title = r.get("title", "")
                    image_url = r.get("image", "")
                    source = r.get("source", "")
                    output_lines.append(f"- Tên ảnh: {title}\n  URL Ảnh: {image_url}\n  Trang gốc: {source}\n")
                    count += 1

            # 3. Tìm kiếm Video
            elif search_type == "video":
                results = ddgs.videos(query, max_results=max_results)
                for r in results:
                    title = r.get("title", "")
                    video_url = r.get("content", "") 
                    description = r.get("description", "")
                    output_lines.append(f"- Tên Video: {title}\n  Mô tả: {description}\n  URL Video: {video_url}\n")
                    count += 1
            
            else:
                return "Lỗi: 'search_type' không hợp lệ. Vui lòng truyền 'text', 'image', hoặc 'video'."

            if count == 0:
                return f"Không tìm thấy kết quả nào cho '{query}' với loại tìm kiếm '{search_type}'."

            return "\n".join(output_lines)
            
    except Exception as e:
        return f"Lỗi truy xuất hệ thống tìm kiếm: {str(e)}"


async def tool_multimedia_search(query: str, search_type: str = "text", max_results: int = 5) -> str:
    """
    Tìm kiếm đa phương tiện trên DuckDuckGo. Trả về Text, hoặc danh sách URL Ảnh/Video.
    (Hàm Wrapper bất đồng bộ an toàn cho FastAPI)
    """
    # Đẩy tác vụ I/O của DuckDuckGo sang một luồng riêng để không làm khựng bot
    return await asyncio.to_thread(_sync_multimedia_search, query, search_type, max_results)