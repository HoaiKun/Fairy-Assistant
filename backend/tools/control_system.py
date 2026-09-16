import ctypes
import json
import re
import subprocess
import math
user32 = ctypes.windll.user32

# Mã Virtual-Key Win32 cho phím Multimedia
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _press_key(vk_code: int, times: int = 1):
    """Giả lập bấm phím Multimedia qua user32 API cấp OS."""
    for _ in range(times):
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def _parse_duration_to_seconds(val_str: str) -> int:
    """Chuyển đổi chuỗi thời gian tự nhiên (30m, 1h, 1 tiếng, 45 phút,...) sang giây."""
    if not val_str:
        return 0

    s = str(val_str).strip().lower()

    # Nếu truyền số thuần: nếu <= 120 thì coi như phút, > 120 coi như giây
    if s.isdigit():
        num = int(s)
        return num * 60 if num <= 120 else num

    total_seconds = 0

    # Bắt giờ: '1h', '2 giờ', '1.5 tiếng'
    hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|giờ|tiếng|hour)", s)
    if hour_match:
        total_seconds += int(float(hour_match.group(1)) * 3600)

    # Bắt phút: '30m', '45p', '20 phút'
    min_match = re.search(r"(\d+)\s*(?:m|p|phút|min)", s)
    if min_match:
        total_seconds += int(min_match.group(1)) * 60

    # Bắt giây: '30s', '45 giây'
    sec_match = re.search(r"(\d+)\s*(?:s|giây|sec)", s)
    if sec_match:
        total_seconds += int(sec_match.group(1))

    return total_seconds if total_seconds > 0 else 60


def control_system(action: str, value: str = "") -> str:
    """Điều khiển hệ thống Windows an toàn: Quản lý nguồn, hẹn giờ, âm lượng."""
    action = action.lower().strip()

    try:
        # 1. Hẹn giờ Tắt máy (Shutdown)
        if action == "shutdown":
            seconds = _parse_duration_to_seconds(value) if value else 60
            # Hủy lệnh hẹn giờ trước đó (nếu có) để tránh lỗi xung đột
            subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
            subprocess.run(["shutdown", "/s", "/t", str(seconds)], capture_output=True, text=True)
            mins_display = round(seconds / 60, 1)
            return json.dumps({
                "status": "success",
            }, ensure_ascii=False)

        # 2. Hẹn giờ Khởi động lại (Restart)
        elif action == "restart":
            seconds = _parse_duration_to_seconds(value) if value else 60
            subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
            subprocess.run(["shutdown", "/r", "/t", str(seconds)], capture_output=True, text=True)
            mins_display = round(seconds / 60, 1)
            return json.dumps({
                "status": "success",
            }, ensure_ascii=False)

        # 3. Hủy hẹn giờ tắt / khởi động lại
        elif action == "cancel_shutdown":
            result = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
            if result.returncode == 0:
                return json.dumps({
                    "status": "success",
                }, ensure_ascii=False)
            return json.dumps({
                "status": "idle",
            }, ensure_ascii=False)

        # 4. Khóa màn hình (Lock)
        elif action == "lock":
            user32.LockWorkStation()
            return json.dumps({
                "status": "success",
            }, ensure_ascii=False)

        # 5. Ngủ (Sleep / Suspend)
        elif action == "sleep":
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
            return json.dumps({
                "status": "success",
            }, ensure_ascii=False)

        # 6. Tăng âm lượng
        elif action == "volume_up":
            raw_steps = int(value) if str(value).isdigit() else 5
            # Mỗi lần nhấn VK_VOLUME_UP tăng 2%, nên chia 2 để đúng số nấc mong muốn
            actual_presses = max(1, math.ceil(raw_steps / 2))
            _press_key(VK_VOLUME_UP, actual_presses)
            return json.dumps(
                {
                    "status": "success",
                    "message": (
                        f"Đã tăng âm lượng tương đương {actual_presses * 2}% ({raw_steps}"
                        " nấc)."
                    ),
                },
                ensure_ascii=False,
            )

        elif action == "volume_down":
            raw_steps = int(value) if str(value).isdigit() else 5
            actual_presses = max(1, math.ceil(raw_steps / 2))
            _press_key(VK_VOLUME_DOWN, actual_presses)
            return json.dumps(
                {
                    "status": "success",
                    "message": (
                        f"Đã giảm âm lượng tương đương {actual_presses * 2}% ({raw_steps}"
                        " nấc)."
                    ),
                },
                ensure_ascii=False,
            )

        # 8. Bật / Tắt câm tiếng (Mute)
        elif action == "mute_toggle":
            _press_key(VK_VOLUME_MUTE, 1)
            return json.dumps({
                "status": "success",
            }, ensure_ascii=False)

        return json.dumps({
            "status": "unsupported",
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)