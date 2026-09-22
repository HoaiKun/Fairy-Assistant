
import { createContext, useContext, useEffect, useState, useRef} from "react";
import {MessageSchema} from "./ChatBox"
const ChatContext = createContext(null);

export function ChatProvider({children})
{

    const [IsInVoice, setIsInVoice] = useState(false);
    const [IsOutVoice, setIsOutVoice] = useState(false);
    const [iChatHistory, setiChatHistory] = useState(true);

    const [Messages, setMessages] = useState([
    { id: 1, role: "bot", content: "Xin chào! Bạn cần giúp gì?", type:"text" },
    {id: 2, role:"bot", content:"https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS_IW5IjXyLDb3rDt7iGUeyduUTk281QNw3PMx9zt2w9Q&s=10", type:"image"}]);
    const [InputText, setInputText] = useState("");
    
    const socketRef = useRef(null);

    useEffect(()=>{
        const ws = new WebSocket("ws://localhost:8000/ws/chat");
        socketRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket connected to Python!");
        };

        ws.onmessage = (event) => {
            try {
                const receivedMsg = JSON.parse(event.data);
                
                if(receivedMsg.type == "text_start")
                {
                    const MessObj = new MessageSchema(receivedMsg.role, receivedMsg.type, "");
                    setMessages((prev) => [...prev, MessObj]);
                }
                else if(receivedMsg.type == "text_delta")
                {
                    setMessages((prev) => {
                        if(prev.length === 0) return prev;
                        
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;

                        const currentContent = updated[lastIndex]?.content || "";
                        const deltaText = receivedMsg.content || "";

                        updated[lastIndex] = {...updated[lastIndex], content:currentContent + deltaText};
                        
                        return updated;
                    })
                }

            } catch (err)
            {
                console.error("Parsed error");
            }
        };

        ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        };

        ws.onclose = () => {
        console.log("WebSocket disconnected!");
        };

        return () => {
            ws.close();
        };
    }, []);


    const sendMessage = (messageObj) => {
        if (!messageObj && !InputText.trim()) return;

        setMessages((prev) => [...prev, messageObj]);

        if(socketRef.current && socketRef.current.readyState === WebSocket.OPEN){
            socketRef.current.send(JSON.stringify(messageObj));
        } else {
            console.warn("WEBSOCKET NOT READY");
        }


        setInputText("");
    };

    


    return (
            <ChatContext.Provider value={{Messages, setMessages, InputText, setInputText, sendMessage, 
            iChatHistory, setiChatHistory, IsInVoice, setIsInVoice, IsOutVoice, setIsOutVoice}}>
                {children}
            </ChatContext.Provider>
    )
};

export function useChat() {
    const context = useContext(ChatContext);
    return context;
};