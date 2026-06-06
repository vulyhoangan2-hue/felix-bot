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

MAX_HISTORY = 15
history = defaultdict(list)


def build_prompt(user_id, text):
    profile = get_profile(user_id)

    language = detect_language(text)

    return f"""
{FELIX_PROMPT}

Current language: {language}

Trust level: {profile['trust']}

Known notes:
{profile['notes']}

IMPORTANT:
- Reply in the user's language.
- Keep replies short.
- Usually 1-3 sentences.
- Sound like a real Discord friend.
"""


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
            "temperature": 0.9,
            "max_tokens": 150,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


@client.event
async def on_ready():
    load_memory()
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

    user_id = str(message.author.id)

    profile = get_profile(user_id)
    profile["trust"] += 1

    history[user_id].append(
        {
            "role": "user",
            "content": message.content,
        }
    )

    messages = [
        {
            "role": "system",
            "content": build_prompt(
                user_id,
                message.content,
            ),
        }
    ]

    messages.extend(
        history[user_id][-MAX_HISTORY:]
    )

    async with message.channel.typing():
        try:
            reply = await asyncio.to_thread(
                ask_groq,
                messages,
            )

            history[user_id].append(
                {
                    "role": "assistant",
                    "content": reply,
                }
            )

            await message.channel.send(reply)

            save_memory()

        except Exception as e:
            print(e)

            await message.channel.send(
                "something broke 😭"
            )


client.run(TOKEN)