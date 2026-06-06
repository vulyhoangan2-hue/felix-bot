import json
import os

MEMORY_FILE = "memory.json"

profiles = {}


def load_memory():

    global profiles

    if not os.path.exists(MEMORY_FILE):
        return

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            profiles = json.load(f)

    except Exception:
        profiles = {}


def save_memory():

    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(
                profiles,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception as e:
        print(e)


def get_profile(user_id):

    user_id = str(user_id)

    if user_id not in profiles:

        profiles[user_id] = {
            "trust": 0,
            "favorite_things": [],
            "language_goal": "",
            "notes": []
        }

    return profiles[user_id]


def add_note(user_id, note):

    profile = get_profile(user_id)

    if note not in profile["notes"]:
        profile["notes"].append(note)

    save_memory()