import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from Brain.CoreBrain import RunFairyMain
app = FastAPI()

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    try:
        while True:
            data_str = await websocket.receive_text()
            data=json.loads(data_str)
            print("Received from cliend", data)

            await websocket.send_text(
                json.dumps({
                    "role":"bot",
                    "type":"text_start",
                    "content": "START",
      
                },ensure_ascii=False)
            )
            
            async for chunk in RunFairyMain(input=data["content"], role=data["role"]):
                await websocket.send_text(
                    json.dumps({
                        "role":"bot",
                        "type":"text_delta",
                        "content":chunk,

                    },ensure_ascii=False)
                )

            await websocket.send_text(
                json.dumps({
                    "role":"bot",
                    "type":"text_end",
                    "content": "START",
 
                },ensure_ascii=False)
            )
            
    except WebSocketDisconnect:
        print("Disconnected Client")
