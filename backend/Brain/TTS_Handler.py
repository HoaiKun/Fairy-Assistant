import base64
import os
import httpx

FISH_API_KEY = os.getenv("FISH_API_KEY")
# Reference ID (voice model của Fairy) bạn lấy trên trang console của Fish Audio
VOICE_REFERENCE_ID = "f8db038da1c34a4c9749f56a1d463fa2"


async def generate_fish_audio_bytes(
    text: str, client: httpx.AsyncClient
) -> bytes:
  """Gửi text lên Fish Audio API và nhận về raw audio bytes (mp3 hoặc opus)."""
  url = "https://api.fish.audio/v1/tts"
  headers = {
      "Authorization": f"Bearer {FISH_API_KEY}",
      "Content-Type": "application/json",
  }
  payload = {
      "text": text,
      "reference_id": VOICE_REFERENCE_ID,
      "format": "mp3",  # Hoặc 'opus', 'wav'
      "latency": "balanced",  # Hoặc 'low' để tối ưu tốc độ phản hồi
  }

  response = await client.post(
      url, headers=headers, json=payload, timeout=15.0
  )
  if response.status_code != 200:
    print(
        f"[FishTTS Error] Status: {response.status_code}, Body: {response.text}"
    )
    return b""
    
  return response.content