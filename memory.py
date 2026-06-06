import json
import os

MEMORY_FILE = "memory.json"

memory = {}


def load_memory():
    global memory
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memory = json.load(f)
    else:
        memory = {}


def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def get_profile(user_id):
    if user_id not in memory:
        memory[user_id] = {
            "trust": 0,
            "notes": [],
            "vn_style": "auto",   # auto | chill | formal | mix
            "slang_level": 1,     # 0 = formal, 1 = normal, 2 = heavy slang
        }
    return memory[user_id]