import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import FairyUI from "./FairyUI";
import "./App.css";

function App() {

  const [OuterRingRotateSpeed, setOuterRingRotateSpeed] = useState(60);

  const [PulseScaleValue, setPulseScaleValue] = useState([1, 0.95, 1.05, 1]);

  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");

  async function greet() {
    // Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
    setGreetMsg(await invoke("greet", { name }));
  }

  return (
    <main className="w-full h-full"  >
      <div className=" grid bg-cyan-200 h-full w-full justify-center">

        <FairyUI RotateReverse= {false} PulseKeyFrameValue={PulseScaleValue} RotateSpeed = {OuterRingRotateSpeed} PulseDuration={1} MasterCycle={2.9} className =" items-center justify-center w-full h-full"></FairyUI>
        <button className="text-2xl text-white bg-amber-300 hover:bg-amber-400 transition-all" onClick={()=>{setPulseScaleValue([1, 0.85, 1.15, 1])}}>UpScale</button>
        <button className="text-2xl text-white bg-amber-300 hover:bg-amber-400 transition-all" onClick={()=>{setPulseScaleValue([1, 0.95, 1.05, 1])}}>DownScale</button>
      </div>
     
    </main>
  );
}

export default App;
