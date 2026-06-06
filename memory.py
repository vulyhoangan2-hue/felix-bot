"""
memory.py — persistent memory for Felix bot.

Stores:
  - Per-user profiles (name, trust, language preference, notes)
  - Shared group facts (things Felix learned about members from group chat)
"""

import json
import os

MEM_FILE = "memory.json"
memory: dict = {}


# ─────────────────────────────────────────
# Load / Save
# ─────────────────────────────────────────

def load_memory():
    global memory
    if os.path.exists(MEM_FILE):
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            try:
                memory = json.load(f)
            except json.JSONDecodeError:
                memory = {}
    else:
        memory = {}

    # Ensure top-level keys exist
    if "users" not in memory:
        memory["users"] = {}
    if "group_facts" not in memory:
        memory["group_facts"] = []


def save_memory():
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# Per-user profile
# ─────────────────────────────────────────

def get_profile(user_id: str) -> dict:
    """
    Returns the profile dict for a user, creating a default if absent.
    Fields:
      - trust: 0–100, increases with interaction
      - display_name: last known Discord display name
      - preferred_language: override for language detection
      - notes: list of short remembered facts about this user
      - slang_level: 0 (formal) to 3 (heavy slang), auto-adjusted
      - vibe: "warm" | "playful" | "quiet" — Felix's read on this person
    """
    users = memory.setdefault("users", {})
    if user_id not in users:
        users[user_id] = {
            "trust": 0,
            "display_name": "",
            "preferred_language": None,
            "notes": [],
            "slang_level": 1,
            "vibe": "warm",
        }
    return users[user_id]


def update_display_name(user_id: str, name: str):
    profile = get_profile(user_id)
    profile["display_name"] = name


def add_user_note(user_id: str, note: str):
    """Add a remembered fact about a specific user. Keeps last 10."""
    profile = get_profile(user_id)
    notes: list = profile.setdefault("notes", [])
    if note not in notes:
        notes.append(note)
    if len(notes) > 10:
        profile["notes"] = notes[-10:]


def get_user_notes(user_id: str) -> list[str]:
    return get_profile(user_id).get("notes", [])


# ─────────────────────────────────────────
# Group-level shared facts
# ─────────────────────────────────────────

def add_group_fact(fact: str):
    """
    Store something Felix learned about a member from the group chat.
    e.g. "Iris said her favourite food is ramen"
    Keeps last 30 facts.
    """
    facts: list = memory.setdefault("group_facts", [])
    if fact not in facts:
        facts.append(fact)
    if len(facts) > 30:
        memory["group_facts"] = facts[-30:]


def get_group_facts() -> list[str]:
    return memory.get("group_facts", [])


def get_memory_context_block() -> str:
    """
    Returns a formatted string summarising what Felix remembers about
    everyone in the group — injected into the system prompt.
    """
    facts = get_group_facts()
    if not facts:
        return ""

    lines = ["WHAT FELIX REMEMBERS ABOUT THIS GROUP:"]
    for f in facts:
        lines.append(f"  - {f}")
    return "\n".join(lines)