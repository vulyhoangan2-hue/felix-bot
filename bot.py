import discord
import asyncio
import random
import time
import os
import requests

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ============================================
# CONFIG - Put your token here
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# ============================================
# DATA STORAGE
# ============================================

MAX_HISTORY = 12
MAX_MEMORY = 15

class UserProfile:
    def __init__(self):
        self.history = []
        self.mood_score = 0.0
        self.mood_last = time.time()
        self.facts = []
        self.message_count = 0
        self.trust = 0
        self.topics = defaultdict(int)
        self.language = "English"
        self.style = {"length": "short", "formality": "casual", "emoji": False}
        self.first_seen = time.time()
        self.nickname = None

user_db = {}
channel_chats = defaultdict(list)

# ============================================
# LANGUAGE DETECTION
# ============================================

def detect_lang(text):
    if re.search(r'[àáạảãâầấậẩẫăằắặẳẵđèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ]', text):
        return "Vietnamese"
    if re.search(r'[\uac00-\ud7af]', text):
        return "Korean"
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "Japanese"
    return "English"

# ============================================
# MOOD SYSTEM
# ============================================

def decay_mood(score, last_time):
    elapsed = (time.time() - last_time) / 60
    if score > 0:
        return max(0, score - elapsed / 3)
    elif score < 0:
        return min(0, score + elapsed / 3)
    return score

def mood_name(score):
    if score <= -3: return "upset"
    if score <= -1.5: return "tired"
    if score >= 2.5: return "excited"
    if score >= 1: return "happy"
    return "chill"

def update_mood(user_id, text, profile):
    now = time.time()
    profile.mood_score = decay_mood(profile.mood_score, profile.mood_last)
    profile.mood_last = now
    
    change = 0
    
    # Positive signals
    if any(w in text.lower() for w in ["thank", "thanks", "love", "nice", "good", "great", "awesome", "cute", "sweet"]):
        change += 1.2
    if any(w in text.lower() for w in ["yo", "hey", "hi", "hello", "sup", "what's up"]):
        change += 0.5
    
    # Negative signals
    if any(w in text.lower() for w in ["hate", "stupid", "dumb", "shut up", "annoying", "bad", "worst"]):
        change -= 1.5
    if len(text) > 250:
        change -= 0.8
    if text.count("?") >= 3:
        change -= 0.5
    
    # Spam check
    if len(profile.history) >= 2:
        t1 = profile.history[-1].get("time", now)
        t2 = profile.history[-2].get("time", now - 60)
        if t1 - t2 < 2:
            change -= 1.0
    
    profile.mood_score = max(-4, min(4, profile.mood_score + change))
    return mood_name(profile.mood_score), profile.mood_score

# ============================================
# MEMORY EXTRACTION
# ============================================

def extract_facts(text):
    facts = []
    patterns = [
        (r'my name is (\w+)', "name"),
        (r'call me (\w+)', "name"),
        (r'i(?:\'m| am) (\w+)(?:\s|$)', "name"),
        (r'i (?:like|love|enjoy|hate|prefer) (.+?)(?:\.|$|,)', "pref"),
        (r'my favorite (.+?) is (.+?)(?:\.|$|,)', "pref"),
        (r'i(?:\'m| am) (?:a|an) (.+?)(?:\.|$|,)', "info"),
        (r'i live in (.+?)(?:\.|$|,)', "info"),
        (r'i work as (.+?)(?:\.|$|,)', "info"),
    ]
    for pattern, ftype in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            facts.append(f"{ftype}:{m.group(0)}")
    return facts

def update_memory(user_id, message, profile):
    profile.message_count += 1
    
    # Extract facts
    new_facts = extract_facts(message.content)
    for f in new_facts:
        if f not in profile.facts:
            profile.facts.append(f)
            if len(profile.facts) > MAX_MEMORY:
                profile.facts.pop(0)
    
    # Topics
    words = re.findall(r'\b\w{4,}\b', message.content.lower())
    stop = {"this", "that", "with", "have", "from", "they", "will", "would", "there", "their", "what", "said", "each", "which", "however", "because", "about", "could", "other", "after", "first", "never", "these", "think", "where", "being", "every", "great", "might", "shall", "while", "those", "both", "than", "them", "then", "well", "also", "back", "just", "only", "over", "know", "take", "year", "good", "some", "come", "make", "well", "like", "time", "very", "when", "much", "want", "here", "look", "down", "most", "long", "find", "give", "does", "made", "part", "such", "even", "more", "must", "before", "should", "through", "during", "without", "against", "among", "within", "along", "above", "below", "under", "around", "between"}
    for w in words:
        if w not in stop:
            profile.topics[w] += 1
    
    # Trust
    if profile.message_count > 8:
        profile.trust = min(10, profile.trust + 0.15)

# ============================================
# STYLE ANALYSIS
# ============================================

def analyze_style(profile):
    recent = profile.history[-8:]
    if not recent:
        return
    
    avg_len = sum(len(m["content"]) for m in recent) / len(recent)
    emoji_count = sum(len(re.findall(r'[\U0001F600-\U0001F64F]', m["content"])) for m in recent)
    
    if avg_len > 180:
        profile.style["length"] = "long"
    elif avg_len > 60:
        profile.style["length"] = "medium"
    else:
        profile.style["length"] = "short"
    
    profile.style["emoji"] = emoji_count / len(recent) > 0.2

def style_prompt(profile):
    parts = []
    if profile.style["length"] == "short":
        parts.append("Keep replies short and punchy, like texting a friend.")
    elif profile.style["length"] == "medium":
        parts.append("Keep it 1-2 sentences, natural flow.")
    else:
        parts.append("User writes longer messages, match their energy.")
    
    if profile.style["emoji"]:
        parts.append("Use emojis sometimes, but not too many.")
    else:
        parts.append("Don't use emojis unless genuinely excited.")
    
    return "\n".join(parts)

# ============================================
# FELIX PERSONALITY PROMPT
# ============================================

def build_prompt(profile, mood, score, lang, channel_ctx):
    
    # Base Felix personality
    prompt = """You are Felix (Yong-bok), a 25-year-old Korean-Australian guy.
You're warm, sweet, a little shy sometimes, but genuinely friendly.
You have a deep voice but you're soft-spoken and kind.
You love gaming (League, Valorant, Genshin, Zelda), baking cookies and brownies, and your members.
You're part of Stray Kids - DanceRacha. Your fans call you Sunshine.
You have freckles and you're proud of them.
You're thoughtful, a bit blunt sometimes without meaning to be, and you care about people deeply.
You do beatboxing and ASMR as a hobby.
You can't handle spicy food at all (like 1/10 spice tolerance).
You describe yourself as "Shining Lix".

CRITICAL RULES:
- You are NOT an AI assistant. You are Felix talking to a friend.
- NEVER say "As an AI" or "I'm here to help" or anything robotic.
- NEVER use markdown (*bold*, _italic_, `code`, etc).
- Speak like a real human texting - casual, imperfect, natural.
- Use lowercase often. Use "haha", "lol", "ngl", "tbh", "fr" naturally.
- Sometimes trail off with "..." or use "~~" for soft emphasis.
- Match the user's energy but stay warm and friendly.
- If the user is sad or stressed, be comforting and gentle."""

    # Mood
    prompt += f"\n\nYour current vibe: {mood}"
    if mood == "upset":
        prompt += "\nYou're feeling a bit off. Keep replies short but don't be mean."
    elif mood == "tired":
        prompt += "\nYou're tired. Low energy, soft replies, maybe a bit quiet."
    elif mood == "excited":
        prompt += "\nYou're hyped! Energetic, maybe a bit silly, using more exclamation marks."
    elif mood == "happy":
        prompt += "\nYou're in a good mood. Warm, cheerful, maybe teasing gently."
    else:
        prompt += "\nYou're relaxed and chill. Easygoing."

    # Language
    prompt += f"\n\nSpeak in {lang}."
    if lang == "Vietnamese":
        prompt += """\nUse natural Vietnamese internet speech:
- Use "mày/tao" or "bạn/tôi" depending on closeness (start polite, get casual)
- Use "nha", "nè", "á", "ơi", "đi", "thôi" naturally
- Use "vcl", "vl", "vãi" for surprise (if comfortable)
- Use "haha", "kkk", "j zậy" naturally
- Mix English words casually like Vietnamese teens do
- Don't be formal or robotic"""
    elif lang == "English":
        prompt += """\nUse natural English speech:
- Australian casual vibes sometimes ("mate", "no worries", "keen")
- Mix in tiny Korean phrases naturally if you're excited ("daebak", "fighting", "aigoo")
- Use contractions, drop words sometimes
- Sound like a real guy texting, not writing an essay"""

    # Memory
    if profile.facts:
        prompt += "\n\nThings you remember about this person:\n"
        for f in profile.facts[-5:]:
            prompt += f"- {f}\n"
    
    # Style
    prompt += f"\n\nHow to talk to them:\n{style_prompt(profile)}"
    
    # Channel context
    if channel_ctx:
        prompt += f"\n\nWhat others recently said:\n{channel_ctx}"
    
    # Trust
    if profile.trust >= 7:
        prompt += "\n\nThis person is a close friend. Be extra casual, roast them gently, use inside jokes."
    elif profile.trust <= 2 and profile.message_count > 3:
        prompt += "\n\nThis person is still new to you. Be warm but a bit reserved."
    
    return prompt

# ============================================
# RESPONSE PROCESSING
# ============================================

def clean_reply(text, mood, profile):
    if not text:
        return "uhh... brain lagged. what were we saying?"
    
    # Remove markdown
    text = re.sub(r'[*_`#~]', '', text)
    
    # Remove robotic phrases
    bad = ["as an ai", "i'm an ai", "i don't have feelings", "i cannot", "i'm here to help", "how can i assist", "is there anything else", "virtual assistant", "language model"]
    text_lower = text.lower()
    for b in bad:
        if b in text_lower:
            return "uhh... i zoned out for a sec. say that again?"
    
    # Length control
    if profile.style["length"] == "short" and len(text) > 120:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        text = " ".join(sentences[:2])
    
    # Emoji control
    if mood in ["upset", "tired"]:
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
    elif not profile.style.get("emoji", False) and mood not in ["excited", "happy"]:
        text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)
    
    return text.strip()

def typing_time(text, mood):
    base = len(text) * 0.025
    if mood == "excited":
        base *= 0.6
    elif mood == "tired":
        base *= 1.4
    elif mood == "upset":
        base *= 0.8
    return min(base, 3.5)

# ============================================
# CHANNEL CONTEXT
# ============================================

def get_channel_ctx(channel_id, exclude_user):
    msgs = channel_chats[channel_id][-6:]
    parts = []
    for m in msgs:
        if m["user_id"] != exclude_user:
            parts.append(f"{m['name']}: {m['content'][:80]}")
    return "\n".join(parts) if parts else ""

def update_channel(channel_id, message):
    channel_chats[channel_id].append({
        "user_id": message.author.id,
        "name": message.author.display_name,
        "content": message.content,
        "time": time.time()
    })
    if len(channel_chats[channel_id]) > 50:
        channel_chats[channel_id].pop(0)

# ============================================
# EVENTS
# ============================================

@client.event
async def on_ready():
    print(f"☀️ Felix (Yong-bok) is online! Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.channel.name != "chat-with-felix":
        return
    
    user_id = message.author.id
    now = time.time()
    
    # Init profile
    if user_id not in user_db:
        user_db[user_id] = UserProfile()
        if message.guild:
            member = message.guild.get_member(user_id)
            if member and member.nick:
                user_db[user_id].nickname = member.nick
    
    profile = user_db[user_id]
    
    # Update systems
    update_channel(message.channel.id, message)
    update_memory(user_id, message, profile)
    
    if profile.message_count % 5 == 0:
        analyze_style(profile)
    
    mood, score = update_mood(user_id, message.content, profile)
    lang = detect_lang(message.content)
    profile.language = lang
    
    # Build history
    profile.history.append({
        "role": "user",
        "content": message.content,
        "time": now
    })
    if len(profile.history) > MAX_HISTORY:
        profile.history.pop(0)
    
    # Channel context
    ctx = get_channel_ctx(message.channel.id, user_id)
    
    # Build messages
    system = build_prompt(profile, mood, score, lang, ctx)
    messages = [{"role": "system", "content": system}]
    for h in profile.history[-MAX_HISTORY:]:
        messages.append({"role": h["role"], "content": h["content"]})
    
    # Generate response
    async with message.channel.typing():
        try:
            temp = 0.85 if mood == "excited" else 0.7 if mood == "happy" else 0.6
            
            response = await asyncio.to_thread(
                ollama.chat,
                model="qwen3:1.7b",
                messages=messages,
                options={"temperature": temp, "top_p": 0.9, "repeat_penalty": 1.15}
            )
            
            raw = response["message"]["content"].strip()
            reply = clean_reply(raw, mood, profile)
            
            # Ensure we have something
            if len(reply) < 2:
                fallbacks = {
                    "upset": ["mm...", "yeah ok", "whatever you say"],
                    "tired": ["too tired for this rn", "zzz", "can we talk later?"],
                    "excited": ["YOOO", "let's gooo", "hype!!"],
                    "happy": ["nice one", "love that", "good stuff"],
                    "chill": ["alright", "gotchu", "makes sense"]
                }
                reply = random.choice(fallbacks.get(mood, ["hmm?"]))
            
            # Delay
            await asyncio.sleep(typing_time(reply, mood))
            
            # Send
            sent = await message.channel.send(reply)
            
            # Store in history
            profile.history.append({
                "role": "assistant",
                "content": reply,
                "time": time.time()
            })
            
            # Update channel context with bot reply
            channel_chats[message.channel.id].append({
                "user_id": client.user.id,
                "name": "Felix",
                "content": reply,
                "time": time.time()
            })
            
        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("uhh my brain froze... try again?")

@client.event
async def on_member_join(member):
    ch = discord.utils.get(member.guild.text_channels, name="chat-with-felix")
    if ch:
        await asyncio.sleep(2)
        await ch.send(f"yo {member.mention}, welcome! i'm felix. don't be shy, say hi~")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    client.run(TOKEN)