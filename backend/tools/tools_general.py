import json
from tools.get_dynamic_memories import get_dynamic_memories
tools_schema = [

    #Built in tools
    {
        "type": "web_search_preview"
    },

    # 2. Máy ảo chạy mã Python tính toán/xử lý số liệu
  

    # 3. Tra cứu tài liệu nội bộ qua Vector Store
    

    ### Custom tools

    {
        "type": "function",
        "name" : "get_dynamic_memories",
        "description": ("A semantic description of the user information being sought (e.g.,"
                " 'user's class schedule', 'interests', 'weekly plan')."
                " Incorporate the intent spanning previous messages,"
                " rather than relying solely on keywords from the final message."),
        "parameters" : {
            "type" : "object",
            "properties" : {
                "search_query" : {
                    "type" : "string",
                    "description" : ("A semantic description of what needs to be retrieved (e.g., "
                    "'lịch học thời khóa biểu', 'thói quen sinh hoạt', 'kế hoạch tuần', 'work schedule'). "
                    "Incorporate the overall context of previous turns instead of just the latest word.")
                },
                "limit" :
                {
                    "type" : "integer",
                    "description" : "The limit of the searching attemp, the greater the deeper to search and more result to return"
                }
            },
            
            "required" : ["search_query"],
        }
    },

    #More tools here
]


tool_registry = {
    "get_dynamic_memories" : get_dynamic_memories

}