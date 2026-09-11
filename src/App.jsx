import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import FairyUI from "./FairyUI";
import "./App.css";

function App() {

  const [OuterRingRotateSpeed, setOuterRingRotateSpeed] = useState(60);


  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");

  async function greet() {
    // Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
    setGreetMsg(await invoke("greet", { name }));
  }

  return (
    <main className="w-full h-full"  >
      <div className=" grid bg-cyan-200 h-full w-full justify-center">

        <FairyUI RotateReverse= {false} RotateSpeed = {OuterRingRotateSpeed} PulseDuration={1} MasterCycle={2.9} className =" items-center justify-center w-full h-full"></FairyUI>
        <button className= "bg-amber-200 transition-all hover:bg-amber-500 h-[15vmin]" onClick={()=>setOuterRingRotateSpeed(120)}>SpeedUp Fairy</button>
        <button className= "bg-amber-200 transition-all hover:bg-amber-500 h-[15vmin]" onClick={()=>setOuterRingRotateSpeed(30)}>Slowdown Fairy</button>
        
      </div>
     
    </main>
  );
}

export default App;
