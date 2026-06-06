import os
import asyncio
import time
from collections import defaultdict

import discord
import requests

from personality import FELIX_PROMPT
from language import detect_language
from memory import load_memory, save_memory, get_profile

from intent import detect_intent
from emotion import detect_emotion
from planner import build_plan
from vn_normalizer import normalize

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "llama-3.1-8b-instant"

MAX_HISTORY = 12
COOLDOWN = 4

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

history = defaultdict(list)
cooldowns = {}
global_lock = asyncio.Lock()


# -------------------------
# GROQ
# -------------------------

def ask_groq(messages):
    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 120,
        },
        timeout=30,
    )

    if res.status_code == 429:
        return "slow down a bit 😭"

    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]


# -------------------------
# PROMPT BUILDER
# -------------------------

def build_messages(user_id, raw_text, clean_text, intent, emotion, plan):
    profile = get_profile(user_id)
    language = detect_language(raw_text)

    system = f"""
{FELIX_PROMPT}

STATE:
- Intent: {intent}
- Emotion: {emotion}
- Tone: {plan['tone']}
- Slang: {plan['slang']}
- Emoji level: {plan['emoji']}

USER:
- Language: {language}
- Trust: {profile['trust']}

RULES:
- 1–3 sentences
- Natural Discord friend tone
- Never sound like AI
"""

    msgs = [{"role": "system", "content": system}]
    msgs.extend(history[user_id])
    msgs.append({"role": "user", "content": clean_text})

    return msgs


# -------------------------
# BOT EVENTS
# -------------------------

@client.event
async def on_ready():
    load_memory()
    print(f"{client.user} is online!")


@client.event
async def on_message(message):
    if message.author.bot:
        return

    if not (
        message.channel.name == "chat-with-felix"
        or client.user in message.mentions
    ):
        return

    user_id = str(message.author.id)
    now = time.time()

    if user_id in cooldowns and now - cooldowns[user_id] < COOLDOWN:
        return

    cooldowns[user_id] = now

    profile = get_profile(user_id)

    raw_text = message.content
    clean_text = normalize(raw_text)

    intent = detect_intent(raw_text)
    emotion = detect_emotion(raw_text)
    plan = build_plan(intent, emotion, profile)

    profile["trust"] = min(profile["trust"] + 1, 100)

    history[user_id].append({"role": "user", "content": clean_text})
    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]

    messages = build_messages(
        user_id,
        raw_text,
        clean_text,
        intent,
        emotion,
        plan
    )

    async with message.channel.typing():
        async with global_lock:
            reply = await asyncio.to_thread(ask_groq, messages)

    history[user_id].append({"role": "assistant", "content": reply})

    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]

    await message.channel.send(reply)

    save_memory()


client.run(TOKEN)