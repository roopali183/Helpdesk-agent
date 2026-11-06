import itertools

from kb import search_kb

# Demo mode: any user ID you type is treated as a real (locked) mock employee.
# Set to False to make unknown IDs return "user not found" again.
DEMO_AUTO_CREATE_USERS = True

USERS = {
    "u101": {"name": "Asha", "locked": True, "dept": "Finance"},
    "u102": {"name": "Ravi", "locked": False, "dept": "Engineering"},
}

# Gives each escalation its own number: ESC-1001, ESC-1002, ...
_escalation_counter = itertools.count(1001)


def _find_user(user_id: str):
    """Return the user record, creating a mock one in demo mode."""
    user_id = str(user_id).strip().lower()
    if not user_id:
        return None, user_id
    if user_id not in USERS and DEMO_AUTO_CREATE_USERS:
        USERS[user_id] = {
            "name": f"Employee {user_id}",
            "locked": True,
            "dept": "Unknown",
        }
    return USERS.get(user_id), user_id


def get_user_status(user_id: str) -> dict:
    """Look up an employee account."""
    user, _ = _find_user(user_id)
    return user if user else {"error": "user not found"}


def unlock_account(user_id: str) -> dict:
    """Unlock a locked account."""
    user, uid = _find_user(user_id)
    if not user:
        return {"error": "user not found"}
    if not user["locked"]:
        return {"success": True, "message": f"{uid} was already unlocked"}
    user["locked"] = False
    return {"success": True, "message": f"{uid} unlocked"}


def create_escalation(summary: str, priority: str) -> dict:
    """Hand the ticket to a human engineer."""
    return {
        "ticket_id": f"ESC-{next(_escalation_counter)}",
        "summary": summary,
        "priority": priority,
    }


TOOL_FUNCTIONS = {
    "get_user_status": get_user_status,
    "unlock_account": unlock_account,
    "create_escalation": create_escalation,
    "search_kb": search_kb,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_status",
            "description": "Look up an employee account by user ID. Shows whether it is locked.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unlock_account",
            "description": "Unlock a locked employee account by user ID.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_escalation",
            "description": "Escalate the ticket to a human engineer when you cannot solve it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["summary", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "Search the IT knowledge base for help articles (VPN, password policy, software requests). Use this for any how-to or policy question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short search phrase, e.g. 'VPN setup'",
                    }
                },
                "required": ["query"],
            },
        },
    },
]