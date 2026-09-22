import base64
import io
import av
import numpy as np


import os
import sys

# Tự động nạp đường dẫn DLL của NVIDIA vào runtime trên Windows
if sys.platform == "win32":
  cuda_path = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
  if os.path.exists(cuda_path):
    for root, dirs, files in os.walk(cuda_path):
      if any(f.endswith(".dll") for f in files):
        os.add_dll_directory(root)
        os.environ["PATH"] = root + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel

whisper_model = WhisperModel("small.en", device="cuda", compute_type="float16")


def base64_to_pcm_audio(base64_str: str) -> np.ndarray:
  """Giải mã Base64 WebM/Opus từ trình duyệt thành NumPy float32 16kHz Mono

  hoàn toàn trên RAM bằng PyAV (FFmpeg).
  """
  audio_bytes = base64.b64decode(base64_str)
  input_io = io.BytesIO(audio_bytes)

  # Mở container WebM từ BytesIO
  container = av.open(input_io)

  # Resample trực tiếp về 16000Hz, mono (s16 hoặc flt) chuẩn cho Whisper
  resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)

  frames = []
  for frame in container.decode(audio=0):
    resampled_frames = resampler.resample(frame)
    for resampled in resampled_frames:
      # Chuyển frame audio sang numpy array
      frames.append(resampled.to_ndarray())

  if not frames:
    return np.array([], dtype=np.float32)

  # Ghép các frame và làm phẳng thành vector 1D float32
  audio_np = np.concatenate(frames, axis=1).squeeze()
  return audio_np.astype(np.float32)


def transcribe_audio_base64(base64_str: str) -> str:
  try:
    audio_np = base64_to_pcm_audio(base64_str)

    # Bỏ qua nếu audio quá ngắn (dưới 0.2s: 16000 * 0.2 = 3200 samples)
    if len(audio_np) < 3200:
      return ""

    segments, _ = whisper_model.transcribe(
        audio_np,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=False,
    )

    result_text = "".join([segment.text for segment in segments]).strip()
    return result_text

  except Exception as e:
    print(f"[STT Error]: {e}")
    return ""