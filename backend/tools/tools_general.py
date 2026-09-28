import json
from extensions.app_tracking import app_tracker 
from extensions.system_tracking import system_tracker
from tools.manage_schedule import manage_schedule
from tools.execute_terminal import execute_terminal_command
from tools.music_tool import manage_playback
from Database.ChromaDB.ChromaDB_Handler import get_long_term_memories
tools_schema = [
    # 1. Built-in tools
    {"type": "web_search_preview"},
    {
        "type": "function",
        "name": "get_long_term_memories",
        "description": (
            "Retrieve Master's long-term facts, preferences, background history"
            "or project stacks from ChromaDB. Use focused search terms without conversational fluff."
            "Must use when missing or forgetting facts about user/master"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Dense keyword or key semantic phrase (e.g., 'favorite music genre', 'RTX graphics card')."
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "tech", "work", "personal", "gaming", "music"],
                    "description": "Optional domain filter. Defaults to 'all'."
                },
                "limit": {
                    "type": "integer",
                    "description": "Max entries to return. Defaults to 5."
                }
            },
            "required": ["search_query"]
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

    "get_app_usage_context": app_tracker.get_app_usage_context,

    "get_system_telemetry": system_tracker.get_system_telemetry,

    "manage_schedule":(manage_schedule),

    "execute_terminal_command":(execute_terminal_command),

    "manage_playback":(manage_playback),
    "get_long_term_memories": (get_long_term_memories)
    

}