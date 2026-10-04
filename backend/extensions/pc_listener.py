import numpy as np
import soundcard as sc
import kagglehub
import csv
import os
import tensorflow as tf
from faster_whisper import WhisperModel
import threading
import queue
import time

class FairyEar:
    def __init__(self, sample_rate=16000, chunk_duration=3):
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.is_tts_speaking = False
        
        # Dùng queue chuẩn của Python (không cần async)
        self.audio_queue = queue.Queue()
        self.current_background_audio = "Silence"
        self.current_transcripts = ""
        self.recent_transcripts = []
        self.class_names = []

        self.active_mode = False            # Trạng thái Bật/Tắt
        self.active_language = "vi"         # Ngôn ngữ mục tiêu (ja, en, vi...)
        self.active_buffer = []             # Nơi lưu trữ text độ dài vô hạn khi Bật

    def load_models(self):
        print("[FairyEar] Đang tải YAMNet và Whisper...")
        model_path = kagglehub.model_download("google/yamnet/tensorFlow2/yamnet")
        self.yamnet_model = tf.saved_model.load(model_path)
        
        class_map_path = os.path.join(model_path, 'assets', 'yamnet_class_map.csv')
        if not os.path.exists(class_map_path):
            class_map_path = self.yamnet_model.class_map_path().numpy().decode('utf-8')
            
        with open(class_map_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self.class_names.append(row['display_name'])

        self.whisper_model = WhisperModel("base", device="cuda", compute_type="int8")
        print("[FairyEar] Tải mô hình hoàn tất!")



    # === THÊM 2 HÀM ĐỂ LÀM TOOL CHO LLM ===
    def turn_on_active_listening(self, language="vi"):
        """Kích hoạt chế độ chép chính tả"""
        self.active_language = language
        self.active_buffer = []  # Xóa buffer cũ
        self.active_mode = True
        return f"Đã bật chế độ chép chính tả. Ngôn ngữ: {language}. Đang lắng nghe PC..."

    def turn_off_active_listening(self):
        """Tắt và trả về toàn bộ văn bản đã nghe được"""
        self.active_mode = False
        full_text = " ".join(self.active_buffer)
        self.active_buffer = []  # Xóa đi cho nhẹ RAM
        
        if not full_text.strip():
            return "Đã tắt. Không nghe thấy giọng nói nào trong khoảng thời gian vừa rồi."
        return f"Đã tắt. Nội dung trích xuất được:\n{full_text}"

    def _audio_capture_thread(self):
        try:
            # 1. Lấy loa mặc định hiện tại của hệ thống (VD: FxSound)
            speaker = sc.default_speaker()
            print(f"[FairyEar] Đã tìm thấy loa: {speaker.name}")
            
            # 2. Tìm Microphone (Loopback) tương ứng với cái loa đó
            loopback_mic = sc.get_microphone(id=speaker.id, include_loopback=True)
            print(f"[FairyEar] Đã kích hoạt đôi tai (Loopback). Bắt đầu nghe ngầm...")
            
            # 3. Ghi âm từ loopback_mic thay vì speaker
            with loopback_mic.recorder(samplerate=self.sample_rate, channels=1) as recorder:
                while True:
                    if self.is_tts_speaking:
                        # Đọc bỏ buffer khi Fairy đang nói để tránh vọng âm
                        recorder.record(numframes=int(self.sample_rate * 0.5))
                        time.sleep(0.1)
                        continue
                    
                    # Cắt mỗi chunk âm thanh (VD: 3 giây)
                    data = recorder.record(numframes=self.sample_rate * self.chunk_duration)
                    audio_data = data[:, 0].astype(np.float32)
                    self.audio_queue.put(audio_data)
                    
        except Exception as e:
            print(f"❌ [LỖI AUDIO CAPTURE]: {str(e)}")

    def _process_audio_thread(self):
        while True:
            audio_chunk = self.audio_queue.get() 
            scores, embeddings, spectrogram = self.yamnet_model(audio_chunk)
            mean_scores = np.mean(scores, axis=0)
            top_class_index = np.argmax(mean_scores)
            top_class_name = self.class_names[top_class_index]
            speech_score = mean_scores[0] 
            
            if speech_score > 0.2:
                # 1. Chuyển đổi ngôn ngữ theo chế độ Active hay Passive
                target_lang = self.active_language if self.active_mode else "vi"
                
                segments, _ = self.whisper_model.transcribe(audio_chunk, beam_size=1, language=target_lang, vad_filter=True,)
                text = " ".join([segment.text for segment in segments]).strip()
                
                if text:
                    self.current_transcripts = text
                    # 2. Lưu vào trí nhớ thụ động (luôn chạy)
                    self.recent_transcripts.append(text)
                    if len(self.recent_transcripts) > 20: self.recent_transcripts.pop(0)

                    # 3. LƯU VÀO TRÍ NHỚ CHỦ ĐỘNG (Nếu đang Bật)
                    if self.active_mode:
                        self.active_buffer.append(text)
            else:
                if top_class_name != "Silence":
                    self.current_background_audio = top_class_name


                

            

    def start(self):
        """Chạy trực tiếp 2 luồng ngầm (daemon=True nghĩa là nó sẽ tự tắt khi bạn tắt app chính)"""
        threading.Thread(target=self._audio_capture_thread, daemon=True).start()
        threading.Thread(target=self._process_audio_thread, daemon=True).start()

# Tạo instance sẵn
FairyEarInstance = FairyEar()

import warnings
from soundcard import SoundcardRuntimeWarning
warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning)