import asyncio
import base64
from contextlib import asynccontextmanager
import json
import re
from urllib.parse import unquote

from Brain.CoreBrain import CleanUpUnsavedMemory, RunFairyMain
from Brain.STT_Handler import transcribe_audio_base64
from Brain.TTS_Handler import generate_fish_audio_bytes
from extensions.reminder_manager import reminder_manager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx

http_client = httpx.AsyncClient(timeout=15.0)
PUNCTUATION_PATTERN = re.compile(r"([.!?;:\n]+)")
IsVoice = False
main_loop = None

# active_connections sẽ lưu tuple: (user_queue, cancel_ongoing_pipeline)
active_connections: set[tuple] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
  global main_loop
  main_loop = asyncio.get_running_loop()
  asyncio.create_task(CleanUpUnsavedMemory())
  yield
  await http_client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# KHỐI XỬ LÝ NHẮC NHỞ KHẨN CẤP (REMINDER)
# ==========================================
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
  print(f"\n🔔 [REMINDER TRIGGERED]: {title}")

  if main_loop and not main_loop.is_closed():
    for connection in list(active_connections):
      # Bóc tách tuple
      user_queue = connection[0]
      cancel_func = connection[1]

      # Khởi tạo một task chạy bên trong event loop chính
      async def force_interrupt_and_remind(q, canceler, msg):
        print("🛑 [Reminder] Đang chen ngang tiến trình hiện tại để báo thức...")
        await canceler()       # 1. Bắt bot im lặng ngay lập tức
        await q.put(msg)       # 2. Nhét báo thức vào hàng đợi trống

      # Đẩy từ Thread của scheduler sang Asyncio một cách an toàn
      asyncio.run_coroutine_threadsafe(
          force_interrupt_and_remind(user_queue, cancel_func, payload), main_loop
      )
  else:
    print("[ERROR] main_loop is None or closed!")


# Đăng ký hàm callback
reminder_manager.callback_func = RaiseReminder


# ==========================================
# ENDPOINT WEBSOCKET CHÍNH
# ==========================================
@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
  await websocket.accept()
  print("[WS] Client kết nối thành công.")

  user_queue = asyncio.Queue()
  current_pipeline_task: asyncio.Task | None = None

  # ─── HÀM DỪNG VÀ DỌN DẸP PIPELINE CŨ ───
  async def cancel_ongoing_pipeline():
    nonlocal current_pipeline_task
    if current_pipeline_task and not current_pipeline_task.done():
      print("🛑 [Interrupt] Đang ngắt pipeline cũ...")
      current_pipeline_task.cancel()
      try:
        await current_pipeline_task
      except asyncio.CancelledError:
        pass
      current_pipeline_task = None

    # Xóa sạch các câu còn xếp hàng trong Queue
    while not user_queue.empty():
      try:
        user_queue.get_nowait()
        user_queue.task_done()
      except (asyncio.QueueEmpty, ValueError):
        break

    # Gửi tín hiệu để Frontend xóa buffer âm thanh và reset animation
    try:
      await websocket.send_text(
          json.dumps(
              {"type": "interrupted", "role": "system"}, ensure_ascii=False
          )
      )
    except Exception:
      pass

  # 👉 Đăng ký kết nối vào active_connections dưới dạng Tuple
  connection_tuple = (user_queue, cancel_ongoing_pipeline)
  active_connections.add(connection_tuple)

  # ─── PIPELINE THỰC THI (LLM + TTS) ───
  async def run_pipeline(item: dict):
    global IsVoice
    tts_queue = asyncio.Queue() if IsVoice else None
    tts_task = None

    # Báo trạng thái bắt đầu xử lý cho Frontend
    await websocket.send_text(
        json.dumps(
            {"type": "status", "is_processing": True}, ensure_ascii=False
        )
    )

    if IsVoice:

      async def tts_worker():
        chunk_idx = 0
        try:
          while True:
            sentence = await tts_queue.get()
            if sentence is None:
              tts_queue.task_done()
              break
            try:
              audio_bytes = await generate_fish_audio_bytes(
                  sentence, http_client
              )
              if audio_bytes:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                await websocket.send_text(
                    json.dumps(
                        {
                            "role": "bot",
                            "type": "audio_chunk",
                            "index": chunk_idx,
                            "audio_data": audio_b64,
                            "text": sentence,
                        },
                        ensure_ascii=False,
                    )
                )
                chunk_idx += 1
            except Exception as err:
              print(f"[TTS Error]: {err}")
            finally:
              tts_queue.task_done()
        except asyncio.CancelledError:
          pass

      tts_task = asyncio.create_task(tts_worker())

    try:
      sentence_buffer = ""
      is_first_sentence = True

      async for chunk in RunFairyMain(
          input=item["content"], role=item["role"]
      ):
        await websocket.send_text(json.dumps(chunk, ensure_ascii=False))

        if IsVoice:
          sentence_buffer += chunk.get("content") or ""
          should_cut = False

          if is_first_sentence:
            if "," in sentence_buffer or len(sentence_buffer.split()) >= 6:
              should_cut = True
              is_first_sentence = False
          elif PUNCTUATION_PATTERN.search(sentence_buffer):
            should_cut = True

          if should_cut:
            parts = PUNCTUATION_PATTERN.split(sentence_buffer, maxsplit=1)
            ready_sentence = (
                (parts[0] + parts[1]).strip()
                if len(parts) >= 2
                else sentence_buffer.strip()
            )
            sentence_buffer = "".join(parts[2:]) if len(parts) >= 2 else ""

            clean_sentence = re.sub(
                r"\[.*?\]\(https?://[^\)]+\)", "", ready_sentence
            )
            clean_sentence = re.sub(
                r"https?://\S+", "", clean_sentence
            ).strip()

            if clean_sentence:
              await tts_queue.put(clean_sentence)

      if IsVoice and sentence_buffer.strip():
        clean_tail = re.sub(r"\[.*?\]\(https?://[^\)]+\)", "", sentence_buffer)
        clean_tail = re.sub(r"https?://\S+", "", clean_tail).strip()
        if clean_tail:
          await tts_queue.put(clean_tail)

      if IsVoice and tts_task:
        await tts_queue.put(None)
        await tts_task

    except asyncio.CancelledError:
      print("⚡ Pipeline đã bị hủy an toàn.")
      if tts_task and not tts_task.done():
        tts_task.cancel()
      raise
    finally:
      if tts_task and not tts_task.done():
        tts_task.cancel()
      # Báo Frontend đã hoàn thành câu
      try:
        await websocket.send_text(
            json.dumps(
                {"type": "status", "is_processing": False}, ensure_ascii=False
            )
        )
      except Exception:
        pass

  # ─── VÒNG LẶP NHẬN SỰ KIỆN TỪ CLIENT ───
  async def receive_loop():
    global IsVoice
    try:
      while True:
        data_str = await websocket.receive_text()
        data = json.loads(data_str)
        msg_type = data.get("type")

        if msg_type == "interrupt":
          await cancel_ongoing_pipeline()
          continue

        if msg_type == "toggle_voice":
          IsVoice = data.get("enabled", True)
          continue

        if msg_type == "text" or (
            "content" in data and not data.get("audio_data")
        ):
          content = data.get("content", "").strip()
          if content:
            await cancel_ongoing_pipeline()
            await user_queue.put({
                "source": "client",
                "role": "user",
                "content": content,
            })

        elif msg_type == "audio_input":
          base64_audio = data.get("audio_data")
          if not base64_audio:
            continue

          await cancel_ongoing_pipeline()
          loop = asyncio.get_running_loop()
          transcribed_text = await loop.run_in_executor(
              None, transcribe_audio_base64, base64_audio
          )

          if transcribed_text:
            await websocket.send_text(
                json.dumps(
                    {
                        "role": "user",
                        "type": "transcribed_text",
                        "content": transcribed_text,
                    },
                    ensure_ascii=False,
                )
            )
            await user_queue.put({
                "source": "client",
                "role": "user",
                "content": transcribed_text,
            })

    except WebSocketDisconnect:
      print("[WS] Client disconnected.")
    except Exception as e:
      print(f"[WS Error]: {e}")

  # ─── VÒNG LẶP ĐIỀU PHỐI PIPELINE ───
  async def process_and_send_loop():
    nonlocal current_pipeline_task
    while True:
      item = await user_queue.get()
      try:
        current_pipeline_task = asyncio.create_task(run_pipeline(item))
        await current_pipeline_task
      except asyncio.CancelledError:
        pass
      finally:
        user_queue.task_done()

  receiver_task = asyncio.create_task(receive_loop())
  sender_task = asyncio.create_task(process_and_send_loop())

  try:
    done, pending = await asyncio.wait(
        [receiver_task, sender_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
      task.cancel()
  finally:
    await cancel_ongoing_pipeline()
    # Dọn dẹp an toàn tuple khi ngắt kết nối
    active_connections.discard(connection_tuple)


# ==========================================
# MUSIC PROXY
# ==========================================

@app.get("/api/stream_music")
async def proxy_stream_music(url: str):
  # Giải mã URL 1 lần duy nhất để FastAPI hiểu được link gốc
  target_url = unquote(url)

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
          " (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
      ),
      "Accept": "*/*",
      "Range": "bytes=0-",
      "Referer": "https://www.youtube.com/",
  }

  async def audio_stream_generator():
    try:
      # Nếu gặp lỗi chứng chỉ SSL, có thể thêm verify=False tạm thời
      async with httpx.AsyncClient(
          headers=headers, follow_redirects=True, timeout=30.0
      ) as client:
        async with client.stream("GET", target_url) as response:
          if response.status_code not in (200, 206):
            print(
                f"❌ [Stream Proxy] Google Video từ chối. Status: {response.status_code}"
            )
            return

          async for chunk in response.aiter_bytes(chunk_size=32768):
            yield chunk
    except Exception as e:
      print(f"❌ [Stream Proxy Error]: {e}", flush=True)

  return StreamingResponse(
      audio_stream_generator(),
      media_type="audio/webm",
      headers={
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-cache",
      },
  )