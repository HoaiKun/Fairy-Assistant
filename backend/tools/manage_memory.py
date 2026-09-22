import json
import threading
import uuid
from datetime import datetime
from Database.ChromaDB.ChromaDB_Handler import search_memory
from Kit.load_dbconfig import get_db_config
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = get_db_config()


class MemoryManager:

  def __init__(self, db_config: dict):
    self.db_config = db_config
    self.lock = threading.Lock()
    self._init_db()

  def _get_connection(self):
    return psycopg2.connect(**self.db_config)

  def _init_db(self):
    """Khởi tạo extension pgcrypto và 2 bảng chat_sessions, chat_details."""
    with self.lock:
      with self._get_connection() as conn:
        with conn.cursor() as cur:
          # Đảm bảo PostgreSQL có sẵn hàm gen_random_uuid()
          cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

          # Bảng 1: Quản lý phiên hội thoại với session_id kiểu UUID
          cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_sessions (
                            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            title VARCHAR(255) DEFAULT 'New Conversation',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC);
                    """)

          # Bảng 2: Chi tiết từng lượt thoại
          cur.execute("""
                        CREATE TABLE IF NOT EXISTS chat_details (
                            message_id BIGSERIAL PRIMARY KEY,
                            session_id UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                            role VARCHAR(20) NOT NULL,
                            content TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_details_session ON chat_details(session_id, created_at ASC);
                        CREATE INDEX IF NOT EXISTS idx_details_time ON chat_details(created_at DESC);
                    """)
        conn.commit()

  def _validate_uuid(self, val: str) -> str:
    """Kiểm tra và chuẩn hóa UUID string hợp lệ."""
    try:
      return str(uuid.UUID(str(val).strip()))
    except (ValueError, AttributeError, TypeError):
      return ""

  def save_message(
      self,
      session_id: str = "",
      role: str = "user",
      content: str = "",
      session_title: str = "",
  ) -> dict:
    """Lưu tin nhắn vào PostgreSQL.

    Tự động sinh UUID mới nếu session_id trống.
    """
    role = str(role).strip().lower()
    content = str(content).strip()

    if not content:
      return {"status": "error", "message": "Content cannot be empty."}

    # Xử lý session_id: nếu trống thì tự sinh UUIDv4, nếu có thì kiểm tra định dạng
    clean_session_id = self._validate_uuid(session_id)
    if not clean_session_id:
      if session_id.strip():
        return {
            "status": "error",
            "message": (
                f"Invalid UUID format for session_id: '{session_id}'. Must be"
                " standard UUID (8-4-4-4-12 hex chars)."
            ),
        }
      # Sinh UUIDv4 mới nếu không truyền vào
      clean_session_id = str(uuid.uuid4())

    default_title = (
        session_title.strip()
        or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    with self.lock:
      with self._get_connection() as conn:
        with conn.cursor() as cur:
          # Upsert session
          cur.execute(
              """
                        INSERT INTO chat_sessions (session_id, title, updated_at)
                        VALUES (%s::uuid, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (session_id)
                        DO UPDATE SET updated_at = CURRENT_TIMESTAMP;
                    """,
              (clean_session_id, default_title),
          )

          # Insert chat log
          cur.execute(
              """
                        INSERT INTO chat_details (session_id, role, content)
                        VALUES (%s::uuid, %s, %s)
                        RETURNING message_id, to_char(created_at, 'YYYY-MM-DD HH24:MI:SS');
                    """,
              (clean_session_id, role, content),
          )
          row = cur.fetchone()
        conn.commit()

    return {
        "status": "success",
        "message_id": row[0],
        "session_id": clean_session_id,
        "role": role,
        "created_at": row[1],
    }

  def load_history(
      self,
      session_id: str = "",
      start_time: str = "",
      end_time: str = "",
      limit: int = 20,
  ) -> dict:
    """Tải lịch sử hội thoại từ PostgreSQL.

    Hỗ trợ lọc theo session_id (UUID) và khoảng thời gian.
    """
    clauses = []
    params = []

    if session_id.strip():
      clean_session_id = self._validate_uuid(session_id)
      if not clean_session_id:
        return {
            "status": "error",
            "message": f"Invalid UUID format for session_id: '{session_id}'.",
        }
      clauses.append("session_id = %s::uuid")
      params.append(clean_session_id)

    if start_time.strip():
      clauses.append("created_at >= %s::timestamp with time zone")
      params.append(start_time.strip())

    if end_time.strip():
      clauses.append("created_at <= %s::timestamp with time zone")
      params.append(end_time.strip())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # Lấy N tin nhắn mới nhất, sau đó đảo lại theo thứ tự thời gian tăng dần
    query_sql = f"""
            SELECT message_id, session_id::text, role, content, 
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
        "time_range": {"start": start_time or None, "end": end_time or None},
        "count": len(messages),
        "messages": messages,
    }

  def query_semantic_memories(
      self, search_query: str, limit: int = 5
  ) -> dict:
    """Truy vấn ký ức ngữ nghĩa dài hạn từ ChromaDB."""
    results = search_memory(query=search_query, limit=limit)
    return {
        "status": "success",
        "search_query": search_query,
        "count": len(results) if isinstance(results, list) else 0,
        "results": results,
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
    limit: int = 10,
) -> str:
  """Điều phối truy xuất ký ức vector (ChromaDB) và nhật ký trò chuyện (PostgreSQL)."""
  action_clean = str(action).lower().strip()

  try:
    # 1. Truy vấn vector memory (ChromaDB)
    if action_clean == "search_semantic":
      if not search_query.strip():
        return json.dumps(
            {
                "status": "error",
                "message": (
                    "search_query is required for action 'search_semantic'."
                ),
            },
            ensure_ascii=False,
        )
      res = memory_manager.query_semantic_memories(
          search_query=search_query, limit=limit
      )
      return json.dumps(res, ensure_ascii=False)

    # 2. Đọc lịch sử hội thoại (PostgreSQL)
    elif action_clean == "load_history":
      res = memory_manager.load_history(
          session_id=session_id,
          start_time=start_time,
          end_time=end_time,
          limit=limit,
      )
      return json.dumps(res, ensure_ascii=False)

    # 3. Lưu lượt chat mới (PostgreSQL)
    elif action_clean == "save_message":
      if not content.strip():
        return json.dumps(
            {
                "status": "error",
                "message": "content is required for action 'save_message'.",
            },
            ensure_ascii=False,
        )
      res = memory_manager.save_message(
          session_id=session_id,
          role=role,
          content=content,
          session_title=session_title,
      )
      return json.dumps(res, ensure_ascii=False)

    return json.dumps(
        {
            "status": "error",
            "message": (
                f"Invalid action '{action}'. Supported: 'search_semantic',"
                " 'load_history', 'save_message'."
            ),
        },
        ensure_ascii=False,
    )

  except Exception as e:
    return json.dumps(
        {"status": "error", "message": str(e)}, ensure_ascii=False
    )