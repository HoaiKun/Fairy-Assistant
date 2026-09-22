import { createContext, useContext, useEffect, useState, useRef } from "react";
import { MessageSchema } from "./ChatBox";
import { useAudioRecorder } from "./hooks/AudioRecorder";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);
    const currentAudioRef = useRef(null);

    // 1. ĐỔI MẶC ĐỊNH SANG TRUE VÀ DÙNG THÊM REF ĐỂ CHỐNG STALE CLOSURE
    const [IsOutVoice, setIsOutVoice] = useState(true);
    const isOutVoiceRef = useRef(true);

    // Đồng bộ state và ref mỗi khi user toggle
    const handleToggleVoice = (val) => {
        setIsOutVoice(val);
        isOutVoiceRef.current = val;
    };

    const playNextAudioChunk = () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            currentAudioRef.current = null;
            return;
        }

        isPlayingRef.current = true;
        const base64Audio = audioQueueRef.current.shift();
        const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
        currentAudioRef.current = audio;

        audio.onended = () => {
            playNextAudioChunk();
        };

        audio.onerror = (e) => {
            console.error("Lỗi phát audio chunk:", e);
            playNextAudioChunk();
        };

        audio.play().catch((err) => {
            console.warn("Lỗi phát audio:", err);
            playNextAudioChunk();
        });
    };

    const stopAudioPlayback = () => {
        // 1. Xóa sạch hàng đợi ngay lập tức
        audioQueueRef.current = [];
        isPlayingRef.current = false;

        // 2. Cắt đứt hoàn toàn audio element hiện tại
        if (currentAudioRef.current) {
            // QUAN TRỌNG NHẤT: Hủy callback onended để nó KHÔNG gọi playNextAudioChunk nữa!
            currentAudioRef.current.onended = null;
            currentAudioRef.current.onerror = null;

            currentAudioRef.current.pause();
            currentAudioRef.current.currentTime = 0;
            currentAudioRef.current.removeAttribute("src"); // Xóa triệt để source
            currentAudioRef.current.load(); // Reset trạng thái buffer của HTMLAudioElement
            currentAudioRef.current = null;
        }
        console.log("[Audio] Đã cưỡng chế dừng toàn bộ âm thanh!");
    };

    const handleAudioReady = ({ base64Audio }) => {
        console.log("Hook vừa thu xong câu nói, chuẩn bị bắn socket!");

        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({
                type: "audio_input",
                role: "user",
                audio_data: base64Audio,
                format: "webm"
            }));
        } else {
            console.warn("Socket chưa kết nối!");
        }
    };

    const [iChatHistory, setiChatHistory] = useState(true);

    const { isListening, isSpeaking, startListening, stopListening } = useAudioRecorder({
        onAudioReady: handleAudioReady
    });

    const [Messages, setMessages] = useState([
        { id: 1, role: "bot", content: "Xin chào! Bạn cần giúp gì?", type: "text" },
        { id: 2, role: "bot", content: "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS_IW5IjXyLDb3rDt7iGUeyduUTk281QNw3PMx9zt2w9Q&s=10", type: "image" }
    ]);
    const [InputText, setInputText] = useState("");
    const socketRef = useRef(null);

    useEffect(() => {
        const ws = new WebSocket("ws://localhost:8000/ws/chat");
        socketRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket connected to Python!");
        };

        ws.onmessage = (event) => {
            try {
                const receivedMsg = JSON.parse(event.data);

                if (receivedMsg.type === "text_start") {
                    stopAudioPlayback();
                    const MessObj = new MessageSchema(receivedMsg.role, receivedMsg.type, "");
                    setMessages((prev) => [...prev, MessObj]);
                }
                else if (receivedMsg.type === "text_delta") {
                    setMessages((prev) => {
                        if (prev.length === 0) return prev;
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;
                        const currentContent = updated[lastIndex]?.content || "";
                        const deltaText = receivedMsg.content || "";
                        updated[lastIndex] = { ...updated[lastIndex], content: currentContent + deltaText };
                        return updated;
                    });
                }
                else if (receivedMsg.type === "audio_chunk") {
                    // DÙNG isOutVoiceRef.current THAY VÌ STATE BIẾN THƯỜNG
                    console.log("[WS] Nhận audio_chunk từ server, check Voice:", isOutVoiceRef.current);

                    if (isOutVoiceRef.current && receivedMsg.audio_data) {
                        audioQueueRef.current.push(receivedMsg.audio_data);
                        console.log("Speaking desuwa");
                        
                        if (!isPlayingRef.current) {
                            playNextAudioChunk();
                        }
                    }
                }
            } catch (err) {
                console.error("Parsed error", err);
            }
        };

        ws.onerror = (err) => console.error("WebSocket error:", err);
        ws.onclose = () => console.log("WebSocket disconnected!");

        return () => {
            ws.close();
            stopAudioPlayback();
        };
    }, []);

    const sendMessage = (messageObj) => {
        if (!messageObj && !InputText.trim()) return;

        stopAudioPlayback();
        setMessages((prev) => [...prev, messageObj]);

        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(messageObj));
        } else {
            console.warn("WEBSOCKET NOT READY");
        }

        setInputText("");
    };

    const toggleVoice = () => {
    const newState = !IsOutVoice;
    
    // Cập nhật cả State lẫn Ref cùng lúc
    setIsOutVoice(newState);
    if (isOutVoiceRef) {
            isOutVoiceRef.current = newState;
        }

        // Nếu tắt voice -> Dừng loa ngay lập tức
        if (!newState) {
            stopAudioPlayback();
        }

        // Bắn thông báo cho Backend đổi cờ hủy TTS task
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({
                type: "toggle_voice",
                enabled: newState
            }));
        }
    };

    return (
        <ChatContext.Provider value={{
            Messages, setMessages, InputText, setInputText, sendMessage,
            iChatHistory, setiChatHistory,
            IsOutVoice,
            setIsOutVoice: handleToggleVoice, // Bọc hàm để cập nhật luôn cả Ref
            startListening,
            stopListening,
            toggleMic: isListening ? stopListening : startListening,
            toggleVoice
        }}>
            {children}
        </ChatContext.Provider>
    );
}

export function useChat() {
    const context = useContext(ChatContext);
    return context;
}