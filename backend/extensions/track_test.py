import time
from extensions.app_tracking import AppBehaviorTracker

# 1. Điền thông số PostgreSQL cục bộ của bạn
PG_CONFIG = {
    "dbname": "fairy_db",
    "user": "postgres",
    "password": "123456",
    "host": "localhost",
    "port": 5432,
}

print("=== ĐANG KHỞI ĐỘNG TRACKER ===")
# Khởi tạo với idle_threshold = 15 giây để test AFK nhanh (thay vì 180s mặc định)
tracker = AppBehaviorTracker(db_config=PG_CONFIG, idle_threshold_seconds=15)
tracker.start()

print("-> Tracker đã chạy ngầm.")
print("-> HÃY THỬ:")
print("   1. Mở trình duyệt xem YouTube hoặc GitHub khoảng 10-15s.")
print("   2. Chuyển sang VS Code hoặc Notepad gõ vài chữ.")
print("   3. Buông chuột, không chạm bàn phím trong 15s để test AFK.")
print("--------------------------------------------------")

try:
    # Vòng lặp in trạng thái trực tiếp mỗi 3 giây trong vòng 60 giây
    for remaining in range(20, 0, -1):
        idle_time = tracker._get_idle_seconds()
        app, title = tracker._get_active_window_info()
        category = tracker._classify_activity(app, title)
        afk_status = "[AFK]" if tracker.is_afk else "[ACTIVE]"

        print(
            f"[{remaining * 3:02d}s] {afk_status} Idle: {int(idle_time)}s | App: {app} ({category}) | Title: {title[:40]}..."
        )
        time.sleep(3)

except KeyboardInterrupt:
    print("\nĐã dừng test sớm.")

print("\n=== Aggregated results recorded in PostgreSQL ===")
# Đọc chuỗi format context mà Fairy sẽ nhìn thấy
summary_prompt = tracker.get_recent_sessions_context()
print(summary_prompt)
summary_prompt = tracker.get_daily_top_usage_context()
print(summary_prompt)

tracker.running = False