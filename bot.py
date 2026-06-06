import os
import asyncio
import time
from collections import defaultdict

import discord
import requests

from personality import FELIX_PROMPT
from language import detect_language
from memory import load_memory, save_memory, get_profile

# -------------------------
# CONFIG
# -------------------------

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "llama-3.1-8b-instant"  # faster + fewer 429 errors

MAX_HISTORY = 12
COOLDOWN_SECONDS = 5

# -------------------------
# DISCORD SETUP
# -------------------------

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

history = defaultdict(list)
cooldowns = {}
global_lock = asyncio.Lock()


# -------------------------
# MEMORY HELPERS
# -------------------------

def trim_history(user_id):
    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]


def build_messages(user_id, user_text):
    profile = get_profile(user_id)
    language = detect_language(user_text)

    system_prompt = f"""
{FELIX_PROMPT}

USER INFO:
- Language: {language}
- Trust level: {profile.get("trust", 0)}
- Notes: {profile.get("notes", "")}

RULES:
- Reply like a Discord friend
- Keep it 1–3 sentences
- Be natural, not robotic
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[user_id])
    messages.append({"role": "user", "content": user_text})

    return messages


# -------------------------
# GROQ CALL (SAFE + RETRY)
# -------------------------

def ask_groq(messages, retries=3):
    for i in range(retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": 0.85,
                    "max_tokens": 120,
                },
                timeout=30,
            )

            # Handle rate limit
            if response.status_code == 429:
                time.sleep(2 ** i)
                continue

            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"[Groq Error Attempt {i+1}]:", e)
            time.sleep(1)

    return "I'm a bit busy right now 😵 try again in a moment."


# -------------------------
# EVENTS
# -------------------------

@client.event
async def on_ready():
    load_memory()
    print(f"{client.user} is online!")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    should_reply = (
        message.channel.name == "chat-with-felix"
        or client.user in message.mentions
    )

    if not should_reply:
        return

    user_id = str(message.author.id)
    now = time.time()

    # -------------------------
    # COOLDOWN (ANTI-SPAM)
    # -------------------------
    if user_id in cooldowns:
        if now - cooldowns[user_id] < COOLDOWN_SECONDS:
            return

    cooldowns[user_id] = now

    profile = get_profile(user_id)
    profile["trust"] = min(profile.get("trust", 0) + 1, 100)

    user_text = message.content

    # -------------------------
    # STORE USER MESSAGE
    # -------------------------
    history[user_id].append({
        "role": "user",
        "content": user_text
    })

    trim_history(user_id)

    messages = build_messages(user_id, user_text)

    # -------------------------
    # GLOBAL LOCK (PREVENT BURSTS)
    # -------------------------
    async with message.channel.typing():
        async with global_lock:
            reply = await asyncio.to_thread(ask_groq, messages)

    # -------------------------
    # STORE ASSISTANT MESSAGE
    # -------------------------
    history[user_id].append({
        "role": "assistant",
        "content": reply
    })

    trim_history(user_id)

    await message.channel.send(reply)

    save_memory()


client.run(TOKEN)