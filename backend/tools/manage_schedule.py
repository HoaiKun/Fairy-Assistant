import json
from extensions.reminder_manager import reminder_manager





def manage_schedule(
    action: str,
    title: str = "",
    time_query: str = "",
    details: str = "",
    reminder_id: int = None,
    keyword: str = ""
) -> str:
    """
    Manage reminders, timers, alarms, and schedule cancellations.
    """
    action = action.lower().strip()

    try:
        if action == "set":
            if not time_query:
                return json.dumps({
                    "status": "error",
                    "message": "Missing required time parameter (time_query)."
                })

            task_title = title.strip() if title.strip() else "Reminder"
            reminder = reminder_manager.add_reminder(
                title=task_title,
                time_query=time_query,
                details=details.strip()
            )
            remind_at_str = reminder["remind_at"].strftime("%Y-%m-%d %H:%M:%S")

            return json.dumps({
                "status": "success",
                "action": "set",
                "reminder_id": reminder["reminder_id"],
                "title": reminder["title"],
                "details": reminder["details"],
                "remind_at": remind_at_str,
                "message": f"Successfully scheduled '{reminder['title']}' for {remind_at_str}."
            })

        elif action == "cancel":
            target_kw = keyword or title
            canceled_items = reminder_manager.cancel_reminder(reminder_id=reminder_id, keyword=target_kw)

            if not canceled_items:
                target_desc = f"ID {reminder_id}" if reminder_id else (f"keyword '{target_kw}'" if target_kw else "most immediate")
                return json.dumps({
                    "status": "not_found",
                    "message": f"No pending reminders found matching {target_desc} to cancel."
                })

            details_list = [f"ID {x['reminder_id']}: '{x['title']}'" for x in canceled_items]
            return json.dumps({
                "status": "success",
                "action": "cancel",
                "canceled_count": len(canceled_items),
                "message": f"Successfully canceled reminders: {', '.join(details_list)}."
            })

        elif action == "list":
            items = reminder_manager.list_pending()
            if not items:
                return json.dumps({
                    "status": "success",
                    "action": "list",
                    "reminders": [],
                    "message": "There are no pending reminders currently active."
                })

            formatted = [
                {
                    "id": item["reminder_id"],
                    "title": item["title"],
                    "details": item["details"],
                    "remind_at": item["remind_at"].strftime("%Y-%m-%d %H:%M:%S")
                }
                for item in items
            ]
            return json.dumps({
                "status": "success",
                "action": "list",
                "reminders": formatted,
                "message": f"Found {len(formatted)} pending reminder(s)."
            })

        return json.dumps({
            "status": "unsupported",
            "message": f"Unsupported action '{action}'. Supported actions: 'set', 'cancel', 'list'."
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def RaiseReminder(item:dict):
    print(item)

reminder_manager.callback_func= RaiseReminder