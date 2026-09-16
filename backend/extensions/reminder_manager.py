import json
from pathlib import Path
import re
import threading
import time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from Kit.load_dbconfig import get_db_config




class ReminderManager:
    def __init__(self, callback_func=None):
        self.callback_func = callback_func
        self._is_running = False
        self._thread = None
        self.db_config = self._load_config()
        self._init_db()

    def _load_config(self) -> dict:
        config_path = get_db_config()
        return config_path

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    def _init_db(self):
        """Automatically create the fairy_reminders table and required indexes if not present."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS fairy_reminders (
            reminder_id BIGSERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            details TEXT DEFAULT '',
            reminder_type VARCHAR(50) DEFAULT 'reminder',
            remind_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            is_triggered BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            triggered_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE INDEX IF NOT EXISTS idx_fairy_reminders_polling 
        ON fairy_reminders (is_triggered, remind_at);
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_sql)
                    conn.commit()
        except Exception as e:
            print(f"[ReminderManager] Database initialization failed: {e}")

    def parse_time(self, time_query: str) -> datetime:
        """Parse natural time strings into a specific datetime object."""
        now = datetime.now()
        s = str(time_query).strip().lower()

        # Absolute time matches (e.g., '08:30', '19:00', '7h', '21h30')
        clock_match = re.match(r"^(\d{1,2})[:h](\d{2})?$", s)
        if clock_match:
            hours = int(clock_match.group(1))
            minutes = int(clock_match.group(2)) if clock_match.group(2) else 0
            target = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target

        # Relative time offset calculations
        delta_seconds = 0
        hour_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|giờ|tiếng|hour|hours)", s)
        if hour_m:
            delta_seconds += float(hour_m.group(1)) * 3600

        min_m = re.search(r"(\d+)\s*(?:m|p|phút|min|minute|minutes)", s)
        if min_m:
            delta_seconds += int(min_m.group(1)) * 60

        sec_m = re.search(r"(\d+)\s*(?:s|giây|sec|second|seconds)", s)
        if sec_m:
            delta_seconds += int(sec_m.group(1))

        # Raw numeric fallback: <= 120 means minutes, > 120 means seconds
        if s.isdigit():
            val = int(s)
            delta_seconds = val * 60 if val <= 120 else val

        if delta_seconds <= 0:
            delta_seconds = 60

        return now + timedelta(seconds=delta_seconds)

    def add_reminder(self, title: str, time_query: str, details: str = "", reminder_type: str = "reminder") -> dict:
        """Insert a new reminder record."""
        target_time = self.parse_time(time_query)
        sql = """
            INSERT INTO fairy_reminders (title, details, reminder_type, remind_at)
            VALUES (%s, %s, %s, %s)
            RETURNING reminder_id, title, details, remind_at;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (title, details, reminder_type, target_time))
                result = cur.fetchone()
                conn.commit()
                return result

    def cancel_reminder(self, reminder_id: int = None, keyword: str = "") -> list:
        """Cancel pending reminders by exact ID, matching keyword, or next immediate task."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if reminder_id:
                    sql = """
                        DELETE FROM fairy_reminders 
                        WHERE reminder_id = %s AND is_triggered = FALSE
                        RETURNING reminder_id, title, details, remind_at;
                    """
                    cur.execute(sql, (reminder_id,))
                elif keyword:
                    sql = """
                        DELETE FROM fairy_reminders 
                        WHERE is_triggered = FALSE AND (title ILIKE %s OR details ILIKE %s)
                        RETURNING reminder_id, title, details, remind_at;
                    """
                    cur.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
                else:
                    sql = """
                        DELETE FROM fairy_reminders 
                        WHERE reminder_id = (
                            SELECT reminder_id FROM fairy_reminders 
                            WHERE is_triggered = FALSE 
                            ORDER BY remind_at ASC 
                            LIMIT 1
                        )
                        RETURNING reminder_id, title, details, remind_at;
                    """
                    cur.execute(sql)

                deleted_rows = cur.fetchall()
                conn.commit()
                return deleted_rows

    def list_pending(self) -> list:
        """Retrieve all active pending reminders ordered chronologically."""
        sql = """
            SELECT reminder_id, title, details, reminder_type, remind_at 
            FROM fairy_reminders 
            WHERE is_triggered = FALSE 
            ORDER BY remind_at ASC;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                return cur.fetchall()

    def _worker_loop(self):
        """Polling loop running every 2 seconds to trigger due reminders."""
        while self._is_running:
            try:
                now = datetime.now()
                select_sql = """
                    SELECT reminder_id, title, details, reminder_type, remind_at
                    FROM fairy_reminders
                    WHERE is_triggered = FALSE AND remind_at <= %s
                    ORDER BY remind_at ASC;
                """
                triggered_items = []
                with self._get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cur:
                        cur.execute(select_sql, (now,))
                        triggered_items = cur.fetchall()

                        if triggered_items:
                            ids = [item["reminder_id"] for item in triggered_items]
                            cur.execute(
                                """
                                UPDATE fairy_reminders 
                                SET is_triggered = TRUE, triggered_at = NOW() 
                                WHERE reminder_id = ANY(%s);
                                """,
                                (ids,)
                            )
                            conn.commit()

                for item in triggered_items:
                    if self.callback_func:
                        self.callback_func(item)
                    else:
                        print(f"[FAIRY REMINDER] Reminder triggered: {item['title']} - {item['details']}")

            except Exception as e:
                print(f"[Reminder Worker Error] {e}")

            time.sleep(2)

    def start_worker(self):
        if not self._is_running:
            self._is_running = True
            self._thread = threading.Thread(target=self._worker_loop, name="FairyReminderWorker", daemon=True)
            self._thread.start()

    def stop_worker(self):
        self._is_running = False


reminder_manager = ReminderManager()
reminder_manager.start_worker()

