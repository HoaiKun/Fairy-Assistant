import { createContext, useContext, useEffect, useState, useRef } from "react";
import { MessageSchema } from "./ChatBox";
import { useAudioRecorder } from "./hooks/AudioRecorder";

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
    const audioQueueRef = useRef([]); // Lưu danh sách object: { audio_data, sentence }
    const isPlayingRef = useRef(false);
    const currentAudioRef = useRef(null);

    const [IsOutVoice, setIsOutVoice] = useState(false);
    const isOutVoiceRef = useRef(false);

    const [SubText, setSubText] = useState("TEST");

    const handleToggleVoice = (val) => {
        setIsOutVoice(val);
        isOutVoiceRef.current = val;
    };

    const playNextAudioChunk = () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            currentAudioRef.current = null;
            setSubText("");
            return;
        }

        isPlayingRef.current = true;
        
        // Lấy chunk gồm dữ liệu âm thanh và sentence tương ứng
        const nextItem = audioQueueRef.current.shift();
        const base64Audio = typeof nextItem === "string" ? nextItem : nextItem?.audio_data;
        const sentence = typeof nextItem === "object" ? nextItem?.sentence : "";

        if (sentence) {
            setSubText(sentence);
            console.log("ALERTING" + sentence);
        }

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
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        setSubText(""); // Reset subtitle ngay lập tức khi dừng audio

        if (currentAudioRef.current) {
            currentAudioRef.current.onended = null;
            currentAudioRef.current.onerror = null;

            currentAudioRef.current.pause();
            currentAudioRef.current.currentTime = 0;
            currentAudioRef.current.removeAttribute("src");
            currentAudioRef.current.load();
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
                    console.log("[WS] Nhận audio_chunk từ server, check Voice:", isOutVoiceRef.current);

                    if (isOutVoiceRef.current && receivedMsg.audio_data) {
                        audioQueueRef.current.push({
                            audio_data: receivedMsg.audio_data,
                            sentence: receivedMsg.text || ""
                        });

                        if (!isPlayingRef.current) {
                            playNextAudioChunk();
                        }
                    }
                }
                else if (receivedMsg.type === "transcribed_text") {
                    const MessObj = new MessageSchema(receivedMsg.role, "text", receivedMsg.content);
                    setMessages((prev) => [...prev, MessObj]);
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
        
        setIsOutVoice(newState);
        if (isOutVoiceRef) {
            isOutVoiceRef.current = newState;
        }

        if (!newState) {
            stopAudioPlayback();
        }

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
            setIsOutVoice: handleToggleVoice,
            startListening,
            stopListening,
            toggleMic: (isListening ? stopListening : startListening),
            isListening,
            toggleVoice,
            SubText, setSubText
        }}>
            {children}
        </ChatContext.Provider>
    );
}

export function useChat() {
    const context = useContext(ChatContext);
    return context;
}