import os
import asyncio
import time
from collections import defaultdict

import discord
import requests

from personality import FELIX_PROMPT
from language import detect_language, detect_mix
from memory import (
    load_memory, save_memory,
    get_profile, update_display_name,
    get_memory_context_block,
)
from intent import detect_intent
from emotion import detect_emotion
from planner import build_plan, plan_to_hint
from vn_normalizer import normalize

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
TOKEN        = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL        = "llama-3.3-70b-versatile"   # upgraded from 8b
MAX_HISTORY  = 40                           # shared group history
COOLDOWN     = 3                            # seconds between responses per user
CHANNEL_NAME = "chat-with-felix"

# ─────────────────────────────────────────
# Discord setup
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ─────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────
channel_history: list[dict] = []   # SHARED across ALL users — the group chat log
cooldowns: dict[str, float] = {}
global_lock = asyncio.Lock()


# ─────────────────────────────────────────
# Groq API call
# ─────────────────────────────────────────
def ask_groq(messages: list[dict]) -> str:
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
                "temperature": 0.82,    # slightly higher = more natural/varied
                "max_tokens": 300,
                "top_p": 0.95,
            },
            timeout=30,
        )
        if res.status_code == 429:
            return "ahhh wait slow down a sec 😭"
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "omg sorry lagged out for a sec, what were you saying"
    except Exception as e:
        print(f"[Groq error] {e}")
        return "wait something went wrong on my end lol"


# ─────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────
def build_messages(
    display_name: str,
    user_id: str,
    raw_text: str,
    clean_text: str,
    intent: str,
    emotion: str,
    plan: dict,
) -> list[dict]:
    profile = get_profile(user_id)
    language = detect_language(raw_text)
    languages_present = detect_mix(raw_text)
    hint = plan_to_hint(plan)

    # Memory context — what Felix remembers about the group
    memory_block = get_memory_context_block()

    # Build a compact user notes block
    user_notes = profile.get("notes", [])
    user_notes_block = ""
    if user_notes:
        user_notes_block = f"\nWhat Felix remembers about {display_name}: {'; '.join(user_notes)}"

    system = f"""{FELIX_PROMPT}

═══════════════════════════════════════
CURRENT CONVERSATION CONTEXT
═══════════════════════════════════════
This is a GROUP CHAT. Each message is tagged [Name]: so you know who said what.
The person talking to you RIGHT NOW: [{display_name}]
Their detected language: {language}
Languages mixed in their message: {', '.join(languages_present)}
Their trust level with you: {profile['trust']}/100

DETECTED STATE:
- Intent: {intent}
- Emotion: {emotion}
- Response hint: {hint}
{user_notes_block}

{memory_block}

REMINDER:
- You are Felix. Not an AI. Not a bot. Just Felix, in a group chat.
- Reply ONLY in the language(s) [{display_name}] used. If they mixed languages, you can mix back.
- Keep it short unless the situation calls for more.
- Read the room. Check the full chat history above before replying.
"""

    msgs = [{"role": "system", "content": system}]
    msgs.extend(channel_history)
    # Note: the current message is already appended to channel_history before this call,
    # so it's already the last item — don't append it again.
    return msgs


# ─────────────────────────────────────────
# Append to shared history
# ─────────────────────────────────────────
def push_to_history(role: str, content: str):
    global channel_history
    channel_history.append({"role": role, "content": content})
    # Trim to window
    if len(channel_history) > MAX_HISTORY:
        channel_history = channel_history[-MAX_HISTORY:]


# ─────────────────────────────────────────
# Bot events
# ─────────────────────────────────────────
@client.event
async def on_ready():
    load_memory()
    print(f"✅ {client.user} is online!")


@client.event
async def on_message(message: discord.Message):
    # Ignore bots
    if message.author.bot:
        return

    # Only respond in the right channel OR when mentioned
    in_felix_channel = message.channel.name == CHANNEL_NAME
    was_mentioned    = client.user in message.mentions

    if not (in_felix_channel or was_mentioned):
        return

    user_id      = str(message.author.id)
    display_name = message.author.display_name
    now          = time.time()

    # Update stored display name
    update_display_name(user_id, display_name)

    # ── Cooldown check ────────────────────────
    # We still log the message to history even if on cooldown,
    # so Felix sees the full conversation flow.
    raw_text   = message.content
    clean_text = normalize(raw_text)

    # Tag the message with the sender's name for group context
    tagged_content = f"[{display_name}]: {clean_text}"
    push_to_history("user", tagged_content)

    # Cooldown: don't REPLY too fast, but still log above
    if user_id in cooldowns and now - cooldowns[user_id] < COOLDOWN:
        return

    # Only actually reply if Felix was addressed (mentioned or in Felix's channel)
    # In the Felix channel, he replies to everything.
    # If mentioned in another channel, he replies there too.
    cooldowns[user_id] = now

    # ── Profile update ────────────────────────
    profile = get_profile(user_id)
    profile["trust"] = min(profile["trust"] + 1, 100)

    # ── Analysis ──────────────────────────────
    intent  = detect_intent(raw_text)
    emotion = detect_emotion(raw_text)
    plan    = build_plan(intent, emotion, profile)

    # ── Build prompt ──────────────────────────
    messages = build_messages(
        display_name,
        user_id,
        raw_text,
        clean_text,
        intent,
        emotion,
        plan,
    )

    # ── Call Groq ─────────────────────────────
    async with message.channel.typing():
        async with global_lock:
            reply = await asyncio.to_thread(ask_groq, messages)

    # ── Log Felix's reply to shared history ───
    push_to_history("assistant", reply)

    # ── Send ──────────────────────────────────
    import re
    reply = re.sub(r"^\[.*?\]\s*:\s*", "", reply).strip()

    await message.channel.send(reply)

    # ── Save memory periodically ──────────────
    save_memory()


# ─────────────────────────────────────────
# Run
# ─────────────────────────────────────────
client.run(TOKEN)