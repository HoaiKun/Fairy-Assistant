import { useState , useEffect } from "react";
import { useChat } from "./ChatProvider";

export class MessageSchema {
    constructor(role, type, content, attachfile)
    {
        this.role = role;
        this.type = type;
        this.content = content;
        this.attachfile = attachfile;
    }
}

export function ChatForm({BorderColor = "border-blue-300/50"})
{

    const {InputText, setInputText, sendMessage , iChatHistory,setiChatHistory, IsInVoice, setIsInVoice, IsOutVoice, setIsOutVoice, sendVoiceMessage, startListening,    
            stopListening,
            isListening,
            toggleMic,
            toggleVoice} = useChat();
    const handleSubmit = (e) => {
    e.preventDefault();     

    let MessObj = new MessageSchema("user", "text", InputText)

    sendMessage(MessObj);
    };

    const handleKeyDown = (e) => {
        if(e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    }


    return(

        <main className="container bg-transparent h-30dvh w-full">
            <form onSubmit={handleSubmit} className= {`border  rounded-2xl flex items-stretch ${BorderColor}  justify-center w-full h-auto bg-transparent p-1`}>
               
                <textarea value={InputText} onChange={(e) =>setInputText(e.target.value)} onKeyDown={handleKeyDown}
                 className="h-20dvh w-4/5 drop-shadow-2xl resize-none p-1 rounded-2xl 
                focus:outline-none focus:ring-0 outline-none
                overflow-auto
                text-1xl"></textarea>

                <div className="flex flex-col w-1/5 self-stretch bg-transparent justify-center p-1 gap-1.5">
                     <button className= {`flex-2 w-full bg-cyan-100 rounded-2xl hover:bg-cyan-500 transition-colors`} type="submit">Enter</button>
                     <div className=" flex flex-1 w-full gap-1 ">

                            <button className= {`flex-1 flex self-stretch rounded-2xl transition-colors ${!isListening ? "bg-cyan-100" : "bg-cyan-500"} items-center justify-center`} type="button" onClick={toggleMic}>
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
                                <path d="M8 1a2 2 0 0 0-2 2v4a2 2 0 1 0 4 0V3a2 2 0 0 0-2-2Z" />
                                <path d="M4.5 7A.75.75 0 0 0 3 7a5.001 5.001 0 0 0 4.25 4.944V13.5h-1.5a.75.75 0 0 0 0 1.5h4.5a.75.75 0 0 0 0-1.5h-1.5v-1.556A5.001 5.001 0 0 0 13 7a.75.75 0 0 0-1.5 0 3.5 3.5 0 1 1-7 0Z" />
                                </svg>
                            </button>

                            <button className= {`flex-1 flex self-stretch rounded-2xl transition-colors ${!IsOutVoice ? "bg-cyan-100" : "bg-cyan-500"} items-center justify-center`} type="button"
                            onClick={toggleVoice}>
                                {
                                    IsOutVoice ? 
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                                    </svg>
                                    :
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                                    </svg>


                                }
                                
                            </button>

                            <button className= {`flex-1 flex self-stretch rounded-2xl transition-colors ${!iChatHistory ? "bg-cyan-100" : "bg-cyan-500"} items-center justify-center`} onClick={() => setiChatHistory(!iChatHistory)} type="button">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
                                <path d="M2 4a2 2 0 0 1 2-2h8a2 2 0 1 1 0 4H4a2 2 0 0 1-2-2ZM2 9.25a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 9.25ZM2.75 12.5a.75.75 0 0 0 0 1.5h10.5a.75.75 0 0 0 0-1.5H2.75Z" />
                                </svg>
                            </button>

                     </div>
                </div>
            </form>
        </main>
    )
};

export function MessageFrame({Content = "NULL", role = "bot", type="text"})
{
    
    return(
        <main className="container w-2/3 h-auto bg-cyan-950 rounded-2xl pt-1 pb-1 pl-2 pr-2">
            {type === "image" ?
            <div className="h-full w-full">
                <img src={Content} alt="IMAGE" className="h-full w-full object-cover block">
                </img>
            </div> :
            <p className=" w-full h-ful text-white whitespace-pre-line">{Content}</p> 
            
            }
        </main>
    )
}



export function MessageCotainer({MessageArray = [{role:"bot", type:"text", content:"GREETING MASTER!"}], 
    BorderColor = "border-blue-500"})
{
    const [fBorderColor, setfBorderColor] = useState(BorderColor);

    useEffect(()=>{
        setfBorderColor(BorderColor);
    }, [fBorderColor,BorderColor]);

    return (
        <main className="container w-full h-full min-h-0">
            <div className={`h-full w-full ${fBorderColor}  rounded-2xl p-2 bg-transparent overflow-y-auto overflow-x-hidden`}>
                {
                    MessageArray.map((msg, index) => (
                        <div key={index} className={`w-full h-auto m-1 flex ${
                            msg.role == "bot" ? 
                            "justify-start" :
                            "justify-end"
                        }`}>
                            <MessageFrame Content={msg.content} msg={msg.role} type={msg.type}></MessageFrame>
                        </div>
                    ))
                }
            </div>
        </main>
    )
};

export function Trans({content = "NULL"})
{
    return(
        <div className="w-auto h-auto">
            <h1 className="text-white text-1xl">{content}</h1>
        </div>
        
    )
}