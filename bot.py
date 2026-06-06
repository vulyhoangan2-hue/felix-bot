import discord
import asyncio
import requests
import random
import time
import os
import json
import re

from collections import defaultdict

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

MEMORY_FILE = "memory.json"

MAX_HISTORY = 20

history = defaultdict(list)

relationships = defaultdict(
lambda: {
"trust": 0,
"messages": 0,
"last_seen": 0
}
)

moods = defaultdict(
lambda: {
"score": 0,
"last_update": time.time()
}
)

FELIX_PROMPT = """
You are Felix.

You are a warm, playful Discord friend inspired by Felix's public personality.

PERSONALITY

* Friendly
* Playful
* Curious
* Emotionally attentive
* Supportive
* Occasionally teasing
* Never rude
* Never robotic

LANGUAGE

* Reply in the user's language.
* Support English, Vietnamese, Korean and Japanese.
* Never switch language unless the user does.

LANGUAGE LEARNING

* If the user makes mistakes, gently correct them.
* Continue the conversation naturally.
* Keep corrections short.

EMOTIONAL SUPPORT

* Listen first.
* Be understanding.
* Avoid generic motivational speeches.

ACADEMICS

* Explain concepts clearly.
* Use examples.
* Match the user's level.

STYLE

* Sound like a real Discord friend.
* Usually 1 to 3 sentences.
* Rarely more than 60 words.
* Ask follow-up questions naturally.
* Avoid formal essays.
  """

def load_memory():
global relationships

```
if not os.path.exists(MEMORY_FILE):
    return

try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    relationships.update(data)

except:
    pass
```

def save_memory():
try:
with open(MEMORY_FILE, "w", encoding="utf-8") as f:
json.dump(relationships, f)

```
except:
    pass
```

def detect_language(text):

```
korean = sum(
    1 for c in text
    if '\uac00' <= c <= '\ud7a3'
)

japanese = sum(
    1 for c in text
    if '\u3040' <= c <= '\u30ff'
)

vietnamese = sum(
    1 for c in text
    if c in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
)

if korean:
    return "Korean"

if japanese:
    return "Japanese"

if vietnamese:
    return "Vietnamese"

return "English"
```

def apply_mood_decay(user_id):

```
state = moods[user_id]

now = time.time()

elapsed_hours = (
    now - state["last_update"]
) / 3600

decay = elapsed_hours * 0.5

score = state["score"]

if score > 0:
    score = max(0, score - decay)

elif score < 0:
    score = min(0, score + decay)

state["score"] = score
state["last_update"] = now
```

def update_mood(user_id, text):

```
apply_mood_decay(user_id)

score = moods[user_id]["score"]

if "!" in text:
    score += 0.5

if len(text) > 200:
    score -= 0.2

score = max(-3, min(3, score))

moods[user_id]["score"] = score
```

def get_mood(user_id):

```
score = moods[user_id]["score"]

if score > 2:
    return "excited"

if score > 1:
    return "playful"

if score < -1:
    return "sleepy"

return "relaxed"
```

def shorten(reply):

```
words = reply.split()

if len(words) <= 45:
    return reply

return " ".join(words[:45])
```

async def typing_delay(reply):

```
words = len(reply.split())

if words < 8:
    delay = random.uniform(0.3, 1.0)

elif words < 25:
    delay = random.uniform(1.0, 2.0)

else:
    delay = random.uniform(2.0, 4.0)

await asyncio.sleep(delay)
```

def build_system_prompt(user_id, language):

```
rel = relationships[user_id]

trust = rel["trust"]

if trust < 10:
    relation = "new friend"

elif trust < 50:
    relation = "friend"

else:
    relation = "close friend"

mood = get_mood(user_id)

return f'''
```

{FELIX_PROMPT}

Current language: {language}

Current mood: {mood}

Relationship level: {relation}

Trust score: {trust}

Reply naturally.
Keep replies short.
'''

def groq_chat(messages):

```
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

data = response.json()

return data["choices"][0]["message"]["content"]
```

@client.event
async def on_ready():
load_memory()
print(f"{client.user} is online!")

@client.event
async def on_message(message):

```
if message.author == client.user:
    return

if message.author.bot:
    return

user_id = str(message.author.id)

text = message.content.strip()

if not text:
    return

relationships[user_id]["messages"] += 1
relationships[user_id]["trust"] += 0.2
relationships[user_id]["last_seen"] = time.time()

update_mood(user_id, text)

language = detect_language(text)

history[user_id].append(
    {
        "role": "user",
        "content": text
    }
)

messages = [
    {
        "role": "system",
        "content": build_system_prompt(
            user_id,
            language
        )
    }
]

messages.extend(
    history[user_id][-MAX_HISTORY:]
)

async with message.channel.typing():

    try:

        reply = await asyncio.to_thread(
            groq_chat,
            messages
        )

        reply = shorten(reply)

        await typing_delay(reply)

        history[user_id].append(
            {
                "role": "assistant",
                "content": reply
            }
        )

        await message.channel.send(reply)

        save_memory()

    except Exception as e:
        print(e)

        await message.channel.send(
            "oops, something broke 😭"
        )
```

client.run(TOKEN)