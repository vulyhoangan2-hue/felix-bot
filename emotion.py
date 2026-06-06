"""
emotion.py — detects the emotional tone of a message across EN/VN/KR/JP.
"""


def detect_emotion(text: str) -> str:
    """
    Returns one of:
      happy      — positive, fun, energetic
      excited    — hyped, caps, exclamation
      sad        — down, tired, low energy
      frustrated — annoyed, angry
      nervous    — anxious, worried
      soft       — nostalgic, gentle, missing someone
      neutral    — no strong signal
    """
    t = text.lower().strip()

    # ── Frustrated / Angry ─────────────────────
    frustrated_triggers = [
        "vcl", "vl", "vc ", "wtf", "what the f",
        "bực", "tức", "ghét", "điên", "chịu không nổi",
        "pissed", "angry", "so annoyed", "hate this", "ugh", "i'm done",
        "짜증", "열받", "싫어", "화나",
        "最悪", "むかつく", "ありえない",
    ]
    if any(x in t for x in frustrated_triggers):
        return "frustrated"

    # ── Sad / Low ─────────────────────────────
    sad_triggers = [
        "sad", "cry", "crying", "i want to cry", "im so sad",
        "buồn", "chán", "mệt", "khóc", "cô đơn", "nhớ",
        "힘들어", "슬퍼", "외로워", "보고싶어", "ㅠㅠ", "ㅜㅜ",
        "つらい", "かなしい", "寂しい", "ㅠ",
        "😢", "😭", "💔",
    ]
    if any(x in t for x in sad_triggers):
        return "sad"

    # ── Nervous / Anxious ─────────────────────
    nervous_triggers = [
        "nervous", "anxious", "anxiety", "scared", "worried", "i'm freaking out",
        "lo lắng", "hồi hộp", "sợ",
        "불안", "긴장", "무서워",
        "こわい", "不安", "ドキドキ",
    ]
    if any(x in t for x in nervous_triggers):
        return "nervous"

    # ── Soft / Nostalgic / Missing ─────────────
    soft_triggers = [
        "miss", "missing", "remember when", "i wish", "nostalgia",
        "nhớ", "thương", "hồi đó",
        "그립다", "보고싶다",
        "懐かしい", "会いたい",
        "🥺", "🤍", "☁️",
    ]
    if any(x in t for x in soft_triggers):
        return "soft"

    # ── Excited / Hyped ───────────────────────
    if text != text.lower() and len([c for c in text if c.isupper()]) > 4:
        return "excited"
    excited_triggers = [
        "omg", "oh my god", "no way", "wait what", "WAIT",
        "i'm so hyped", "can't wait", "yesss", "lesgo", "let's go",
        "trời ơi", "chời ơi", "OMG",
        "대박", "헐", "진짜요", "세상에",
        "やばい", "まじか", "すごい",
        "🎉", "🔥", "😱",
    ]
    if any(x in t for x in excited_triggers):
        return "excited"

    # ── Happy / Playful ───────────────────────
    happy_triggers = [
        "haha", "lol", "lmao", "hehe", "hihi", "=))", "😂", "😄", "🤣",
        "so fun", "this is great", "love it", "love this",
        "vui", "okie", "oke bro", "thích",
        "ㅋㅋ", "ㅎㅎ",
        "w", "草",
    ]
    if any(x in t for x in happy_triggers):
        return "happy"

    # ── Excited from punctuation ──────────────
    if t.count("!") >= 2:
        return "excited"

    return "neutral"