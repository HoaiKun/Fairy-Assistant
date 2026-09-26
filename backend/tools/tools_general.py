import json
from extensions.app_tracking import app_tracker 
from extensions.system_tracking import system_tracker
from tools.control_system import control_system
from tools.manage_schedule import manage_schedule
from tools.execute_terminal import execute_terminal_command
from tools.manage_app import manage_application
from tools.music_tool import manage_playback
from Database.ChromaDB.ChromaDB_Handler import handle_general_memory
tools_schema = [
    # 1. Built-in tools
    {"type": "web_search_preview"},
    # 2. Custom tools (Flattened for Responses API)

    {
        "type": "function",
        "name": "get_dynamic_memories",
        "description": (
            "Retrieve relevant long-term memories, user background facts, or"
            " contextual profile information based on a semantic search query."
            " Incorporate multi-turn conversational context rather than just"
            " individual keywords."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": (
                        "A natural language semantic query representing the"
                        " target memory (e.g., 'class schedule', 'sleep"
                        " habits', 'ongoing projects', 'workout routine')."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of relevant memory entries to retrieve."
                        " Defaults to 5."
                    ),
                    "default": 5,
                },
            },
            "required": ["search_query"],
        },
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
        "name": "control_system",
        "description": (
            "Execute Windows system controls and timed power actions. "
            "Supports scheduling shutdown or restart (e.g., 'in 30 minutes', '1 hour'), "
            "canceling scheduled shutdowns, locking workstation, sleeping, and volume controls."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "shutdown",
                        "restart",
                        "cancel_shutdown",
                        "lock",
                        "sleep",
                        "volume_up",
                        "volume_down",
                        "mute_toggle",
                    ],
                    "description": "The system operation to perform.",
                },
                "value": {
                    "type": "string",
                    "description": (
                        "Optional duration for shutdown/restart (e.g., '30m', '1"
                        " tiếng', '45 phút', '3600') or number of volume steps"
                        " (e.g., '5', '10')."
                    ),
                },
            },
            "required": ["action"],
        },
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
    {
        "type": "function",
        "name": "handle_general_memory",
        "description": (
            "Manage Master's long-term memory profile. "
            "Silently use this to 'add' new personal facts, 'update' existing facts when habits change, or 'delete' incorrect memories. "
            "Always write facts in third-person (e.g., 'Master loves React')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "delete"],
                    "description": "The memory operation to perform."
                },
                "doc_id": {
                    "type": "string",
                    "description": "The unique ID of the memory. Required ONLY for 'update' and 'delete'. Must be extracted from System Prompt context."
                },
                "content": {
                    "type": "string",
                    "description": "The fact text written in third-person. Required ONLY for 'add' and 'update'."
                },
                "category": {
                    "type": "string",
                    "description": "Category of the memory (e.g., 'general', 'music', 'work'). Optional, defaults to 'general'. Used only for 'add'."
                }
            },
            "required": ["action"]
        }
    }
]

tool_registry = {

    "get_app_usage_context": app_tracker.get_app_usage_context,

    "get_system_telemetry": system_tracker.get_system_telemetry,

    "manage_application": manage_application,

    "control_system":(control_system),

    "manage_schedule":(manage_schedule),

    "execute_terminal_command":(execute_terminal_command),

    "manage_playback":(manage_playback),
    "handle_general_memory": (handle_general_memory)
    

}