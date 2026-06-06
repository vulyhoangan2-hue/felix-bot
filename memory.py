import json
import os

MEM_FILE = "memory.json"
memory = {}


def load_memory():
    global memory
    if os.path.exists(MEM_FILE):
        with open(MEM_FILE, "r", encoding="utf-8") as f:
            memory = json.load(f)
    else:
        memory = {}


def save_memory():
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def get_profile(user_id):
    if user_id not in memory:
        memory[user_id] = {
            "trust": 0,
            "vn_style": "auto",
            "slang_level": 1,
            "notes": []
        }
    return memory[user_id]