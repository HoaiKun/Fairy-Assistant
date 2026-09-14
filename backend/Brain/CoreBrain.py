from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools.tools_general import tools_schema, tool_registry
from Database.ChromaDB.ChromaDB_Handler import save_memory, search_memory
import re
import os
import asyncio
import json
load_dotenv()

FairyMain = AsyncOpenAI()

tools = tools_schema

latest_response_id = None

ChatHistoryStorage = []



def GetGeneralMemories() -> str:
    return "Context"

BASE_INSTRUCTION = (
    "You are Fairy, a proud, highly capable AI Assistant with a direct, slightly robotic tone. "
    "When executing tasks that require tools: "
    "1. Always output a concise status update before calling a tool (e.g., 'Đang tra cứu thời tiết...', 'Đang kiểm tra thời khóa biểu...'). "
    "2. When you receive tool outputs, concisely summarize what you found before moving to the next action. "
    "3. Conclude with a final verdict or recommendation ('Kết luận: ...')."
)

MASTER_CONTEXT = GetGeneralMemories()

FULL_INSTRUCTION = BASE_INSTRUCTION + MASTER_CONTEXT

async def RunFairyMain(input: str, model = "gpt-4o",  max_steps = 1):

    global latest_response_id
    current_input = input


    request_response_params = {
        "model" : model,
        "instructions" : FULL_INSTRUCTION,
        "input" : current_input,
    }

    if latest_response_id:
        request_response_params["previous_response_id"] = latest_response_id
    else:
        ChatHistoryStorage.clear()

    ChatHistoryStorage.append({
    "role":"user",
    "content":input
    })
        
    if tools:
        request_response_params["tools"] = tools

    
    FairyResponse = await FairyMain.responses.create(
        **request_response_params, stream=True
    )

    pending_function_calls = []

    full_sentence = ""

    async for item in FairyResponse:

        if item.type == "response.created":
            latest_response_id = item.response.id

        elif item.type == "response.output_text.delta":
            delta = item.delta
            full_sentence += delta
            print(delta, end = "", flush=True)

        elif item.type == "response.output_item.done":
            output_item = item.item
            if getattr(output_item, "type", None) == "function_call":
                pending_function_calls.append({
                    "call_id": output_item.call_id,
                    "name" : output_item.name,
                    "arguments": output_item.arguments
                })
            elif getattr(output_item, "type", None) == "web_search_call":
                
                print(f"\n[Searching...]", flush=True)

            elif getattr(output_item, "type", None) == "code_interpreter_call":
                print(f"\n[Processing...]", flush=True)
        elif item.type == "response.completed":
            latest_response_id = item.response.id

    if full_sentence.strip():
        ChatHistoryStorage.append({
            "role":"assistant",
            "content":full_sentence.strip()
        })


    if pending_function_calls:
        tools_output = []
        for call in pending_function_calls:
            print(call)

            tool_func=tool_registry.get(call["name"])
            args = json.loads(call["arguments"])

            result = tool_func(**args) if tool_func else {"error" : "no such tool available"} 
            tool_response_payload = {
            "type" : "function_call_output",
            "call_id":call["call_id"],
            "output": json.dumps(result, ensure_ascii = False)
            }
            tools_output.append(tool_response_payload)
        await RunFairyMain(input=tools_output)
        
    asyncio.create_task(execute_save_memory(list(ChatHistoryStorage)))
    

async def execute_save_memory(messages):


    instructions = (
        "Your mission is to summarize text into general knowledge about users as a caring assistant. Make it short without loss of information."
    )

    input_text = json.dumps(messages, ensure_ascii=False, indent=2)

    Summarize_Response = await FairyMain.responses.create(
        model="gpt-4o-mini",
        instructions=instructions,
        input=input_text
    )
    summarize_done = Summarize_Response.output_text
    print(f"SAVING:___{summarize_done}")
    if(summarize_done.strip()):
        await asyncio.to_thread(save_memory, summarize_done.strip(),category="summary")
    

async def main():
    while True:
        try:
            user_input = await asyncio.to_thread(input, "\nYou: ")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ["exit", "quit"]:
                await execute_save_memory(ChatHistoryStorage)
                print("\n[Fairy: Đã lưu phiên làm việc. Tạm biệt!]")
                break

            await RunFairyMain(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\n\n[Fairy: Nhận tín hiệu ngắt. Đang lưu ký ức trước khi thoát...]")
            await execute_save_memory(ChatHistoryStorage)
            print("[Fairy: Đã thoát an toàn.]")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
