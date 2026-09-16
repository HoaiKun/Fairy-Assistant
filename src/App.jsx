import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import FairyUI from "./FairyUI";
import "./App.css";
import {ChatForm} from "./ChatBox";

function App() {

  const [OuterRingRotateSpeed, setOuterRingRotateSpeed] = useState(60);

  const [PulseScaleValue, setPulseScaleValue] = useState([1, 0.95, 1.05, 1]);

  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");

  return (
    <main className="flex w-full h-full items-center justify-center"  >
      <div className="flex  bg-cyan-200 h-full w-full justify-center items-center">

        <FairyUI 
        RotateReverse= {false} 
        PulseKeyFrameValue={PulseScaleValue} 
        RotateSpeed = {OuterRingRotateSpeed} 
        PulseDuration={1} 
        MasterCycle={2.9} 
        className ="absolute items-center justify-center w-full h-full rounded-full"></FairyUI>

        <ChatForm className=" absolute bg-red-400 w-1/2 h-auto"></ChatForm>

      </div> 
    </main>
  );
}

export default App;
