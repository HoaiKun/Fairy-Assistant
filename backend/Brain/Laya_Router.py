import os
from typing import Literal

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from laya import Router

laya_router = Router(preload=True)

# Chỉ giữ lại câu hỏi định tuyến Model (Có cần GUI / Desktop App không)
routing_questions = {
    "requires_computer_use": {
        "type": "noul",
        "instructions": (
            "Does this task strictly require taking over the mouse, keyboard, looking at the graphical screen, or opening specific visual applications? "
            "YES: Clicking buttons, taking screenshots, interacting with graphical UIs, or explicitly opening desktop apps/websites (e.g., open Gmail, open Word). "
            "NO: Answering general knowledge questions, playing music, setting alarms, or running background terminal commands."
        )
    }
}

def analyze_and_route(user_input: str) -> Literal["gpt-5.6-luna", "gpt-4o-mini"]:
    """
    Định tuyến Model: Chọn gpt-4o-mini hay gpt-5.6-luna dựa trên yêu cầu sử dụng UI/Computer.
    """
    if not user_input or not user_input.strip():
        return "gpt-4o-mini"

    try:
        # Laya phân tích tác vụ
        result = laya_router.predict(user_input, routing_questions)
        
        prob_computer = result["answers"]["requires_computer_use"]["noul"]
        
        print(f"[Router Telemetry] Text: \"{user_input}\" | UI: {prob_computer:.2f}")

        # Siết chặt tác vụ UI với ngưỡng 0.70. Nếu phân vân, fallback về 4o-mini.
        target_model = "gpt-5.6-luna" if prob_computer >= 0.5 else "gpt-4o-mini"
        
        return target_model

    except Exception as e:
        print(f"[Router Error]: {e}")
        # Trả về model mặc định nếu có lỗi
        return "gpt-4o-mini"