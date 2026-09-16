import ctypes
from datetime import date, datetime
import os
import threading
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import psutil
import pygetwindow as gw
from win32 import win32process
from Kit.load_dbconfig import get_db_config

# Win32 API bắt idle time (chuột/phím)
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32



DB_CONFIG = get_db_config()



class LASTINPUTINFO(ctypes.Structure):
  _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class AppBehaviorTracker:

  def __init__(self, db_config: dict, idle_threshold_seconds: int = 180):

    print("INITATING APP Tracking")
    self.db_config = db_config
    self.idle_threshold = idle_threshold_seconds
    self.lock = threading.Lock()
    self.running = True

    # Trạng thái session hiện tại trong RAM
    self.current_app = "Desktop"
    self.current_title = "Desktop"
    self.current_exe_path = ""
    self.session_start_time = datetime.now()
    self.is_afk = False

    self._init_db()

  def _get_connection(self):
    return psycopg2.connect(**self.db_config)

  def _init_db(self):
    """Khởi tạo schema 2 tầng và migration cột exe_path nếu chưa có."""
    with self._get_connection() as conn:
      with conn.cursor() as cur:
        # Bảng 1: Lịch sử từng phiên (Session Logs)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS app_sessions (
                        session_id BIGSERIAL PRIMARY KEY,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP NOT NULL,
                        duration_seconds INTEGER GENERATED ALWAYS AS (
                            EXTRACT(EPOCH FROM (end_time - start_time))::INTEGER
                        ) STORED,
                        app_name VARCHAR(100) NOT NULL,
                        exe_path TEXT,
                        window_title TEXT,
                        category VARCHAR(50) DEFAULT 'Uncategorized',
                        is_afk BOOLEAN DEFAULT FALSE
                    );
                    ALTER TABLE app_sessions ADD COLUMN IF NOT EXISTS exe_path TEXT;
                    CREATE INDEX IF NOT EXISTS idx_sessions_time ON app_sessions(start_time, end_time);
                    CREATE INDEX IF NOT EXISTS idx_sessions_app ON app_sessions(app_name);
                """)

        # Bảng 2: Tổng hợp nhanh theo ngày (Daily Summary)
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS app_daily_summary (
                        record_date DATE NOT NULL,
                        app_name VARCHAR(100) NOT NULL,
                        exe_path TEXT,
                        category VARCHAR(50) DEFAULT 'Uncategorized',
                        total_duration_minutes REAL DEFAULT 0,
                        session_count INTEGER DEFAULT 1,
                        late_night_minutes REAL DEFAULT 0,
                        last_window_title TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (record_date, app_name)
                    );
                    ALTER TABLE app_daily_summary ADD COLUMN IF NOT EXISTS exe_path TEXT;
                """)
      conn.commit()

  def _get_idle_seconds(self) -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(info)):
      millis = kernel32.GetTickCount() - info.dwTime
      return millis / 1000.0
    return 0.0

  def _get_active_window_info(self) -> tuple[str, str, str]:
    """Lấy tên app, tiêu đề cửa sổ và đường dẫn file thực thi tuyệt đối."""
    try:
      win = gw.getActiveWindow()
      if not win or not win.title.strip():
        return "Desktop", "Desktop", ""
      title = win.title.strip()
      _, pid = win32process.GetWindowThreadProcessId(win._hWnd)
      proc = psutil.Process(pid)
      proc_name = proc.name()

      try:
        exe_path = proc.exe()
      except (psutil.AccessDenied, psutil.NoSuchProcess):
        exe_path = ""

      return proc_name, title, exe_path
    except Exception:
      return "Desktop", "Desktop", ""

  def _classify_activity(self, app_name: str, title: str) -> str:
    """Phân loại ngữ cảnh động dựa trên Process Name và Window Title."""
    app_lower = app_name.lower()
    title_lower = title.lower()

    if any(
        k in app_lower
        for k in ["game", "steam", "genshin", "starrail", "wuwa", "riot"]
    ):
      return "Gaming"

    if any(b in app_lower for b in ["chrome", "edge", "firefox", "brave"]):
      if any(
          w in title_lower
          for w in ["github", "stackoverflow", "docs", "chatgpt", "gemini"]
      ):
        return "Technical Research"
      if any(
          w in title_lower
          for w in ["youtube", "bilibili", "netflix", "anime", "facebook"]
      ):
        return "Entertainment"
      return "Browsing"

    if any(
        ide in app_lower
        for ide in ["code", "devenv", "pycharm", "unreal", "blender", "rider"]
    ):
      return "Development / Creative"

    if any(comm in app_lower for comm in ["discord", "zalo", "telegram"]):
      return "Communication"

    return "Productivity / Other"

  def _flush_session(
      self,
      app_name: str,
      title: str,
      exe_path: str,
      start_dt: datetime,
      end_dt: datetime,
  ):
    """Ghi session vào app_sessions và cập nhật exe_path vào app_daily_summary."""
    duration_secs = (end_dt - start_dt).total_seconds()
    if duration_secs < 5 or app_name in [
        "Desktop",
        "Taskmgr.exe",
        "SearchHost.exe",
        "",
    ]:
      return

    category = self._classify_activity(app_name, title)
    duration_mins = duration_secs / 60.0
    record_date = start_dt.date()

    late_mins = 0.0
    if 0 <= start_dt.hour < 5:
      late_mins = duration_mins

    try:
      with self.lock:
        with self._get_connection() as conn:
          with conn.cursor() as cur:
            # 1. Lưu log chi tiết kèm exe_path
            cur.execute(
                """
                            INSERT INTO app_sessions (
                                start_time, end_time, app_name, exe_path, window_title, category, is_afk
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, FALSE);
                        """,
                (start_dt, end_dt, app_name, exe_path, title, category),
            )

            # 2. Cập nhật bảng tổng hợp ngày (ghi nhận và làm mới exe_path)
            cur.execute(
                """
                            INSERT INTO app_daily_summary (
                                record_date, app_name, exe_path, category, total_duration_minutes, 
                                session_count, late_night_minutes, last_window_title, last_updated
                            )
                            VALUES (%s, %s, %s, %s, %s, 1, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (record_date, app_name)
                            DO UPDATE SET
                                exe_path = COALESCE(EXCLUDED.exe_path, app_daily_summary.exe_path),
                                total_duration_minutes = app_daily_summary.total_duration_minutes + EXCLUDED.total_duration_minutes,
                                session_count = app_daily_summary.session_count + 1,
                                late_night_minutes = app_daily_summary.late_night_minutes + EXCLUDED.late_night_minutes,
                                last_window_title = EXCLUDED.last_window_title,
                                last_updated = CURRENT_TIMESTAMP;
                        """,
                (
                    record_date,
                    app_name,
                    exe_path,
                    category,
                    duration_mins,
                    late_mins,
                    title,
                ),
            )
          conn.commit()
    except Exception:
      pass

  def _monitor_loop(self):
    """Vòng lặp quét ứng dụng mỗi 5 giây."""
    while self.running:
      idle_seconds = self._get_idle_seconds()
      self.is_afk = idle_seconds >= self.idle_threshold
      app_name, title, exe_path = self._get_active_window_info()
      now = datetime.now()

      if app_name != self.current_app or self.is_afk:
        if not self.is_afk:
          self._flush_session(
              self.current_app,
              self.current_title,
              self.current_exe_path,
              self.session_start_time,
              now,
          )
        self.current_app = "AFK" if self.is_afk else app_name
        self.current_title = "User Away" if self.is_afk else title
        self.current_exe_path = "" if self.is_afk else exe_path
        self.session_start_time = now

      time.sleep(5)

  def start(self):
    worker = threading.Thread(target=self._monitor_loop, daemon=True)
    worker.start()

  def find_app_path(self, query: str) -> str | None:
    """Tra cứu đường dẫn exe trong DB dựa vào tên app hoặc window_title gần nhất."""
    cleaned_query = f"%{query.strip().lower()}%"
    try:
      with self.lock:
        with self._get_connection() as conn:
          with conn.cursor() as cur:
            cur.execute(
                """
                            SELECT exe_path 
                            FROM app_daily_summary 
                            WHERE (LOWER(app_name) LIKE %s OR LOWER(last_window_title) LIKE %s)
                              AND exe_path IS NOT NULL 
                              AND exe_path != ''
                            ORDER BY last_updated DESC 
                            LIMIT 1;
                        """,
                (cleaned_query, cleaned_query),
            )
            row = cur.fetchone()
            if row and row[0] and os.path.exists(row[0]):
              return row[0]

            # Fallback tra cứu trong lịch sử session chi tiết
            cur.execute(
                """
                            SELECT exe_path 
                            FROM app_sessions 
                            WHERE (LOWER(app_name) LIKE %s OR LOWER(window_title) LIKE %s)
                              AND exe_path IS NOT NULL 
                              AND exe_path != ''
                            ORDER BY end_time DESC 
                            LIMIT 1;
                        """,
                (cleaned_query, cleaned_query),
            )
            row = cur.fetchone()
            if row and row[0] and os.path.exists(row[0]):
              return row[0]
    except Exception:
      pass
    return None

  def get_recent_sessions_context(self, limit: int = 10) -> str:
    sessions = []
    try:
      with self.lock:
        with self._get_connection() as conn:
          with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                                SELECT app_name, window_title, category,
                                        ROUND(duration_seconds / 60.0, 1) as mins,
                                        to_char(start_time, 'HH24:MI') as t_start,
                                        to_char(end_time, 'HH24:MI') as t_end
                                FROM app_sessions
                                ORDER BY end_time DESC
                                LIMIT %s;
                            """,
                (limit,),
            )
            sessions = cur.fetchall()
    except Exception:
      pass

    if not sessions:
      return "[RECENT ACTIVITY SESSIONS]: No recent sessions recorded."

    lines = [
        f"- [{s['t_start']} -> {s['t_end']}] {s['app_name']} ({s['mins']}m) |"
        f" Category: {s['category']} | Title: \"{s['window_title'][:60]}\""
        for s in sessions
    ]
    return "[RECENT ACTIVITY SESSIONS]:\n" + "\n".join(lines)

  def get_daily_top_usage_context(self, limit: int = 100) -> str:
    today = date.today()
    top_apps = []
    try:
      with self.lock:
        with self._get_connection() as conn:
          with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                                SELECT app_name, category, 
                                        ROUND(total_duration_minutes::numeric, 1) as total_mins,
                                        session_count, 
                                        ROUND(late_night_minutes::numeric, 1) as late_mins
                                FROM app_daily_summary
                                WHERE record_date = %s
                                ORDER BY total_duration_minutes DESC
                                LIMIT %s;
                            """,
                (today, limit),
            )
            top_apps = cur.fetchall()
    except Exception:
      pass

    if not top_apps:
      return "[TODAY USAGE STATS]: No usage recorded today."

    lines = [
        f"- {row['app_name']} ({row['category']}): {row['total_mins']}m across"
        f" {row['session_count']} sessions (Late night: {row['late_mins']}m)"
        for row in top_apps
    ]
    return f"[TODAY TOP USAGE (Limit {limit})]:\n" + "\n".join(lines)


app_tracker = AppBehaviorTracker(
    db_config=DB_CONFIG, idle_threshold_seconds=15
)
app_tracker.start()