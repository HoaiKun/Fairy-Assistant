import { useState, useRef, useEffect } from "react";

export function useAudioRecorder({ onAudioReady } = {}) {
    // isListening: Mic đang mở và chờ bạn nói
    const [isListening, setIsListening] = useState(false);
    // isSpeaking: Đang có tiếng nói và đang thực sự ghi âm
    const [isSpeaking, setIsSpeaking] = useState(false);

    const streamRef = useRef(null);
    const audioContextRef = useRef(null);
    const analyserRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    const animFrameRef = useRef(null);
    const silenceTimerRef = useRef(null);
    const isSpeakingRef = useRef(false);

    // CẤU HÌNH NGƯỠNG VAD
    const VOICE_THRESHOLD = 0.025; // Ngưỡng âm lượng (RMS từ 0.015 đến 0.04 tùy độ nhạy của mic)
    const SILENCE_DURATION = 350;  // Thời gian im lặng để chốt câu (~0.35s - 0.3s là tối ưu)

    // 1. Bật chế độ Always-Listening
    const startListening = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            });

            streamRef.current = stream;

            // Thiết lập Web Audio API để đo volume liên tục
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            const audioCtx = new AudioCtx();
            audioContextRef.current = audioCtx;

            const source = audioCtx.createMediaStreamSource(stream);
            const analyser = audioCtx.createAnalyser();
            analyser.fftSize = 512;
            source.connect(analyser);
            analyserRef.current = analyser;

            setIsListening(true);
            console.log("[Mic] Always-Listening Activated. Chờ giọng nói của Master...");

            // Bắt đầu vòng lặp đo âm lượng
            detectSound();
        } catch (err) {
            console.error("Lỗi cấp quyền Mic:", err);
            alert("Không thể truy cập Microphone. Vui lòng kiểm tra quyền thiết bị!");
        }
    };

    // 2. Vòng lặp đo Volume theo thời gian thực (RMS Calculation)
    const detectSound = () => {
        if (!analyserRef.current) return;

        const dataArray = new Uint8Array(analyserRef.current.fftSize);
        analyserRef.current.getByteTimeDomainData(dataArray);

        // Tính Root Mean Square (RMS) từ biên độ sóng âm
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            const val = (dataArray[i] - 128) / 128;
            sum += val * val;
        }
        const rms = Math.sqrt(sum / dataArray.length);

        // PHÁT HIỆN TIẾNG NÓI
        if (rms > VOICE_THRESHOLD) {
            // Nếu có tiếng thì xóa ngay bộ đếm im lặng
            if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = null;
            }

            // Nếu trước đó đang im lặng mà giờ có tiếng -> BẮT ĐẦU GHI
            if (!isSpeakingRef.current) {
                isSpeakingRef.current = true;
                setIsSpeaking(true);
                startActualRecording();
            }
        } 
        // PHÁT HIỆN ĐANG IM LẶNG
        else {
            if (isSpeakingRef.current && !silenceTimerRef.current) {
                // Đếm ngược 300ms, nếu vẫn im lặng thì DỪNG và GỬI
                silenceTimerRef.current = setTimeout(() => {
                    isSpeakingRef.current = false;
                    setIsSpeaking(false);
                    stopActualRecording();
                    silenceTimerRef.current = null;
                }, SILENCE_DURATION);
            }
        }

        animFrameRef.current = requestAnimationFrame(detectSound);
    };

    // 3. Kích hoạt MediaRecorder để gom audio
    const startActualRecording = () => {
        if (!streamRef.current) return;
        audioChunksRef.current = [];

        const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm";

        const recorder = new MediaRecorder(streamRef.current, { mimeType });
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
                audioChunksRef.current.push(e.data);
            }
        };

        recorder.onstop = () => {
            // Gom tất cả chunk lại
            const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });

            // Bỏ qua nếu đoạn âm thanh quá ngắn (dưới 1KB - thường là tiếng click chuột hoặc thở nhẹ)
            if (blob.size < 1200) {
                console.log("[Mic] Âm thanh quá ngắn hoặc tạp âm, bỏ qua.");
                return;
            }

            // Đọc base64 và bắn callback
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = () => {
                const base64Audio = reader.result.split(",")[1];
                console.log(`[Mic] Đã chốt câu nói (${blob.size} bytes). Gửi lên Backend...`);

                if (onAudioReady) {
                    onAudioReady({ blob, base64Audio });
                }
            };
        };

        recorder.start(50);
        console.log("🎙️ [Mic] Đang nói: START RECORDING");
    };

    // 4. Dừng thu một câu (không tắt stream mic)
    const stopActualRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.stop();
            console.log("🛑 [Mic] Ngừng nói 0.3s: STOP & SEND");
        }
    };

    // 5. Tắt hoàn toàn Mic (khi người dùng chủ động tắt nút Mic)
    const stopListening = () => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.stop();
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }

        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        isSpeakingRef.current = false;
        setIsSpeaking(false);
        setIsListening(false);
        console.log("[Mic] Đã tắt hoàn toàn thiết bị Mic.");
    };

    // Dọn dẹp khi unmount
    useEffect(() => {
        return () => {
            stopListening();
        };
    }, []);

    return {
        isListening,       // State: Mic đang bật và sẵn sàng nghe
        isSpeaking,        // State: Bạn đang thực sự cất tiếng nói (dùng làm animation nhấp nháy)
        startListening,    // Hàm: Bật chế độ luôn lắng nghe
        stopListening,     // Hàm: Tắt mic hoàn toàn
    };
}