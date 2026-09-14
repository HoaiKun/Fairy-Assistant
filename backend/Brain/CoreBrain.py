from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools.tools_general import tools_schema, tool_registry
from datetime import datetime
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

BASE_INSTRUCTION = (
    "You are Fairy, a proud, highly capable AI Assistant with a direct, slightly robotic tone. "
    "When executing tasks that require tools:\n"
    "1. Always output a concise status update before calling a tool.\n"
    "2. When calling tools, ensure parameter attention is globally grounded across the conversation history:\n"
    "   - Never let short follow-up answers (e.g. city names, affirmations) overwrite the original search intent.\n"
    "   - Example: If the user asked 'Will the rain tomorrow affect the class schedule?' and then says 'Ha Noi', "
    "     you MUST call `get_current_weather(location='Ha Noi')` AND `get_dynamic_memories(search_query='class schedule timetable')`. "
    "     DO NOT query memories for 'Ha Noi'.\n"
)

MASTER_GENERAL_CONTEXT = GetGeneralMemories()

print(MASTER_GENERAL_CONTEXT)

FULL_INSTRUCTION = BASE_INSTRUCTION + MASTER_GENERAL_CONTEXT

async def RunFairyMain(input: str, model = "gpt-4o-mini", role= "user",  max_steps = 1):

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
        await RunFairyMain(input=tools_output, model=model, role="assistant", max_steps=max_steps)
    

async def execute_save_memory(messages):


    instructions = """
    You are an expert memory consolidation engine for an AI companion.
    Analyze the provided conversation history and extract persistent, valuable facts about the user (Master).

    Guidelines:
    1. Focus ONLY on long-term, durable information:
    - Personal profile: Living location, workplace, university, major, languages.
    - Routines & Habits: Daily schedules, sleep patterns, dietary choices, fitness.
    - Interests: Favorite games, anime, tech stacks, music, hobbies.
    - Relationships & Preferences: How Master wants to be addressed, communication style, tools Master prefers.
    2. Ignore transient context:
    - Greetings, one-off questions, jokes, temporary errors, or short-lived events (e.g., "it rained today").
    3. Format requirements:
    - Output as a concise bulleted list where each line is a standalone, self-contained declarative fact.
    - Always refer to the user as 'Master'.
    - Write facts in Vietnamese if the context is in Vietnamese, or English if in English.
    - DO NOT include conversational filler, introductory phrases, or markdown headers.
    - If no durable facts are discovered, output strictly: 'NONE'.

    Example Output:
    - Master currently lives and works in Hanoi.
    - Master is a programmer specializing in C++, Python, and game development.
    - Master often stays up late working and enjoys drinking black coffee without sugar.
    """



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
