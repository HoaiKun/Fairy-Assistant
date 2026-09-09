import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import FairyUI from "./FairyUI";
import "./App.css";

function App() {
  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");

  async function greet() {
    // Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
    setGreetMsg(await invoke("greet", { name }));
  }

  return (
    <main className="w-full h-full"  >
      <div className=" grid bg-cyan-900 h-full w-full  justify-center">

        <FairyUI className =" items-center justify-center w-full h-full"></FairyUI>
        

      </div>
     
    </main>
  );
}

export default App;
