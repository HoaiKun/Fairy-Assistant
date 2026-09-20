import json
import threading
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from Kit.load_dbconfig import get_db_config
from Database.ChromaDB.ChromaDB_Handler import search_memory



DB_CONFIG = get_db_config()


class MemoryManager:
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    def _init_db(self):
        """Khởi tạo 2 bảng chat_sessions và chat_details nếu chưa tồn tại."""
        with self.lock:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Bảng 1: Quản lý phiên hội thoại
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_sessions (
                            session_id VARCHAR(64) PRIMARY KEY,
                            title VARCHAR(255) DEFAULT 'New Conversation',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC);
                    """)

                    # Bảng 2: Chi tiết từng lượt thoại
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_details (
                            message_id BIGSERIAL PRIMARY KEY,
                            session_id VARCHAR(64) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                            role VARCHAR(20) NOT NULL,
                            content TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_details_session ON chat_details(session_id, created_at ASC);
                        CREATE INDEX IF NOT EXISTS idx_details_time ON chat_details(created_at DESC);
                    """)
                conn.commit()

    def save_message(self, session_id: str, role: str, content: str, session_title: str = "") -> dict:
        """Lưu tin nhắn vào PostgreSQL. Tự động upsert session_id."""
        session_id = str(session_id).strip()
        role = str(role).strip().lower()
        content = str(content).strip()

        if not session_id or not content:
            return {"status": "error", "message": "session_id và content không được để trống."}

        default_title = session_title.strip() or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with self.lock:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Upsert session
                    cur.execute("""
                        INSERT INTO chat_sessions (session_id, title, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (session_id)
                        DO UPDATE SET updated_at = CURRENT_TIMESTAMP;
                    """, (session_id, default_title))

                    # Insert chat log
                    cur.execute("""
                        INSERT INTO chat_details (session_id, role, content)
                        VALUES (%s, %s, %s)
                        RETURNING message_id, created_at;
                    """, (session_id, role, content))
                    row = cur.fetchone()
                conn.commit()

        return {
            "status": "success",
            "message_id": row[0],
            "session_id": session_id,
            "role": role,
            "created_at": str(row[1])
        }

    def load_history(
        self,
        session_id: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: int = 20
    ) -> dict:
        """
        Tải lịch sử hội thoại từ PostgreSQL.
        Hỗ trợ lọc theo session_id và khoảng thời gian (start_time, end_time).
        """
        clauses = []
        params = []

        if session_id.strip():
            clauses.append("session_id = %s")
            params.append(session_id.strip())

        if start_time.strip():
            clauses.append("created_at >= %s::timestamp")
            params.append(start_time.strip())

        if end_time.strip():
            clauses.append("created_at <= %s::timestamp")
            params.append(end_time.strip())

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        query_sql = f"""
            SELECT message_id, session_id, role, content, 
                   to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') as time
            FROM (
                SELECT message_id, session_id, role, content, created_at
                FROM chat_details
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s
            ) sub
            ORDER BY created_at ASC;
        """
        params.append(limit)

        with self.lock:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query_sql, tuple(params))
                    messages = cur.fetchall()

        return {
            "status": "success",
            "session_id": session_id or "all",
            "time_range": {
                "start": start_time or None,
                "end": end_time or None
            },
            "count": len(messages),
            "messages": messages
        }

    def query_semantic_memories(self, search_query: str, limit: int = 5) -> dict:
        """Truy vấn ký ức ngữ nghĩa dài hạn từ ChromaDB."""
        results = search_memory(query=search_query, limit=limit)
        return {
            "status": "success",
            "search_query": search_query,
            "count": len(results) if isinstance(results, list) else 0,
            "results": results
        }


# Khởi tạo singleton instance
memory_manager = MemoryManager(db_config=DB_CONFIG)


# ==============================================================================
# HÀM WRAPPER ĐIỀU PHỐI TOOL DÀNH CHO FAIRY CORE BRAIN
# ==============================================================================

def manage_memory(
    action: str,
    search_query: str = "",
    session_id: str = "",
    role: str = "user",
    content: str = "",
    session_title: str = "",
    start_time: str = "",
    end_time: str = "",
    limit: int = 10
) -> str:
    """Điều phối truy xuất ký ức vector (ChromaDB) và nhật ký trò chuyện (PostgreSQL)."""
    action_clean = str(action).lower().strip()

    try:
        # 1. Truy vấn vector memory (ChromaDB)
        if action_clean == "search_semantic":
            if not search_query.strip():
                return json.dumps({
                    "status": "error",
                    "message": "search_query is required for action 'search_semantic'."
                }, ensure_ascii=False)
            res = memory_manager.query_semantic_memories(search_query=search_query, limit=limit)
            return json.dumps(res, ensure_ascii=False)

        # 2. Đọc lịch sử hội thoại (PostgreSQL)
        elif action_clean == "load_history":
            res = memory_manager.load_history(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            return json.dumps(res, ensure_ascii=False)

        # 3. Lưu lượt chat mới (PostgreSQL)
        elif action_clean == "save_message":
            if not session_id.strip() or not content.strip():
                return json.dumps({
                    "status": "error",
                    "message": "session_id and content are required for action 'save_message'."
                }, ensure_ascii=False)
            res = memory_manager.save_message(
                session_id=session_id,
                role=role,
                content=content,
                session_title=session_title
            )
            return json.dumps(res, ensure_ascii=False)

        return json.dumps({
            "status": "error",
            "message": f"Invalid action '{action}'. Supported: 'search_semantic', 'load_history', 'save_message'."
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)