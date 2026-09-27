import base64
import ctypes
import json
import time
from io import BytesIO
import pyautogui
import pyperclip
from PIL import Image

# ==========================================
# CẤU HÌNH HỆ THỐNG VÀ AN TOÀN
# ==========================================

# Kích hoạt nhận diện DPI để tọa độ pixel đồng bộ chính xác với màn hình Windows
try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

# Đưa chuột lên góc trên cùng bên trái (0, 0) màn hình để ngắt script khẩn cấp
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# Lấy động kích thước màn hình hiện tại
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()


# ==========================================
# 1. SCHEMA NATIVE TOOL CHO RESPONSES API
# ==========================================
# Khai báo trực tiếp loại tool "computer_use" theo chuẩn built-in
computer_tool_schema = {
    "type": "computer_use",
    "computer_use": {
        "display_width_px": SCREEN_WIDTH,
        "display_height_px": SCREEN_HEIGHT
    }
}


# ==========================================
# 2. XỬ LÝ HÌNH ẢNH (ĐÔI MẮT)
# ==========================================
def capture_screen_base64(quality: int = 80) -> str:
    """Chụp màn hình và nén thành Base64 JPEG."""
    screenshot = pyautogui.screenshot()
    buffered = BytesIO()
    screenshot.save(buffered, format="JPEG", quality=quality)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def get_vision_payload(prompt: str = "Màn hình hiện tại:") -> list:
    """Tạo mảng đa phương tiện chuẩn Responses API."""
    b64_img = capture_screen_base64()
    return [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
        }
    ]


# ==========================================
# 3. TRÌNH THỰC THI (ACTION HANDLER)
# ==========================================
def execute_computer_action(action):
  # Hỗ trợ truy xuất thuộc tính cho cả Object (từ SDK) và Dict (nếu bóc JSON)
  action_type = getattr(
      action, "type", action.get("type") if isinstance(action, dict) else None
  )

  if action_type == "click":
    x = getattr(action, "x", action.get("x") if isinstance(action, dict) else 0)
    y = getattr(action, "y", action.get("y") if isinstance(action, dict) else 0)
    button = getattr(
        action,
        "button",
        action.get("button") if isinstance(action, dict) else "left",
    )
    pyautogui.click(x, y, button=button)

  elif action_type == "double_click":
    x = getattr(action, "x", action.get("x") if isinstance(action, dict) else 0)
    y = getattr(action, "y", action.get("y") if isinstance(action, dict) else 0)
    pyautogui.doubleClick(x, y)

  elif action_type == "type":
    text = getattr(
        action, "text", action.get("text") if isinstance(action, dict) else ""
    )
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")

  elif action_type == "keypress":
    keys = getattr(
        action, "keys", action.get("keys") if isinstance(action, dict) else []
    )
    for key in keys:
      pyautogui.press(key)

  elif action_type == "scroll":
    x = getattr(action, "x", action.get("x") if isinstance(action, dict) else 0)
    y = getattr(action, "y", action.get("y") if isinstance(action, dict) else 0)
    scroll_y = getattr(
        action,
        "scroll_y",
        action.get("scroll_y") if isinstance(action, dict) else -300,
    )
    pyautogui.moveTo(x, y)
    pyautogui.scroll(scroll_y)

  elif action_type == "wait":
    time.sleep(1)

  # THÊM NHÁNH NÀY: Model chỉ muốn xem màn hình hiện tại
  elif action_type == "screenshot":
    pass

  else:
    print(f"[Warning] Bỏ qua action chưa hỗ trợ: {action_type}")