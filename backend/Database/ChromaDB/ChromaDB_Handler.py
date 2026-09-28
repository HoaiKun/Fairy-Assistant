from langchain_core.tools import tool
from Database.ChromaDB.ChromaDBMain import insert_memory, update_memory_doc, delete_memory_doc, search_memory
from typing import List, Dict, Any, Optional
@tool
def memorize_fact(content: str, category: str = "general") -> str:
    """
    QUIETLY INVOKE THIS TOOL to record new details whenever Master reveals preferences, habits, work, musical tastes, or personal facts.
    You MUST save the information in the third person.
    Examples: "Master loves listening to Youngcaptain", "Master works as a Python Developer".
    """
    doc_id = insert_memory(content, category)
    return f"[Memory Saved] ID: {doc_id}"

@tool
def update_fact(doc_id: str, new_content: str) -> str:
    """
    SILENTLY CALL THIS TOOL to modify/overwrite an OLD memory when the Master changes a habit.
    The doc_id must be retrieved from the 'Master's Context' section of the System Prompt.
    Example: The Master used to prefer React but has now switched to Tauri.
    """
    update_memory_doc(doc_id, new_content)
    return f"[Memory Updated] ID: {doc_id}"

@tool
def forget_fact(doc_id: str) -> str:
    """
    Silently invoke this tool to delete a memory if the Master requests to "forget it" or if the information is no longer accurate.
    """
    delete_memory_doc(doc_id)
    return f"[Memory Deleted] ID: {doc_id}"

# Đóng gói danh sách Tools để export
FAIRY_MEMORY_TOOLS = [memorize_fact, update_fact, forget_fact]



def get_long_term_memories(
    search_query: str, 
    category: Optional[str] = "all", 
    limit: int = 5
) -> str:
    """
    Retrieve user background facts, historical habits, preferences, tech stacks, or past projects.
    
    Args:
        search_query: Concise semantic query focusing on the key topic (e.g., 'favorite framework', 'gym schedule', 'current GPU'). Avoid conversational filler words.
        category: Filter by specific memory domain: 'tech', 'work', 'personal', 'gaming', 'music', or 'all'. Defaults to 'all'.
        limit: Number of top memory entries to retrieve (default is 5).
    """
    memories = search_memory(
        query=search_query, 
        category=None if category == "all" else category, 
        limit=limit
    )

    if not memories:
        return "No relevant past memories found for this query."

    # Format đầu ra dạng text markdown sạch để LLM hiểu trực tiếp
    formatted_output = ["### Retrieved Long-Term Memories:"]
    for idx, mem in enumerate(memories, 1):
        date_str = mem["timestamp"].split("T")[0] if mem.get("timestamp") else "Unknown date"
        formatted_output.append(
            f"{idx}. [{date_str}] ({mem['category']}) {mem['content']}"
        )

    return "\n".join(formatted_output)

