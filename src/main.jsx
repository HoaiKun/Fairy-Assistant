import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ChatProvider } from "./ChatProvider";
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ChatProvider>
        <App className="w-full h-full"></App>
    </ChatProvider>
    
  </React.StrictMode>,
);
