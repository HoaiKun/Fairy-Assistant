import json
from tools.get_weather import get_current_weather
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
            "description": "Get deeply information that storage in the vector database  (for example: user's previous chat session, user's recent activities) ",
            "parameters" : {
                "type" : "object",
                "properties" : {
                    "search_query" : {
                        "type" : "string",
                        "description" : "Name of a specific city or region (Ha Noi, Tokyo,...)"
                    },
                },
                "required" : ["search_query"],
            }
    },

    {
        "type": "function",
        "name" : "get_current_weather",
        "description": "Get the weather information in specific region",
        "parameters" : {
            "type" : "object",
            "properties" : {
                "location" : {
                    "type" : "string",
                    "description" : "Name of a specific city or region (Ha Noi, Tokyo,...)"
                },
                "unit" : {
                    "type":"string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                }
            },
            "required" : ["location"],
        }
    },
    #More tools here
]



tool_registry = {
    "get_current_weather" : get_current_weather,
    "get_dynamic_memories" : get_dynamic_memories

}