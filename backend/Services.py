import asyncio
import json
from extensions.reminder_manager import reminder_manager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from Brain.CoreBrain import RunFairyMain
from contextlib import asynccontextmanager
from Brain.STT_Handler import transcribe_audio_base64
main_loop = None
@asynccontextmanager
async def lifespan(app: FastAPI):
  global main_loop
  main_loop = asyncio.get_running_loop()  # Lưu loop chính tại đây
  print(f"[Fairy Server] Main Event Loop captured: {main_loop}")
  yield

app = FastAPI(lifespan=lifespan)

# Tập hợp lưu các client đang online (để bắn thông báo)
active_connections: set[asyncio.Queue] = set()


# Callback được gọi khi reminder đến giờ
def RaiseReminder(item: dict):
  global main_loop
  title = item.get("title", "Reminder")
  details = item.get("details", "")

  prompt = (
      f"[SYSTEM ALERT: Reminder reached for '{title}'. "
      f"Details: '{details}'. Deliver this notification to Master"
      " immediately.]"
  )

  payload = {"source": "reminder", "role": "user", "content": prompt}
  print(f"[DEBUG] ALERTING: {payload}")

  if main_loop and not main_loop.is_closed():
    for q in list(active_connections):
      main_loop.call_soon_threadsafe(q.put_nowait, payload)
  else:
    print("[ERROR] main_loop is None or closed!")

reminder_manager.callback_func = RaiseReminder


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")

    # Mỗi client kết nối sẽ sở hữu 1 hàng đợi riêng
    user_queue = asyncio.Queue()
    active_connections.add(user_queue)

    # 1. Task chỉ nhận tin nhắn từ Client -> đẩy vào Queue
    async def receive_loop():
        try:
            while True:
                data_str = await websocket.receive_text()
                data = json.loads(data_str)
                msg_type = data.get("type")

                # ─── TRƯỜNG HỢP 1: USER GÕ PHÍM (TEXT THƯỜNG) ───
                if msg_type == "text" or (
                    "content" in data and not data.get("audio_data")
                ):
                    content = data.get("content", "").strip()
                    if content:
                        await user_queue.put({
                            "source": "client",
                            "role": "user",
                            "content": content,
                        })

                # ─── TRƯỜNG HỢP 2: USER NÓI QUA MIC (AUDIO BASE64) ───
                elif msg_type == "audio_input":
                    base64_audio = data.get("audio_data")
                if not base64_audio:
                    continue

                print("[WS] Nhận audio chunk, đang đưa vào Faster-Whisper...")

                # Chạy Whisper trong thread pool để không block Event Loop của FastAPI
                loop = asyncio.get_running_loop()
                transcribed_text = await loop.run_in_executor(
                    None, transcribe_audio_base64, base64_audio
                )

                print(f"🎙️ [Whisper Transcribed]: '{transcribed_text}'")

                if transcribed_text:
                    # 1. Báo ngược lại cho Frontend biết nội dung text vừa nhận dạng được để update khung chat
                    await websocket.send_text(
                        json.dumps({
                            "role": "user",
                            "type": "transcribed_text",
                            "content": transcribed_text,
                        })
                    )

                    # 2. Đẩy text vào user_queue để Fairy bắt đầu suy nghĩ và stream câu trả lời
                    await user_queue.put({
                        "source": "client",
                        "role": "user",
                        "content": transcribed_text,
                    })
        except WebSocketDisconnect:
            print("[WS] Client disconnected.")
        except Exception as e:
            print(f"[WS Error]: {e}")

    # 2. Task tiêu thụ Queue -> gọi FairyMain -> stream qua WebSocket
    async def process_and_send_loop():
        while True:
            item = await user_queue.get()
            try:
                # Bắt đầu stream
                await websocket.send_text(
                    json.dumps({
                        "role": "bot",
                        "type": "text_start",
                        "content": "START",
                        "source": item["source"]  # Giúp frontend phân biệt đây là chat thường hay reminder
                    }, ensure_ascii=False)
                )

                # Stream từng chunk từ FairyMain
                async for chunk in RunFairyMain(input=item["content"], role=item["role"]):
                    await websocket.send_text(
                        json.dumps({
                            "role": "bot",
                            "type": "text_delta",
                            "content": chunk
                        }, ensure_ascii=False)
                    )

                # Kết thúc stream
                await websocket.send_text(
                    json.dumps({
                        "role": "bot",
                        "type": "text_end",
                        "content": "END"
                    }, ensure_ascii=False)
                )
            except Exception as e:
                print(f"[WebSocket Error]: {e}")
                break
            finally:
                user_queue.task_done()

    # Chạy song song cả hai luồng
    receiver_task = asyncio.create_task(receive_loop())
    sender_task = asyncio.create_task(process_and_send_loop())

    try:
        # Giữ kết nối đến khi client ngắt kết nối
        done, pending = await asyncio.wait(
            [receiver_task, sender_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    finally:
        active_connections.discard(user_queue)
        print("Disconnected Client")