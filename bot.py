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

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load memory from JSON file
def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    else:
        return {}

# Save memory to JSON file
def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

# Get user profile
def get_profile(user_id, memory):
    if str(user_id) not in memory:
        memory[str(user_id)] = {
            "trust": 0,
            "notes": "",
            "history": []  # conversation history
        }
    return memory[str(user_id)]

# Build prompt with recent conversation history
def build_prompt(user_id, message_content, memory):
    profile = get_profile(user_id, memory)
    language = detect_language(message_content)
    # Limit history to last 5 exchanges
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

Reply naturally.
Keep replies short.
"""

# Ask GROQ API
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
            "temperature": 0.9,
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

    # Append user message to history
    profile["history"].append({"role": "user", "content": message.content})

    # Build prompt with history
    prompt = build_prompt(user_id, message.content, memory)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message.content}
    ]

    try:
        reply = await asyncio.to_thread(ask_groq, messages)
        await message.channel.send(reply)
        # Append assistant reply to history
        profile["history"].append({"role": "assistant", "content": reply})

        # Save memory after each interaction
        save_memory(memory)

    except Exception as e:
        print(e)
        await message.channel.send("Something broke 😭")

# Run the bot
client.run(TOKEN)