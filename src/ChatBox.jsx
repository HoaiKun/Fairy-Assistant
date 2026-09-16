import { useState , useEffect } from "react";

export function ChatForm()
{
    const handleSubmit = (e) => {
    e.preventDefault(); 
    console.log("SUBMITED");
    };

    return(
        <main className="container bg-transparent h-30dvh w-full">
            <form onSubmit={handleSubmit} className=" border border-cyan-300 rounded-2xl flex items-stretch justify-center w-full h-auto bg-transparent p-1">
               
                <textarea className="h-20dvh w-4/5 drop-shadow-2xl resize-none p-1 rounded-2xl 
                focus:outline-none focus:ring-0 outline-none
                overflow-auto
                text-1xl"></textarea>

                <div className="flex flex-col w-1/5 self-stretch bg-transparent justify-center p-1 gap-1.5">
                     <button className=" flex-2 w-full bg-amber-200 rounded-2xl hover:bg-amber-400 transition-colors">Enter</button>
                     <div className=" flex flex-1 w-full gap-1 ">
                            <button className="flex-1 self-stretch rounded-2xl transition-colors bg-pink-300 hover:bg-pink-500 item-center justify-center">M</button>
                            <button className="flex-1 self-stretch rounded-2xl transition-colors bg-pink-300 hover:bg-pink-500 item-center justify-center">M</button>
                     </div>
                </div>
               

            </form>
        </main>
    )
}

export function MessageContainer()
{
    return (
        <main className="container h-full w-full">

        </main>
    )
}
