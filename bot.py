import os
import discord
import requests
import asyncio
import json
from pathlib import Path

from personality import FELIX_PROMPT
from language import detect_language
from memory import (
    load_memory,
    save_memory,
    get_profile
)

MEMORY_FILE = Path("memory.json")

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = discord.Client(intents=discord.Intents.default())
client.intents.message_content = True

def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

def get_profile(user_id, memory):
    if str(user_id) not in memory:
        memory[str(user_id)] = {
            "trust": 0,
            "notes": "",
            "history": []
        }
    return memory[str(user_id)]

def build_prompt(user_id, message_content, memory):
    profile = get_profile(user_id, memory)
    language = detect_language(message_content)
    recent_history = profile.get("history", [])[-5:]
    history_text = ""
    for msg in recent_history:
        role = "User" if msg['role'] == 'user' else 'Felix'
        history_text += f"{role}: {msg['content']}\n"

    return f"""
{FELIX_PROMPT}

Current language: {language}

Trust level: {profile['trust']}

Known notes:
{profile['notes']}

Conversation history:
{history_text}

IMPORTANT:
- Reply in the user's language.
- Keep replies short.
- Usually 1-3 sentences.
- Sound like a real online friend.
"""

def ask_groq(messages):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 120
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

@client.event
async def on_ready():
    global memory
    memory = load_memory()
    print(f"{client.user} is online!")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    should_reply = False

    if message.channel.name == "chat-with-felix":
        should_reply = True

    if client.user in message.mentions:
        should_reply = True

    if not should_reply:
        return

    user_id = message.author.id
    profile = get_profile(user_id, memory)
    profile["trust"] += 1
    profile["history"].append({"role": "user", "content": message.content})

    prompt = build_prompt(user_id, message.content, memory)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message.content}
    ]

    try:
        reply = await asyncio.to_thread(ask_groq, messages)
        await message.channel.send(reply)
        profile["history"].append({"role": "assistant", "content": reply})
        save_memory(memory)
    except Exception as e:
        print(e)
        await message.channel.send("Something broke 😭")

client.run(TOKEN)