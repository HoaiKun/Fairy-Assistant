import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import FairyUI from "./FairyUI";
import "./App.css";
import {ChatForm, MessageCotainer, MessageSchema, Transcribe} from "./ChatBox";
import { useChat } from "./ChatProvider";

function App() {

  const [OuterRingRotateSpeed, setOuterRingRotateSpeed] = useState(120);
  const [PulseScaleValue, setPulseScaleValue] = useState([1, 0.95, 1.05, 1]);
  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");



  const {Messages, setMessages, InputText, setInputText, sendMessage, iChatHistory, setiChatHistory} = useChat();

  return (
    <main className="flex w-full h-full items-center justify-center"  >
      <div className="flex bg-cyan-800 h-full w-full justify-center items-center">

        <FairyUI 
        RotateReverse= {false} 
        PulseKeyFrameValue={PulseScaleValue} 
        RotateSpeed = {OuterRingRotateSpeed} 
        PulseDuration={1} 
        MasterCycle={2.9} 
        className ="absolute z-0 items-center justify-center w-full h-full rounded-full"></FairyUI>
        
        <div className="absolute z-10 w-full h-19/20 flex flex-col justify-center items-center gap-2">

          <div className= {`min-h-0 w-full  flex-1 flex justify-center items-center overflow-hidden`}>
            {iChatHistory &&  <MessageCotainer MessageArray = {Messages}></MessageCotainer>}
          </div>

          <div className= {`shrink-0 h-auto w-full flex flex-col justify-center items-center`}>
            <Transcribe></Transcribe>
            <ChatForm ></ChatForm>
          </div>
          
        </div>


      </div> 
    </main>
  );
}

export default App;
