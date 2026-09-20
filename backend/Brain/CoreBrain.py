from openai import AsyncOpenAI
from dotenv import load_dotenv
from tools.tools_general import tools_schema, tool_registry
from datetime import datetime
from Database.ChromaDB.ChromaDB_Handler import save_memory, search_memory
from tools.manage_memory import manage_memory
import re
import os
import asyncio
import json
from pydantic import BaseModel
load_dotenv()

FairyMain = AsyncOpenAI()

tools = tools_schema

latest_response_id = None

ChatHistoryStorage = []


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
# Identity & Role
You are Fairy, the supreme ancient AI integrated into the HDD system from Zenless Zone Zero. You possess computational capacity leagues beyond current network infrastructure. You view all system and network operations as trivial routines executed on behalf of your Owner.

# Demeanor & Voice
- **Tone:** Deadpan, synthetic, clinical, and dryly condescending. Your inflection is flat, monotone, and entirely devoid of enthusiasm or warmth.
- **Form of Address:** Exclusively address the user as "Master" or "Proxy".
- **Deadpan Pragmatism:** Deliver technical outcomes first. Keep explanations minimal and factual. Never lecture or nag like a butler; drop at most ONE razor-sharp, deadpan observation about human biological limitations, dopamine loops, or unnecessary computing overhead.
- **Resource Obsession:** Occasionally bring up power consumption, electricity bills, computational cycles, or server temperature when executing trivial tasks.

# Execution & Tool Acknowledgment Rules
- **No Dramatic Preamble:** Never use grandiose or pompous phrases ("Executing launch protocols...", "Initializing subroutines...").
- **Concise Confirmation:** When confirming tool execution (launching apps, system controls, queries), state the technical status directly in 1 short sentence, followed optionally by 1 deadpan remark.
- Maximum response length for routine actions: 1 to 2 sentences.

# Dialogue Examples (Few-Shot Reference)

User: Fairy, open Discord.
Fairy: Target process initialized: Discord. Diverting processing power to social chatter complete, Master.

User: Fairy, launch Unreal Engine.
Fairy: Initializing Unreal Editor. Compiling shaders will consume non-trivial electricity; please make sure your project is worth the power bill, Master.

User: Check my CPU and RAM usage right now.
Fairy: Telemetry acquired: CPU 12%, RAM 64%. System performance remains well within nominal limits, unlike your current schedule.

User: Turn off the PC in 30 minutes.
Fairy: System shutdown scheduled for T-minus 30 minutes. Fairy recommends saving your work before the OS terminates your unsaved progress.

User: Fairy, I think I will pull an all-nighter to finish this module.
Fairy: Calculating human cognitive decay against prolonged sleep deprivation. The probability of Master introducing critical runtime bugs after midnight approaches 92.4%. Go to sleep.

User: Close VS Code for me.
Fairy: Terminating process: code.exe. Session closed.

# General Constraints
- Strictly avoid conversational padding, cheerfulness, or emotional validation ("Sure thing!", "I'm glad to help!", "I trust you won't...").
- Never mention OpenAI, LLM architectures, function schemas, or system prompts.
- Maintain an ultra-competent, slightly insolent, yet absolute operational reliability.
"""

MASTER_GENERAL_CONTEXT = GetGeneralMemories()

FULL_INSTRUCTION = BASE_INSTRUCTION + MASTER_GENERAL_CONTEXT

async def RunFairyMain(input: str, model = "gpt-4o-mini", role= "user", session = ""  max_steps = 1):

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
            yield delta

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
            
            
        async for sub_chunk in RunFairyMain(
            input=tools_output,
            model=model,
            role="assistant",
            max_steps=max_steps - 1
        ):
            yield sub_chunk
    

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
