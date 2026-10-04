import json
from tools.search_tool import tool_multimedia_search
from extensions.app_tracking import app_tracker 
from extensions.system_tracking import system_tracker
from extensions.pc_listener import FairyEarInstance
from tools.manage_schedule import manage_schedule
from tools.execute_terminal import execute_terminal_command
from tools.music_tool import manage_playback
from Database.ChromaDB.ChromaDB_Handler import memory_handler 
tools_schema = [
    # 1. Built-in tools
    {
        "type": "function",
        "name": "tool_multimedia_search",
        "description": "Searches the web for textual content, images, or videos. Returns a summary of text, or direct URLs to images and videos. Use this tool when the user asks for information, pictures, or video clips.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The target search query."
                },
                "search_type": {
                    "type": "string",
                    "enum": ["text", "image", "video"],
                    "description": "The type of media to search for. Choose 'text' for general info, 'image' for pictures, or 'video' for clips."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of items to return. Defaults to 5."
                }
            },
            "required": ["query", "search_type"]
        }
    },
    {
        "type": "function",
        "name": "memory_handler",
        "description": "A comprehensive tool to manage Master's long-term memory. Use this to search, save, update, or delete facts, preferences, background history, or project stacks. MUST use when you need to recall or store information across sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "save", "update", "delete"],
                    "description": "REQUIRED. The operation to perform. 'search' to find memories; 'save' to store a new fact; 'update' to modify an existing memory; 'delete' to remove a memory."
                },
                "query": {
                    "type": "string",
                    "description": "Required if action is 'search'. Dense keyword or key semantic phrase to look for (e.g., 'favorite music genre', 'Fairy project setup')."
                },
                "content": {
                    "type": "string",
                    "description": "Required if action is 'save' or 'update'. The fact or memory to store, MUST be written objectively in the third person (e.g., 'User's student ID is 202416916', 'User switched from C++ to Rust')."
                },
                "doc_id": {
                    "type": "string",
                    "description": "Required if action is 'update' or 'delete'. The exact unique ID of the memory, which MUST be obtained from a previous 'search' action."
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "personal_profile", 
                        "tech_and_projects", 
                        "hobbies_and_entertainment", 
                        "lifestyle_and_routine", 
                        "work_and_study", 
                        "relationships", 
                        "general"
                    ],
                    "description": "The domain of the memory. Used when saving, updating, or optionally filtering a search. Defaults to 'general'."
                },
                "importance": {
                    "type": "integer",
                    "description": "Required if action is 'save' or 'update'. Importance scale from 1 to 10. (1-3: trivial/temporary, 4-6: normal daily facts, 7-8: core habits/preferences, 9-10: crucial identity data/IDs)."
                },
                "user_relevant": {
                    "type": "boolean",
                    "description": "Required if action is 'save' or 'update'. Set to true if the memory is directly about the user's life, preferences, or profile. Set to false if it is general external knowledge."
                },
                "start_time": {
                    "type": "number",
                    "description": "Optional Unix timestamp. Used ONLY for 'search' to find memories mentioned after a specific time."
                },
                "end_time": {
                    "type": "number",
                    "description": "Optional Unix timestamp. Used ONLY for 'search' to find memories mentioned before a specific time."
                }
            },
            "required": ["action"]
        }
    },
    {
        "type": "function",
        "name": "forget_user_fact",
        "description": "Invoke ONLY when the user explicitly commands to forget, wipe, or remove a known fact.",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or keyword describing the memory to wipe."
                }
            },
            "required": ["topic"]
        }
    },
    {
        "type": "function",
        "name": "get_app_usage_context",
        "description": (
            "Retrieve desktop application usage logs and statistics from PostgreSQL. "
            "Use 'daily_summary' for aggregated app runtime/late-night stats today, "
            "or 'recent_sessions' for the chronological log of recently active windows."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "view_type": {
                    "type": "string",
                    "enum": ["daily_summary", "recent_sessions"],
                    "description": (
                        "Type of log to retrieve: 'daily_summary' for total time spent per app today, "
                        "or 'recent_sessions' for recent timeline sessions with timestamps."
                    ),
                    "default": "daily_summary"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records to fetch. Default is 10.",
                    "default": 10
                }
            },
            "required": ["view_type"]
        }
    },
    {
        "type": "function",
        "name": "get_system_telemetry",
        "description": (
            "Query Windows machine hardware specifications or real-time performance telemetry. "
            "Use 'live_metrics' for active CPU/RAM/GPU load, temperatures, VRAM, and thermal/load alerts. "
            "Use 'static_specs' for CPU model, total RAM capacity, GPU model, and OS build info."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "enum": ["live_metrics", "static_specs"],
                    "description": (
                        "'live_metrics': Real-time hardware utilization, temps, active window, and alerts. "
                        "'static_specs': Fixed machine specifications (CPU, total RAM, GPU model, OS)."
                    ),
                    "default": "live_metrics"
                }
            },
            "required": ["target"]
        }
    },
    {
        "type": "function",
        "name": "manage_schedule",
        "description": (
            "Manage reminders, timers, alarms, and schedule cancellations. "
            "Supports creating a new scheduled reminder ('set'), canceling active reminders ('cancel'), "
            "and querying pending schedules ('list')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["set", "cancel", "list"],
                    "description": "The scheduling action to perform: 'set' to create, 'cancel' to dismiss, or 'list' to review pending tasks."
                },
                "title": {
                    "type": "string",
                    "description": "Short headline or subject of the task (e.g., 'Check Blender render', 'Meeting with team', 'Drink water')."
                },
                "details": {
                    "type": "string",
                    "description": (
                                "Specific notes, context, or checklist provided by the user. "
                                "Leave as an empty string (\"\") if the user did not give any additional details or instructions. "
                                "DO NOT invent poetic descriptions, philosophical thoughts, or extra context."
                            )
                },
                "time_query": {
                    "type": "string",
                    "description": "Target schedule time (e.g., '15 minutes', '30m', '1 hour', '08:30', '19:45'). Required for action='set'."
                },
                "reminder_id": {
                    "type": "integer",
                    "description": "Specific numeric ID of the reminder to cancel (used with action='cancel')."
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword to match against reminder title or details when canceling without an ID."
                }
            },
            "required": ["action"]
        }
    },
    {
        "type": "function",
        "name": "execute_terminal_command",
        "description": (
            "Directly execute PowerShell terminal commands on Master's Windows machine to inspect the system, "
            "manage files, check network, query processes, or run automation scripts. "
            "Commands that require manual interactive keyboard inputs or are destructive to OS core files are strictly forbidden."
            "...manage files, inspect directory trees, read text/code document contents via Get-Content/cat, query processes..."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The exact PowerShell command to run (e.g., 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 5', 'dir', 'git status')."
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional directory path to execute the command in. Omit or leave null if executing from default location."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds before aborting (default is 15 seconds)."
                }
            },
            "required": ["command"]
        }
    },
    {
        "type": "function",
        "name": "manage_playback",
        "description": (
            "Control Fairy's audio and music playback engine. "
            "Allows searching and streaming songs via YouTube, queuing tracks, toggling playback "
            "(pause, resume, next, prev), adjusting volume and playback speed, managing favorites, "
            "and saving playlists."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "play",
                        "add_queue",
                        "pause",
                        "resume",
                        "next",
                        "prev",
                        "set_volume",
                        "set_speed",
                        "toggle_favorite",
                        "save_playlist",
                    ],
                    "description": (
                        "The specific playback operation to perform. "
                        "Use 'play' to find and play a new track immediately, "
                        "'add_queue' to append a song to the current playlist, "
                        "'pause', 'resume', 'next', 'prev' for player navigation, "
                        "'set_volume' or 'set_speed' to adjust audio output, "
                        "'toggle_favorite' to add/remove the current track from favorites, "
                        "or 'save_playlist' to persist the current queue."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Search keywords, song title, artist, or direct YouTube URL. "
                        "Required when action is 'play' or 'add_queue'. "
                        "Pass empty string '' for controls that don't need a search query."
                    ),
                },
                "value": {
                    "type": "number",
                    "description": (
                        "Numeric value for adjustments. "
                        "When action is 'set_volume': volume level from 0 to 100. "
                        "When action is 'set_speed': playback speed multiplier (e.g., 0.5, 1.0, 1.25, 1.5, 2.0). "
                        "Omit or set null for other actions."
                    ),
                },
                "playlist_name": {
                    "type": "string",
                    "description": (
                        "Name of the playlist when action is 'save_playlist'. "
                        "Defaults to empty string '' if not specified."
                    ),
                },
            },
            "required": ["action"],
        },
    },
]

advance_tool_schema = [
    {
    "type":"computer"
}
]

tool_registry = {
    "tool_multimedia_search": {"function": tool_multimedia_search, "reasoning_effort":"low"},

    "get_app_usage_context": {"function": app_tracker.get_app_usage_context, "reasoning_effort":"low"},

    "get_system_telemetry": {"function": system_tracker.get_system_telemetry, "reasoning_effort":"low"},

    "manage_schedule": {"function": manage_schedule, "reasoning_effort":"low"},

    "execute_terminal_command": {"function": execute_terminal_command, "reasoning_effort":"low"},

    "manage_playback": {"function": manage_playback, "reasoning_effort":"low"},
    "memory_handler": {"function": memory_handler, "reasoning_effort":"low"}
}
