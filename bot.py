import os
import asyncio
from collections import defaultdict

import discord
import requests

from personality import FELIX_PROMPT
from language import detect_language
from memory import load_memory, save_memory, get_profile

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MAX_HISTORY = 12  # tighter = more consistent personality
history = defaultdict(list)


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

USER PROFILE:
- Language: {language}
- Trust level: {profile.get("trust", 0)}
- Notes: {profile.get("notes", "")}

RULES:
- Reply in user's language
- Keep responses 1–3 sentences max
- Be natural like a Discord friend
- Never sound robotic or overly formal
"""

    messages = [{"role": "system", "content": system_prompt}]

    # add conversation history
    messages.extend(history[user_id])

    # add current user message
    messages.append({"role": "user", "content": user_text})

    return messages


# -------------------------
# GROQ CALL
# -------------------------

def ask_groq(messages):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": 120,
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


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

    profile = get_profile(user_id)

    # small controlled trust growth (prevents runaway inflation)
    profile["trust"] = min(profile.get("trust", 0) + 1, 100)

    user_text = message.content

    # store user message
    history[user_id].append({
        "role": "user",
        "content": user_text
    })

    trim_history(user_id)

    messages = build_messages(user_id, user_text)

    async with message.channel.typing():
        try:
            reply = await asyncio.to_thread(ask_groq, messages)

            history[user_id].append({
                "role": "assistant",
                "content": reply
            })

            trim_history(user_id)

            await message.channel.send(reply)

            save_memory()

        except Exception as e:
            print(e)
            await message.channel.send("something broke 😭")


client.run(TOKEN)