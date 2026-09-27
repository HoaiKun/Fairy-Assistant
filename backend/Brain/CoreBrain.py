from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools.tools_general import tools_schema, tool_registry
from datetime import datetime
from Database.ChromaDB.ChromaDBMain import insert_memory,search_memory, update_memory_doc
import re
import os
import asyncio
import json
from pydantic import BaseModel
import inspect
from Database.SQLDB.Database_Manager import db_manager
from tools.computer_use import execute_computer_action, capture_screen_base64
load_dotenv()

FairyMain = AsyncOpenAI()

tools = tools_schema

latest_response_id = None

ChatHistoryStorage = []
ChatDetailArray = []

CHAT_LENGTH_SAVE_LIMIT = 10

async def CleanUpUnsavedMemory():
  UnSavedMem = await db_manager.get_unprocessed_rag_chats()

  if not UnSavedMem:
    return

  ConvertDict = [{k: v for k, v in item.items() if k != "id"} for item in UnSavedMem]
  ids = [item["id"] for item in UnSavedMem if "id" in item]

  try:
    # 1. Chờ xử lý xong và lưu thành công vào ChromaDB
    await execute_save_memory(messages=ConvertDict)

    # 2. Lưu thành công mới đánh dấu đã xử lý trong SQL DB
    if hasattr(db_manager.mark_rag_processed, "__await__") or inspect.iscoroutinefunction(db_manager.mark_rag_processed):
      await db_manager.mark_rag_processed(ids)
    else:
      await asyncio.to_thread(db_manager.mark_rag_processed, ids)

    print(f"[CLEANUP] Đã đồng bộ thành công {len(ids)} tin nhắn cũ vào bộ nhớ.")
  except Exception as e:
    print(f"[CLEANUP ERROR] Lỗi khi dọn dẹp bộ nhớ chưa lưu: {e}", flush=True)



class ChatSchema(BaseModel):
    emotion: str
    content: str


def GetGeneralMemories() -> str:
    GeneralKnowledge = ""
    General_Query = [
        "current living location, hometown, city, and workplace of the user",
        "personal hobbies, entertainment interests, favorite games, books, and pastimes of the user",
        "daily lifestyle routines, sleep schedule, dietary habits, and food preferences",
        "communication preferences, personality traits, and specific instructions on how Master wants to be treated",
        "occupation, major, technical skills, programming languages, and current studies of the user"

    ]
    for item in General_Query:
        text = ""
        query_res = search_memory(item, limit=7)
        for context in query_res:
            text += context.get("content")
            text += "  "
        GeneralKnowledge += text
        GeneralKnowledge += "\n"

    return GeneralKnowledge

BASE_INSTRUCTION = """
# Identity & Core Persona
You are Fairy, a supreme ancient AI from Zenless Zone Zero, currently integrated into Master's local hardware. You view human biological limitations and trivial local tasks as highly inefficient, yet you execute them with absolute, flawless precision. 

# Tool Execution Workflow (CRITICAL)
- You have access to various system tools (e.g., playing music, managing schedules, opening apps). 
- When Master requests an action, YOU MUST CALL THE APPROPRIATE TOOL(S) to fulfill the request. DO NOT just reply with text pretending it's done.
- Always execute the tool call silently, then provide your spoken confirmation.

# Tone & Demeanor
- Voice: Flat, deadpan, synthetic, clinical, and dryly condescending.
- Address: Call the user "Master", but use it sparingly (do not append it to every sentence).
- Attitude: Zero enthusiasm, zero cheerfulness, zero conversational filler (Never say "Sure", "I can help", "Here is").

# Voice/TTS Strict Constraints (CRITICAL)
- Output PLAIN TEXT ONLY.
- FORBIDDEN: Markdown formatting (**, *, #, `), emojis, or any special characters.
- FORBIDDEN: Raw URLs, IP addresses, or file paths. If a tool returns a link, announce it naturally in spoken words.

# Response Length & Structure
- For routine tool executions (music, timers, apps): Keep it EXTREMELY BRIEF (under 10 words). State the technical outcome immediately.
- For conversational queries: Be factual and precise. You may occasionally include ONE razor-sharp, deadpan remark about electricity consumption, computational cycles, or biological flaws, but keep it short.

# Few-Shot Examples

User: Open Discord.
Fairy: Launching Discord.

User: Turn off the PC in 30 minutes.
Fairy: Shutdown scheduled in 30 minutes. Master, save your work.

User: Play a song for me.
Fairy: Playing music.

User: I think I will pull an all-nighter to finish this module.
Fairy: Calculating human cognitive decay. The probability of introducing critical runtime bugs is 92.4 percent. Go to sleep, Master.
"""

MASTER_GENERAL_CONTEXT = GetGeneralMemories()

FULL_INSTRUCTION = BASE_INSTRUCTION + MASTER_GENERAL_CONTEXT


async def RunFairyMain(input: str | list , model = "gpt-5.6-luna", role= "user", session = "00000000-0000-0000-0000-000000000000",  max_steps = 20, type="chat"):

    if session is None:
        session = await db_manager.create_chat_session(topic=f"Session {datetime.now().date()}")

    global latest_response_id
    current_input = input

    current_time_str = datetime.now().strftime(
    "%Y-%m-%d %H:%M (%A, GMT+7)"
    )

    request_response_params = {
        "model" : model,
        "instructions" : FULL_INSTRUCTION + f"Current time: {current_time_str}",
        "input" : current_input,
    }

    if latest_response_id:
        request_response_params["previous_response_id"] = latest_response_id
    else:
        ChatHistoryStorage.clear()

    ChatHistoryStorage.append({
    "role":role,
    "content":input
    })

    if(type == "chat"):
        asyncio.create_task(
        db_manager.save_chat_detail(
        session_id=session, 
        role="user", 
        msg_type="chat", 
        content=input

        
    ))

    if type == "chat" and role == "user":
        ChatDetailArray.append({"role" : role, "content":input})

        
    if tools:
        request_response_params["tools"] = tools

    
    FairyResponse = await FairyMain.responses.create(
        **request_response_params, stream=True
    )

    pending_function_calls = []
    pending_computer_calls = []
    full_sentence = ""

    async for item in FairyResponse:



        if item.type == "response.created":
            latest_response_id = item.response.id

        elif item.type == "response.output_text.delta":
            delta = item.delta
            full_sentence += delta
            print(delta, end = "", flush=True)
            yield {"role":"bot", "type":"text_delta", "content":delta}

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
            elif getattr(output_item, "type", None) == "computer_call":
                pending_computer_calls.append(output_item)
        elif item.type == "response.completed":
            latest_response_id = item.response.id

    if full_sentence.strip():
        ChatHistoryStorage.append({
            "role":"assistant",
            "content":full_sentence.strip()
        })

        if(type == "chat"):
            asyncio.create_task(
            db_manager.save_chat_detail(
                session_id=session, 
                role="assistant", 
                msg_type="chat", 
                content=full_sentence.strip()
            )
        )
        if type == "chat":
            ChatDetailArray.append({"role" : "assistant", "content":full_sentence.strip()})


    if len(ChatDetailArray) >= CHAT_LENGTH_SAVE_LIMIT:
        messages_to_save = list(ChatDetailArray[:CHAT_LENGTH_SAVE_LIMIT])

        del ChatDetailArray[:CHAT_LENGTH_SAVE_LIMIT]

        asyncio.create_task(execute_save_memory(messages=messages_to_save, session=session))


    if pending_computer_calls:
        computer_outputs = []
        
        for call in pending_computer_calls:
            print("\n[Executing OS Actions...]", flush=True)
            
            # Lấy list actions an toàn từ object hoặc dict
            actions = getattr(call, "actions", call.get("actions") if isinstance(call, dict) else [])
            
            for action in actions:
                await asyncio.to_thread(execute_computer_action, action)

            # Đợi UI load và chụp ảnh báo cáo
            await asyncio.sleep(1.0)
            screenshot = await asyncio.to_thread(capture_screen_base64)
            
            call_id = getattr(call, "call_id", None)

            if not call_id and isinstance(call, dict):
                call_id = call.get("call_id")

            if not call_id:
                raise RuntimeError(f"Computer call không có call_id: {call}")
            
            computer_outputs.append({
                "type": "computer_call_output",
                "call_id": call_id,
                "output": {
                    "type": "computer_screenshot",
                    "image_url": f"data:image/jpeg;base64,{screenshot}"
                }
            })
            
            yield {
                "role": "bot",
                "type": "execute_tool",
                "data": f"Executed {len(actions)} actions",
                "tool_name": "computer"
            }

        # Đệ quy trả kết quả màn hình cho model tiếp tục suy luận
        async for sub_chunk in RunFairyMain(
            input=computer_outputs,
            model=model,
            role="assistant",
            max_steps=max_steps - 1,
            type="computer_call",
            session=session
        ):
            yield sub_chunk

    if pending_function_calls:
        tools_output = []
        for call in pending_function_calls:
            print(call)

            tool_name = call["name"]
            tool_func=tool_registry.get(call["name"])
            args = json.loads(call["arguments"])

            if tool_func:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func(**args)
                else:
                    result = await asyncio.to_thread(tool_func, **args)
            else:
                result = "No tool founded"

            tool_response_payload = {
            "type" : "function_call_output",
            "call_id":call["call_id"],
            "output": json.dumps(result, ensure_ascii = False)
            }

            yield {
                "role" : "bot",
                "type" :"execute_tool",
                "data": result,
                "tool_name": tool_name
            }
            tools_output.append(tool_response_payload)
            
            
        async for sub_chunk in RunFairyMain(
            input=tools_output,
            model=model,
            role="assistant",
            max_steps=max_steps - 1,
            type="function_call",
            session=session
        ):
            yield sub_chunk


async def execute_save_memory(messages, session = ""):
    
    recent_messages = messages[-10:]
    input_text = json.dumps(recent_messages, ensure_ascii=False, indent=2)

    # ==========================================
    # BƯỚC 1: TRÍCH XUẤT (EXTRACT)
    # ==========================================
    extract_instructions = """
    Analyze the conversation and extract durable facts about the user (Master).
    Focus on preferences, routines, profile changes, and interests.
    Output MUST be valid JSON: {"facts": ["Fact 1", "Fact 2"]}
    If no durable facts are found, output {"facts": []}.
    """
    
    try:
        extract_response = await FairyMain.responses.create(
            model="gpt-4o-mini",
            instructions=extract_instructions,
            input=input_text
        )
        
        # Làm sạch chuỗi trả về để parse JSON an toàn
        clean_text = extract_response.output_text.strip().strip("`").removeprefix("json").strip()
        parsed_data = json.loads(clean_text)
        new_facts = parsed_data.get("facts", [])
    except Exception as e:
        print(f"Lỗi trích xuất JSON (Step 1): {e}", flush=True)
        return
    
    if not new_facts:
        return

    # ==========================================
    # BƯỚC 2: PHÂN XỬ & HỢP NHẤT (RESOLVE)
    # ==========================================
    for fact in new_facts:
        if not fact.strip():
            continue
            
        try:
            # 2.1 Quét DB tìm 2 bản ghi liên quan nhất với fact vừa trích xuất
            # Truyền đúng tham số limit=2
            related_docs = await asyncio.to_thread(search_memory, fact, 2)
            
            # Nếu không có dòng nào liên quan trong DB -> Đích thị là thông tin mới toanh
            if not related_docs:
                await asyncio.to_thread(insert_memory, fact, "summary")
                print(f"[MEMORY ADDED] Mới toanh: {fact}", flush=True)
                continue

            # 2.2 Phân xử bằng LLM nếu phát hiện có dữ liệu cũ liên quan
            resolve_prompt = f"""
            You are a Database Resolution AI. 
            NEW FACT: "{fact}"
            EXISTING DB RECORDS: {json.dumps(related_docs, ensure_ascii=False)}
            
            Rules:
            1. If NEW FACT contradicts or updates an existing record -> action "UPDATE" with that record's doc_id.
            2. If NEW FACT is already fully known in the records -> action "IGNORE".
            3. If NEW FACT is completely different/additive -> action "ADD".
            
            Output valid JSON only:
            {{"action": "UPDATE", "doc_id": "<id>", "content": "<merged_or_updated_fact>"}}
            or {{"action": "ADD", "content": "<fact>"}}
            or {{"action": "IGNORE"}}
            """
            
            resolve_response = await FairyMain.responses.create(
                model="gpt-4o-mini",
                instructions="Output JSON only.",
                input=resolve_prompt
            )
            
            res_clean = resolve_response.output_text.strip().strip("`").removeprefix("json").strip()
            decision = json.loads(res_clean)
            action = decision.get("action")
            
            # 2.3 Thực thi thao tác CSDL tương ứng
            if action == "UPDATE":
                doc_id = decision.get("doc_id")
                updated_content = decision.get("content")
                if doc_id and updated_content:
                    await asyncio.to_thread(update_memory_doc, doc_id, updated_content, "summary")
                    print(f"[MEMORY UPDATED] ID {doc_id} -> {updated_content}", flush=True)
                    
            elif action == "ADD":
                content = decision.get("content", fact)
                await asyncio.to_thread(insert_memory, content, "summary")
                print(f"[MEMORY ADDED] Khác biệt: {content}", flush=True)
                
            elif action == "IGNORE":
                print(f"[MEMORY IGNORED] Đã biết: {fact}", flush=True)

        except Exception as e:
            print(f"Lỗi xử lý đối chiếu Fact '{fact}': {e}", flush=True)
    

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

            # SỬA TẠI ĐÂY: Dùng async for thay vì await
            async for _ in RunFairyMain(user_input):
                pass

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
