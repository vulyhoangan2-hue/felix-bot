import os
import asyncio
import time
from collections import defaultdict

import discord
import requests

from personality import FELIX_PROMPT
from language import detect_language
from memory import load_memory, save_memory, get_profile
from memory import memory  # IMPORTANT

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "llama-3.1-8b-instant"

MAX_HISTORY = 12
COOLDOWN_SECONDS = 4

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

history = defaultdict(list)
cooldowns = {}
global_lock = asyncio.Lock()


# -------------------------
# STYLE DETECTOR
# -------------------------

def detect_vn_style(text):
    text = text.lower()

    chill = ["vc", "vl", "haha", "kk", "gòi", "okie", "ừa", "ừ", "nè", "=))", "điên"]
    formal = ["xin lỗi", "tôi", "vui lòng", "có thể", "xin phép"]

    chill_score = sum(1 for w in chill if w in text)
    formal_score = sum(1 for w in formal if w in text)

    if chill_score >= 2:
        return "chill"
    if formal_score >= 2:
        return "formal"
    return "mix"


# -------------------------
# MESSAGE BUILDER
# -------------------------

def build_messages(user_id, user_text):
    profile = get_profile(user_id)
    language = detect_language(user_text)

    vn_style = profile.get("vn_style", "mix")
    slang_level = profile.get("slang_level", 1)

    style_map = {
        "chill": "Very casual Vietnamese Discord friend style.",
        "formal": "Polite and structured Vietnamese.",
        "mix": "Balanced casual-neutral Vietnamese.",
    }

    slang_map = {
        0: "No slang. Clean Vietnamese.",
        1: "Light slang allowed (okie, gòi, nè).",
        2: "Heavy Gen Z slang allowed (vc, vl, =)).",
    }

    system_prompt = f"""
{FELIX_PROMPT}

USER INFO:
- Language: {language}
- Trust: {profile.get("trust", 0)}

VIETNAMESE MODE:
- Style: {style_map[vn_style]}
- Slang: {slang_map[slang_level]}
- Mirror user tone naturally

RULES:
- Reply like a Discord friend
- 1–3 sentences max
- Never sound like a bot
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[user_id])
    messages.append({"role": "user", "content": user_text})

    return messages


# -------------------------
# GROQ CALL
# -------------------------

def ask_groq(messages, retries=3):
    for i in range(retries):
        try:
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
                time.sleep(2 ** i)
                continue

            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print("Groq error:", e)
            time.sleep(1)

    return "mình hơi lag xíu 😵 thử lại sau nha"


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
    # COOLDOWN
    # -------------------------
    if user_id in cooldowns:
        if now - cooldowns[user_id] < COOLDOWN_SECONDS:
            return

    cooldowns[user_id] = now

    profile = get_profile(user_id)

    # -------------------------
    # AUTO STYLE UPDATE
    # -------------------------
    detected = detect_vn_style(message.content)

    if profile["vn_style"] == "auto":
        profile["vn_style"] = detected
    else:
        if detected == "chill":
            profile["slang_level"] = min(profile.get("slang_level", 1) + 1, 2)
        elif detected == "formal":
            profile["slang_level"] = max(profile.get("slang_level", 1) - 1, 0)

    profile["trust"] = min(profile.get("trust", 0) + 1, 100)

    # -------------------------
    # HISTORY
    # -------------------------
    history[user_id].append({
        "role": "user",
        "content": message.content
    })

    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]

    messages = build_messages(user_id, message.content)

    # -------------------------
    # REQUEST
    # -------------------------
    async with message.channel.typing():
        async with global_lock:
            reply = await asyncio.to_thread(ask_groq, messages)

    history[user_id].append({
        "role": "assistant",
        "content": reply
    })

    if len(history[user_id]) > MAX_HISTORY:
        history[user_id] = history[user_id][-MAX_HISTORY:]

    await message.channel.send(reply)

    save_memory()


client.run(TOKEN)