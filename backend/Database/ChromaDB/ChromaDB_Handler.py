from langchain_core.tools import tool
from Database.ChromaDB.ChromaDBMain import insert_memory, update_memory_doc, delete_memory_doc

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



async def handle_general_memory(action: str, doc_id: str = None, content: str = None, category: str = "general") -> dict:
    try:
        if action == "add":
            if not content:
                return {"success": False, "error": "Missing content for add action"}
            new_id = insert_memory(content, category)
            return {"success": True, "action": "add", "doc_id": new_id}
            
        elif action == "update":
            if not doc_id or not content:
                return {"success": False, "error": "Missing doc_id or content for update action"}
            update_memory_doc(doc_id, content, category)
            return {"success": True, "action": "update", "doc_id": doc_id}
            
        elif action == "delete":
            if not doc_id:
                return {"success": False, "error": "Missing doc_id for delete action"}
            delete_memory_doc(doc_id)
            return {"success": True, "action": "delete", "doc_id": doc_id}
            
        return {"success": False, "error": "Invalid action"}
    except Exception as e:
        return {"success": False, "error": str(e)}


