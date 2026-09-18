import json
from extensions.app_tracking import app_tracker 
from extensions.system_tracking import system_tracker
from tools.get_dynamic_memories import get_dynamic_memories
from tools.launch_app import launch_application
from tools.control_system import control_system
from tools.manage_schedule import manage_schedule
from tools.execute_terminal import execute_terminal_command
from tools.close_app import close_application
from tools.music_tool import play_music
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
        "name": "get_recent_sessions_context",
        "description": (
            "Retrieve a chronological log of recent desktop application"
            " sessions, complete with exact start/end timestamps (HH:MM),"
            " active window titles, and categories. Useful for analyzing recent"
            " user activity sequences, verifying workflow focus, or"
            " identifying late-night computer usage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Number of recent application sessions to return."
                        " Defaults to 10."
                    ),
                    "default": 10,
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_daily_top_usage_context",
        "description": (
            "Query the PostgreSQL database for an aggregated summary of"
            " today's application usage. Returns total active duration"
            " (minutes), launch session counts, and late-night usage metrics"
            " (00:00–05:00) per software to assess overall productivity versus"
            " leisure time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of top-used applications to fetch."
                        " Defaults to 100."
                    ),
                    "default": 100,
                }
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "name": "get_live_metrics_summary",
        "description": (
            "Fetch real-time hardware telemetry and performance snapshots,"
            " including CPU/RAM/Disk utilization percentages, GPU temperature"
            " and load, VRAM allocation, battery status, and critical system"
            " alert flags (e.g., CPU > 85%, RAM > 90%, GPU overheating > 85°C)."
            " Use to detect system bottlenecks or thermal throttling."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "get_static_specs_summary",
        "description": (
            "Retrieve persistent machine hardware specifications, including"
            " the CPU model, total physical RAM capacity, GPU model, dedicated"
            " VRAM capacity, and Windows OS build version. Use to answer"
            " system configuration inquiries or assess compatibility for games,"
            " 3D rendering engines, and local AI model execution."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
    "type": "function",
    "name": "launch_application",
    "description": (
        "Launch an installed application, IDE, game, or tool on the computer based on its natural name "
        "or common alias (e.g., 'vscode', 'discord', 'maya', 'blender', 'chrome', 'unreal', 'genshin'). "
        "Automatically checks recent app history, Start Menu shortcuts, and Windows Registry."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "The common name or alias of the program to launch (e.g., 'vs code', 'maya', 'unreal engine', 'telegram')."
            }
        },
        "required": ["app_name"]
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
        "name": "close_application",
        "description": (
            "Terminate or gracefully close a currently running desktop application, IDE, game, "
            "or background process on Windows by its common name, alias, or executable filename "
            "(e.g., 'chrome', 'vscode', 'discord', 'maya', 'notepad', 'task manager'). "
            "Supports graceful termination and forced process killing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": (
                        "The common name, alias, or process executable name of the application to close "
                        "(e.g., 'vscode', 'google chrome', 'notepad', 'unreal')."
                    ),
                },
                "force": {
                    "type": "boolean",
                    "description": (
                        "Set to true to forcibly kill the process immediately (force quit), "
                        "or false for a graceful closure (allow app to save/exit cleanly). Defaults to false."
                    ),
                    "default": False,
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "type": "function",
        "name": "play_music",
        "description": (
            "Search and stream background music or songs requested by Master via YouTube. "
            "Extracts direct audio stream URL and cover thumbnail, or handles playback controls "
            "like pause, resume, and stop."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Song title, artist, genre, or mood keyword to search and stream "
                        "(e.g., 'Zenless Zone Zero OST', 'cyberpunk lofi', 'bài Cà phê Min'). "
                        "Required when action is 'play'."
                    ),
                }
            },
            "required": ["query"],
        },
    }
]

tool_registry = {
    "get_dynamic_memories": get_dynamic_memories,
    "get_recent_sessions_context": (
        app_tracker.get_recent_sessions_context
    ),
    "get_daily_top_usage_context": (
        app_tracker.get_daily_top_usage_context
    ),
    "get_live_metrics_summary": (
        system_tracker.get_live_metrics_summary
    ),
    "get_static_specs_summary": (
        system_tracker.get_static_specs_summary
    ),
    "launch_application":(launch_application),
    "control_system":(control_system),
    "manage_schedule":(manage_schedule),
    "execute_terminal_command":(execute_terminal_command),
    "close_application": (close_application),
    "play_music":(play_music)

}