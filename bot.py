import os
import discord
import requests
import asyncio

from personality import FELIX_PROMPT
from language import detect_language
from memory import (
    load_memory,
    save_memory,
    get_profile
)

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


def build_prompt(user_id, message):

    profile = get_profile(user_id)

    language = detect_language(message)

    return f"""
{FELIX_PROMPT}

Current language: {language}

Trust level: {profile['trust']}

Known notes:
{profile['notes']}

Reply naturally.
Keep replies short.
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
            "temperature": 0.9,
            "max_tokens": 120
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


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

    profile = get_profile(message.author.id)

    profile["trust"] += 1

    messages = [
        {
            "role": "system",
            "content": build_prompt(
                message.author.id,
                message.content
            )
        },
        {
            "role": "user",
            "content": message.content
        }
    ]

    async with message.channel.typing():

        try:

            reply = await asyncio.to_thread(
                ask_groq,
                messages
            )

            await message.channel.send(reply)

            save_memory()

        except Exception as e:

            print(e)

            await message.channel.send(
                "something broke 😭"
            )


client.run(TOKEN)