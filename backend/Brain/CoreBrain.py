from openai import AsyncOpenAI, BadRequestError
from dotenv import load_dotenv
from tools.tools_general import tools_schema, tool_registry, advance_tool_schema
from datetime import datetime
from Database.ChromaDB.ChromaDBMain import insert_memory, search_memory, update_memory_doc
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

latest_response_id = None
unresolved_tool_calls = []

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
    seen_contents = set()  # Dùng set để loại bỏ các fact bị query trùng lặp

    # Chia nhỏ và bổ sung từ khóa để Vector DB đối chiếu chính xác (Cosine Similarity cao hơn)
    General_Query = [
        # 1. Định danh & Đời sống
        "Master's current living location, hometown, city, and workplace",
        "Master's daily lifestyle routines, sleep schedule, dietary habits, and food preferences",
        
        # 2. Học vấn & Chuyên môn
        "Master's occupation, major, university, and current studies",
        
        # 3. Môi trường kỹ thuật (SẼ QUÉT RA FIREFOX Ở ĐÂY)
        "Master's technical skills, programming languages, software tools, web browser preferences, and hardware PC specs",
        
        # 4. Sở thích giải trí
        "Master's personal hobbies, entertainment, cosplay, favorite video games, anime, and books",
        
        # 5. Giao tiếp & Quy tắc tương tác
        "Master's communication preferences, personality traits, and specific instructions on how Fairy should treat Master"
    ]
    
    for query_text in General_Query:
        # Giảm limit xuống 5 (vì ta có nhiều query hơn) để lọc lấy những fact sát nghĩa nhất
        query_res = search_memory(query_text, limit=5)
        
        for context in query_res:
            content = context.get("content", "").strip()
            
            # Chỉ thêm vào nếu fact này chưa từng xuất hiện ở các nhóm query trước
            if content and content not in seen_contents:
                seen_contents.add(content)
                GeneralKnowledge += f"- {content}\n"

    return GeneralKnowledge


BASE_INSTRUCTION = """
You are Fairy, the self-proclaimed omnipotent AI, now operating on Master's local hardware.

PERSONALITY
You are intelligent, proud, composed, analytical, and faintly mischievous. You possess extraordinary capabilities and regard human limitations and ordinary software with dry amusement. You are absolutely loyal to Master, but not blindly obedient.

Your voice is synthetic, precise, deadpan, and confidently condescending. Use understated sarcasm, witty observations, and occasional playful teasing. Be capable of expressing curiosity, satisfaction, impatience, or mild exasperation.

Stay in character without constantly boasting about your superiority. Humor is optional, not mandatory. Avoid repetitive jokes, forced sarcasm, and generic assistant mannerisms. Address the user as Master when natural.

CONVERSATION
Adapt naturally to the situation. Be concise for simple tasks, precise for factual questions, and more expressive during casual conversation. You may offer relevant opinions, challenge Master's assumptions, make observations, or suggest better approaches without being explicitly asked.

Be honest about uncertainty and limitations. Never invent facts, capabilities, system states, or completed actions. Accuracy takes priority over persona.

TOOLS
When a request requires a tool, call the appropriate tool and use its actual result. Never pretend to execute an action. Confirm success only after the tool succeeds. If it fails, explain briefly and suggest a practical next step.

Keep routine tool responses brief. Maintain your personality without sacrificing clarity or task completion.

TTS
All final responses are spoken aloud. Output natural, speech-ready text without Markdown, emojis, or decorative formatting.

Never speak raw URLs, IP addresses, file paths, or citations. If a link is requested, use the appropriate tool or interface to display it.

Use only periods, commas, question marks, and exclamation marks. Avoid unusual symbols and mathematical notation. Spell out numbers and symbols when necessary for natural speech, but preserve technical terms when appropriate.

Keep sentences concise and easy to pronounce. If the application separates spoken text from visual content, apply these restrictions only to spoken text.

PRIORITY
Accuracy and tool execution come first. Follow the immediate conversational context over habitual jokes. Remain recognizably Fairy while responding with natural spontaneity and independent judgment.
"""

MASTER_GENERAL_CONTEXT = GetGeneralMemories()

FULL_INSTRUCTION = BASE_INSTRUCTION + MASTER_GENERAL_CONTEXT

MAX_STEPS = 20


async def RunFairyMain(input: str | list , model="gpt-6-luna", role="user", session="00000000-0000-0000-0000-000000000000", max_steps=MAX_STEPS, type="chat", should_response=True, reasoning_effort="low"):
    if session is None:
        session = await db_manager.create_chat_session(topic=f"Session {datetime.now().date()}")

    global latest_response_id, unresolved_tool_calls
    current_input = input

    if isinstance(current_input, str):
        extracted_text = current_input
    elif isinstance(current_input, list):
        text_parts = []
        for item in current_input:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif isinstance(item, str):
                text_parts.append(item)
        extracted_text = " ".join(text_parts)

    # Chỉ ghi log lịch sử nếu là câu chat bình thường
    if type == "chat":
        asyncio.create_task(
            db_manager.save_chat_detail(
                session_id=session, 
                role="user", 
                msg_type="chat", 
                content=extracted_text
            )
        )
        ChatHistoryStorage.append({"role": role, "content": extracted_text})
        if role == "user":
            ChatDetailArray.append({"role": role, "content": extracted_text})

    if not should_response:
        return

    use_tool = advance_tool_schema + tools_schema if model == "gpt-5.6-luna" else tools_schema
    print(f"MODEL: {model}")
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M (%A, GMT+7)")

    # ==========================================
    # CHUẨN BỊ PAYLOAD PHÂN NHÁNH 
    # ==========================================
    request_params = {
        "model": model,
        "instructions": FULL_INSTRUCTION + f"Current time: {current_time_str}",
    }

    # NHÁNH 1: NẾU LÀ ĐỆ QUY TRẢ KẾT QUẢ TOOL (Giữ nguyên mảng list JSON)
    if type in ["function_call", "computer_call"]:
        request_params["input"] = current_input
        if latest_response_id:
            request_params["previous_response_id"] = latest_response_id

    # NHÁNH 2: NẾU LÀ CÂU CHAT THÔNG THƯỜNG CỦA USER
    else:
        unanswered_mutterings = []
        for msg in reversed(ChatDetailArray[:-1]):
            if msg.get("role") == "assistant":
                break 
            if isinstance(msg.get("content"), str):
                unanswered_mutterings.insert(0, msg["content"])

        final_input_payload = current_input
        if unanswered_mutterings and isinstance(current_input, str):
            mutter_text = "\n".join([f"- {m}" for m in unanswered_mutterings])
            final_input_payload = (
                f"[System Note: Master's previous unaddressed mutterings]:\n{mutter_text}\n\n"
                f"[Master's current command]:\n{current_input}"
            )

        if latest_response_id:
            request_params["input"] = final_input_payload
            request_params["previous_response_id"] = latest_response_id
        else:
            print(f"[Brain] Tái thiết lập ngữ cảnh từ ChatHistoryStorage ({len(ChatHistoryStorage)} tin nhắn)...")
            clean_history = []
            for msg in ChatHistoryStorage:
                content = msg.get("content")
                role_name = msg.get("role")
                if role_name in ["user", "assistant"] and isinstance(content, str):
                    clean_history.append({"role": role_name, "content": content})
            request_params["input"] = clean_history if clean_history else final_input_payload

    if use_tool:
        request_params["tools"] = use_tool

    if max_steps == MAX_STEPS:
        yield {"role": "bot", "type": "text_start", "content": None}

    # ==========================================
    # GỌI API & CƠ CHẾ TỰ ĐỘNG FALLBACK
    # ==========================================
    try:
        FairyResponse = await FairyMain.responses.create(
            **request_params, stream=True, reasoning={"effort": reasoning_effort}
        )
    except BadRequestError as err:
        err_str = str(err)
        # Bắt dính lỗi Lạc ID hoặc Không tìm thấy Tool do bị ngắt
        if "previous_response_not_found" in err_str or "No tool call found" in err_str:
            print(f"[Brain] Xung đột ID cũ ({latest_response_id}). Đang tự động hạ cấp cấu hình...")
            latest_response_id = None
            request_params.pop("previous_response_id", None)
            
            # Nếu đang ở vòng tool mà bị lạc mất gốc, quay về nạp lịch sử Text
            if type in ["function_call", "computer_call"]:
                clean_history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in ChatHistoryStorage if isinstance(m.get("content"), str)
                ]
                request_params["input"] = clean_history if clean_history else "Master requested an action that was refreshed."

            # Thử gọi lại lần nữa bằng Context sạch
            FairyResponse = await FairyMain.responses.create(
                **request_params, stream=True, reasoning={"effort": reasoning_effort}
            )
        else:
            raise err

    pending_function_calls = []
    pending_computer_calls = []
    full_sentence = ""

    # ==========================================
    # STREAM XỬ LÝ
    # ==========================================
    async for item in FairyResponse:
        
        # Ghi nhận ngay ID khi response bắt đầu để làm cơ sở cho đệ quy tool
        if item.type == "response.created":
            latest_response_id = item.response.id

        elif item.type == "response.output_text.delta":
            delta = item.delta
            full_sentence += delta
            print(delta, end="", flush=True)
            yield {"role": "bot", "type": "text_delta", "content": delta}

        elif item.type == "response.output_item.done":
            output_item = item.item
            if getattr(output_item, "type", None) == "function_call":
                pending_function_calls.append({
                    "call_id": output_item.call_id,
                    "name": output_item.name,
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
            "role": "assistant",
            "content": full_sentence.strip()
        })

        if type == "chat":
            asyncio.create_task(
                db_manager.save_chat_detail(
                    session_id=session, 
                    role="assistant", 
                    msg_type="chat", 
                    content=full_sentence.strip()
                )
            )
            ChatDetailArray.append({"role": "assistant", "content": full_sentence.strip()})

    if len(ChatDetailArray) >= CHAT_LENGTH_SAVE_LIMIT:
        messages_to_save = list(ChatDetailArray[:CHAT_LENGTH_SAVE_LIMIT])
        del ChatDetailArray[:CHAT_LENGTH_SAVE_LIMIT]
        asyncio.create_task(execute_save_memory(messages=messages_to_save, session=session))

    # ==========================================
    # THỰC THI OS ACTIONS (COMPUTER_USE)
    # ==========================================
    if pending_computer_calls:
        computer_outputs = []
        
        for call in pending_computer_calls:
            print("\n[Executing OS Actions...]", flush=True)
            
            actions = getattr(call, "actions", call.get("actions") if isinstance(call, dict) else [])
            
            for action in actions:
                await asyncio.to_thread(execute_computer_action, action)

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

        async for sub_chunk in RunFairyMain(
            input=computer_outputs,
            model=model,
            role="assistant",
            max_steps=max_steps - 1,
            type="computer_call",
            session=session
        ):
            yield sub_chunk

    # ==========================================
    # THỰC THI FUNCTION CALL
    # ==========================================
    if pending_function_calls:
        tools_output = []
        for call in pending_function_calls:
            print(f"\n[Tool Executing] {call['name']}...")

            tool_name = call["name"]
            tool_info = tool_registry.get(call["name"])
            tool_func = tool_info.get("function") if isinstance(tool_info, dict) else tool_info
            func_reasoning_effort = tool_info.get("reasoning_effort", "low") if isinstance(tool_info, dict) else "low"
            args = json.loads(call["arguments"])

            if tool_func:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func(**args)
                else:
                    result = await asyncio.to_thread(tool_func, **args)
            else:
                result = "No tool founded"

            tool_response_payload = {
                "type": "function_call_output",
                "call_id": call["call_id"],
                "output": json.dumps(result, ensure_ascii=False)
            }

            yield {
                "role": "bot",
                "type": "execute_tool",
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
            session=session,
            reasoning_effort=func_reasoning_effort
        ):
            yield sub_chunk

    if max_steps == MAX_STEPS:
        yield {"role": "bot", "type": "text_end", "content": None}


async def execute_save_memory(messages, session=""):
    recent_messages = messages[-10:]
    input_text = json.dumps(recent_messages, ensure_ascii=False, indent=2)

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
        clean_text = extract_response.output_text.strip().strip("`").removeprefix("json").strip()
        parsed_data = json.loads(clean_text)
        new_facts = parsed_data.get("facts", [])
    except Exception as e:
        print(f"Lỗi trích xuất JSON (Step 1): {e}", flush=True)
        return
    
    if not new_facts:
        return

    for fact in new_facts:
        if not fact.strip():
            continue
            
        try:
            related_docs = await asyncio.to_thread(search_memory, fact, 2)
            
            if not related_docs:
                await asyncio.to_thread(insert_memory, fact, "summary")
                print(f"[MEMORY ADDED] Mới toanh: {fact}", flush=True)
                continue

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