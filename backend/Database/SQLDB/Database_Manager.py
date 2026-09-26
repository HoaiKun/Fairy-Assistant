import asyncpg
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from Kit.load_dbconfig import get_db_config
# Chuỗi kết nối PostgreSQL (Thay đổi thông tin cho đúng với máy bạn)
DATABASE_URL = get_db_config

class ChatDatabaseManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Khởi tạo Connection Pool và tạo bảng tự động"""
        if not self.pool:
            try:
                # 1. Gọi hàm lấy data từ JSON
                db_config = get_db_config()

                if "dbname" in db_config:
                    db_config["database"] = db_config.pop("dbname")
                # 2. Unpack dictionary trực tiếp vào hàm create_pool bằng cú pháp **
                self.pool = await asyncpg.create_pool(**db_config)
                
                await self._init_tables()
                print("[PostgreSQL] Đã kết nối và khởi tạo CSDL thành công.")
                
            except Exception as e:
                print(f"[LỖI DATABASE] Không thể kết nối PostgreSQL: {e}")

    async def close(self):
        """Đóng kết nối khi tắt app"""
        if self.pool:
            await self.pool.close()
            print("[PostgreSQL] Đã ngắt kết nối an toàn.")

    async def _init_tables(self):
        """Tạo bảng nếu chưa tồn tại"""
        async with self.pool.acquire() as conn:
            # Bảng Session
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ChatSession (
                    id UUID PRIMARY KEY,
                    topic TEXT,
                    date_create TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    lasted_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # Thêm dòng này ngay dưới để tạo sẵn Session mặc định:
            await conn.execute('''
                INSERT INTO ChatSession (id, topic)
                VALUES ('00000000-0000-0000-0000-000000000000', 'Default Session')
                ON CONFLICT (id) DO NOTHING;
            ''')
            
            # Bảng Detail
            # Sử dụng ON DELETE CASCADE để nếu xóa Session thì xóa luôn các chat con
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ChatDetail (
                    id UUID PRIMARY KEY,
                    chat_session_id UUID REFERENCES ChatSession(id) ON DELETE CASCADE,
                    role VARCHAR(50),
                    type VARCHAR(50), 
                    content TEXT,
                    import_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    rag_status BOOLEAN DEFAULT FALSE
                );
            ''')
            
            # Tạo Index để truy vấn tốc độ cao (Rất quan trọng khi bảng phình to lên hàng triệu dòng)
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_session ON ChatDetail(chat_session_id);')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_rag_status ON ChatDetail(rag_status);')

    # ==========================================
    # QUẢN LÝ CHAT SESSION
    # ==========================================
    
    async def create_chat_session(self, topic: str = "New Conversation") -> str:
        """Tạo một phiên chat mới, trả về Session ID"""

        if self.pool is None:
            await self.connect()

        session_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO ChatSession (id, topic) VALUES ($1, $2)',
                session_id, topic
            )
        return session_id

    async def load_all_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Load danh sách các phiên chat (để hiển thị ra UI)"""

        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                'SELECT * FROM ChatSession ORDER BY lasted_update DESC LIMIT $1 OFFSET $2',
                limit, offset
            )
            return [dict(r) for r in records]

    # ==========================================
    # QUẢN LÝ CHAT DETAIL
    # ==========================================

    async def save_chat_detail(self, session_id: str, role: str, msg_type: str, content: str):
        """
        Lưu 1 dòng chat. 
        msg_type: 'chat' (để nhớ), 'function' (lệnh ngầm), 'tool_result' (kết quả tool).
        """

        if self.pool is None:
            await self.connect()
        detail_id = str(uuid.uuid4())
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. Insert chat detail
                await conn.execute(
                    '''INSERT INTO ChatDetail 
                       (id, chat_session_id, role, type, content, rag_status) 
                       VALUES ($1, $2, $3, $4, $5, $6)''',
                    detail_id, session_id, role, msg_type, content, False
                )
                # 2. Cập nhật lại thời gian lasted_update của Session cha
                await conn.execute(
                    'UPDATE ChatSession SET lasted_update = CURRENT_TIMESTAMP WHERE id = $1',
                    session_id
                )
        return detail_id

    async def load_session_chats(self, session_id: str, exclude_types: List[str] = None) -> List[Dict]:
        """
        Load toàn bộ lịch sử chat của 1 Session.
        Cho phép lọc bỏ các type không muốn nhét vào LLM (vd: ẩn 'function_call').
        """

        if self.pool is None:
            await self.connect()

        if exclude_types is None:
            exclude_types = ["function", "tool_result"] # Mặc định loại bỏ các lệnh chạy ngầm của tool
            
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                '''SELECT role, type, content, import_date 
                   FROM ChatDetail 
                   WHERE chat_session_id = $1 AND type != ALL($2::varchar[])
                   ORDER BY import_date ASC''',
                session_id, exclude_types
            )
            return [dict(r) for r in records]

    # ==========================================
    # WORKFLOW TRÍCH XUẤT TRÍ NHỚ (RAG STATUS)
    # ==========================================

    async def get_unprocessed_rag_chats(self, limit: int = 40) -> List[Dict]:
        """Lấy danh sách các câu chat CHƯA được trích xuất vào ChromaDB (rag_status = FALSE)"""

        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as conn:
            # Lọc chỉ lấy type = 'chat' để không trích xuất linh tinh từ tool_result
            records = await conn.fetch(
                '''SELECT id, role, content 
                   FROM ChatDetail 
                   WHERE rag_status = FALSE AND type = 'chat'
                   ORDER BY import_date ASC LIMIT $1''',
                limit
            )
            return [dict(r) for r in records]

    async def mark_rag_processed(self, detail_ids: List[str]):

        if self.pool is None:
            await self.connect()

        """Đánh dấu các tin nhắn đã được học xong -> Không bao giờ bị quét lại nữa"""
        if not detail_ids:
            return
            
        async with self.pool.acquire() as conn:
            # Dùng ANY($1::uuid[]) để update mẻ cực kỳ tối ưu
            await conn.execute(
                'UPDATE ChatDetail SET rag_status = TRUE WHERE id = ANY($1::uuid[])',
                detail_ids
            )

# Khởi tạo instance Global (Singleton) để dùng chung cho toàn bộ App
db_manager = ChatDatabaseManager()