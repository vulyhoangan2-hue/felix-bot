"""
planner.py — decides HOW Felix should respond based on intent, emotion, and user profile.
Produces a "plan" dict that shapes the system prompt.
"""


def build_plan(intent: str, emotion: str, profile: dict) -> dict:
    """
    Returns a plan dict:
      tone    — how Felix sounds (playful / soft / calm / clear / hype / warm)
      emoji   — 0 (none), 1 (light), 2 (moderate), 3 (expressive)
      length  — "short" | "medium" | "long"
      style   — "casual" | "supportive" | "explain" | "banter"
    """
    trust = profile.get("trust", 0)

    # ── Defaults ──────────────────────────────
    plan = {
        "tone": "warm",
        "emoji": 1,
        "length": "short",
        "style": "casual",
    }

    # ── Emotion shapes tone first ─────────────
    emotion_map = {
        "frustrated": ("calm",      1, "short",  "supportive"),
        "sad":        ("soft",      1, "medium", "supportive"),
        "nervous":    ("warm",      1, "medium", "supportive"),
        "soft":       ("soft",      1, "medium", "supportive"),
        "happy":      ("playful",   2, "short",  "banter"),
        "excited":    ("hype",      2, "short",  "banter"),
        "neutral":    ("warm",      1, "short",  "casual"),
    }
    if emotion in emotion_map:
        plan["tone"], plan["emoji"], plan["length"], plan["style"] = emotion_map[emotion]

    # ── Intent can override ───────────────────
    if intent == "help_request":
        plan["tone"] = "clear"
        plan["emoji"] = 0
        plan["length"] = "medium"
        plan["style"] = "explain"

    elif intent == "vent":
        plan["tone"] = "soft"
        plan["emoji"] = 1
        plan["length"] = "medium"
        plan["style"] = "supportive"

    elif intent == "joke":
        plan["tone"] = "playful"
        plan["emoji"] = 2
        plan["style"] = "banter"

    elif intent == "greeting":
        plan["tone"] = "warm"
        plan["emoji"] = 1
        plan["length"] = "short"
        plan["style"] = "casual"

    elif intent == "compliment":
        plan["tone"] = "soft"
        plan["emoji"] = 2
        plan["length"] = "short"
        plan["style"] = "casual"

    elif intent == "food_talk":
        plan["tone"] = "excited"   # Felix LOVES food
        plan["emoji"] = 2
        plan["style"] = "banter"

    elif intent == "music_talk":
        plan["tone"] = "playful"
        plan["emoji"] = 1
        plan["style"] = "banter"

    # ── Trust adjusts slang level ─────────────
    # Low trust (0–20): keep it light, don't go too slangy
    # Medium trust (21–60): normal casual
    # High trust (61–100): full slang, more teasing allowed
    if trust < 20:
        plan["slang"] = 0
    elif trust < 60:
        plan["slang"] = 1
    else:
        plan["slang"] = 2

    return plan


def plan_to_hint(plan: dict) -> str:
    """
    Converts a plan into a short natural-language hint for the system prompt.
    Felix uses this to calibrate his response without being told what to do mechanically.
    """
    tone_hints = {
        "calm":    "Stay gentle and grounding. Don't match frustration.",
        "soft":    "Be warm and real. No toxic positivity.",
        "warm":    "Be your usual sunshine self.",
        "playful": "Be fun and a bit teasing.",
        "hype":    "Match their energy! Be excited.",
        "clear":   "Explain clearly and simply. Less slang.",
        "excited": "You're genuinely excited about this topic.",
    }
    style_hints = {
        "supportive": "Listen first. Acknowledge feelings. Don't rush to fix.",
        "banter":     "Keep it light and fun. Tease a little if trust allows.",
        "explain":    "Use examples. Keep it simple. Check if they understood.",
        "casual":     "Just be yourself, talking to a friend.",
    }
    emoji_hints = {
        0: "No emojis.",
        1: "One emoji at most, only if it fits naturally.",
        2: "A couple emojis are fine.",
        3: "Be expressive with emojis.",
    }

    parts = []
    parts.append(tone_hints.get(plan["tone"], "Be yourself."))
    parts.append(style_hints.get(plan["style"], "Just talk naturally."))
    parts.append(emoji_hints.get(plan["emoji"], "Use emojis sparingly."))
    if plan["length"] == "short":
        parts.append("Keep it SHORT — 1-2 sentences max.")
    elif plan["length"] == "medium":
        parts.append("A few sentences is fine here.")
    else:
        parts.append("Can go a bit longer if needed.")

    return " ".join(parts)