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

export function ChatForm({BorderColor = "border-blue-300"})
{

    const {InputText, setInputText, sendMessage , iChatHistory,setiChatHistory} = useChat();


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
                     <button className=" flex-2 w-full bg-amber-200 rounded-2xl hover:bg-amber-400 transition-colors" type="submit">Enter</button>
                     <div className=" flex flex-1 w-full gap-1 ">
                            <button className="flex-1 self-stretch rounded-2xl transition-colors bg-pink-300 hover:bg-pink-500 item-center justify-center" type="button">M</button>
                            <button className="flex-1 self-stretch rounded-2xl transition-colors bg-pink-300 hover:bg-pink-500 item-center justify-center" onClick={() => setiChatHistory(!iChatHistory)} type="button">M</button>
                     </div>
                </div>
            </form>
        </main>
    )
};

export function MessageFrame({Content = "NULL", role = "bot"})
{
    
    return(
        <main className="container w-2/3 h-auto bg-black rounded-2xl pt-1 pb-1 pl-2 pr-2">
            <p className=" w-full h-ful text-white whitespace-pre-line">{Content}</p>
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
            <div className={`h-full w-full ${fBorderColor} border rounded-2xl p-2 bg-transparent overflow-y-auto overflow-x-hidden`}>
                {
                    MessageArray.map((msg, index) => (
                        <div key={index} className={`w-full h-auto m-1 flex ${
                            msg.role == "bot" ? 
                            "justify-start" :
                            "justify-end"
                        }`}>
                            <MessageFrame Content={msg.content} msg={msg.role}></MessageFrame>
                        </div>
                    ))
                }
            </div>
        </main>
    )
};

export function Transcribe({content = "NULL"})
{
    return(
        <div className="w-auto h-auto">
            <h1 className="text-white text-1xl">{content}</h1>
        </div>
        
    )
}