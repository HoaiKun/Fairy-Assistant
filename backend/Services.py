import asyncio
import base64
from contextlib import asynccontextmanager
import json
import re

from Brain.CoreBrain import RunFairyMain
from Brain.STT_Handler import transcribe_audio_base64
from Brain.TTS_Handler import generate_fish_audio_bytes
from extensions.reminder_manager import reminder_manager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import httpx

http_client = httpx.AsyncClient(timeout=15.0)
PUNCTUATION_PATTERN = re.compile(r"([.!?;:\n]+)")

IsVoice = False
main_loop = None


@asynccontextmanager
async def lifespan(app: FastAPI):
  global main_loop
  main_loop = asyncio.get_running_loop()
  print(f"[Fairy Server] Main Event Loop captured: {main_loop}")
  yield
  await http_client.aclose()


app = FastAPI(lifespan=lifespan)

# Tập hợp lưu các client đang online (để bắn thông báo)
active_connections: set[asyncio.Queue] = set()


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

  user_queue = asyncio.Queue()
  active_connections.add(user_queue)

  # 1. Task nhận tin nhắn từ Client -> đẩy vào Queue
  async def receive_loop():
    global IsVoice  # Cần global để cập nhật biến trạng thái
    try:
      while True:
        data_str = await websocket.receive_text()
        data = json.loads(data_str)
        msg_type = data.get("type")

        # ─── BẬT / TẮT VOICE ───
        if msg_type == "toggle_voice":
          IsVoice = data.get("enabled", True)
          print(f"[WS] Master vừa chuyển IsVoice thành: {IsVoice}")
          continue

        # ─── USER GÕ PHÍM ───
        elif msg_type == "text" or (
            "content" in data and not data.get("audio_data")
        ):
          content = data.get("content", "").strip()
          if content:
            await user_queue.put({
                "source": "client",
                "role": "user",
                "content": content,
            })

        # ─── USER NÓI QUA MIC ───
        elif msg_type == "audio_input":
          base64_audio = data.get("audio_data")
          if not base64_audio:
            continue

          print("[WS] Nhận audio chunk, đang đưa vào Faster-Whisper...")
          loop = asyncio.get_running_loop()
          transcribed_text = await loop.run_in_executor(
              None, transcribe_audio_base64, base64_audio
          )
          print(f"🎙️ [Whisper Transcribed]: '{transcribed_text}'")

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

  # 2. Task tiêu thụ Queue -> gọi FairyMain -> stream qua WebSocket
  async def process_and_send_loop():
    global IsVoice
    while True:
      item = await user_queue.get()
      tts_queue = asyncio.Queue() if IsVoice else None
      tts_task = None

      # Worker TTS chỉ khởi chạy khi IsVoice == True
      if IsVoice:

        async def tts_worker():
          chunk_idx = 0
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
            except Exception as tts_err:
              print(f"[TTS Pipeline Error]: {tts_err}")
            finally:
              tts_queue.task_done()

        tts_task = asyncio.create_task(tts_worker())

      try:
        # Báo hiệu START
        await websocket.send_text(
            json.dumps(
                {
                    "role": "bot",
                    "type": "text_start",
                    "content": "START",
                    "source": item["source"],
                },
                ensure_ascii=False,
            )
        )

        sentence_buffer = ""
        is_first_sentence = True

        # Stream token từ Fairy
        async for chunk in RunFairyMain(
            input=item["content"], role=item["role"]
        ):
          # 1. Gửi delta text tức thì lên UI
          await websocket.send_text(
              json.dumps(
                  {"role": "bot", "type": "text_delta", "content": chunk},
                  ensure_ascii=False,
              )
          )

          # 2. Gom câu nếu bật voice
          if IsVoice:
            sentence_buffer += chunk

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
                  r"\(?\[.*?\]\(https?://[^\)]+\)\)?", "", ready_sentence
              ).strip()
              if clean_sentence:
                await tts_queue.put(clean_sentence)

        # Xử lý phần text còn lại sau khi vòng lặp stream kết thúc (NẰM NGOÀI FOR)
        if IsVoice and sentence_buffer.strip():
          clean_tail = re.sub(
              r"\(?\[.*?\]\(https?://[^\)]+\)\)?", "", sentence_buffer
          ).strip()
          if clean_tail:
            await tts_queue.put(clean_tail)

        # Chờ TTS hoàn thành
        if IsVoice and tts_task:
          await tts_queue.put(None)
          await tts_task

        # Báo hiệu kết thúc câu trả lời
        await websocket.send_text(
            json.dumps(
                {"role": "bot", "type": "text_end", "content": "END"},
                ensure_ascii=False,
            )
        )

      except Exception as e:
        print(f"[WebSocket Error]: {e}")
        if tts_task:
          tts_task.cancel()
        break
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
    active_connections.discard(user_queue)
    print("Disconnected Client")