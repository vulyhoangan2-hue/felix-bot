"""
intent.py — detects the intent/purpose of a message across EN/VN/KR/JP.
"""


def detect_intent(text: str) -> str:
    """
    Returns one of:
      help_request  — asking for help or explanation
      question      — general question
      vent          — emotional dump / rant
      joke          — being funny / trolling
      greeting      — hi/hello/hey
      compliment    — saying something nice to Felix
      food_talk     — talking about food (Felix's fave topic)
      music_talk    — talking about music/SKZ/kpop
      chat          — general casual chat (default)
    """
    t = text.lower().strip()

    # ── Greeting ──────────────────────────────
    greeting_triggers = [
        "hello", "hi ", "hey", "sup ", "wassup", "yo ", "heyy", "heyyy",
        "chào", "ê", "ơi", "xin chào",
        "안녕", "여보세요", "야",
        "こんにちは", "おはよ", "やあ",
    ]
    if any(t.startswith(g) or t == g.strip() for g in greeting_triggers):
        return "greeting"

    # ── Japanese learning ──────────────────────
    jp_learning_triggers = [
        "日本語", "にほんご", "japanese", "kanji", "hiragana", "katakana",
        "jlpt", "n5", "n4", "n3", "n2", "n1",
        "どういう意味", "何て読む", "文法", "conjugat", "て形", "た形",
        "teach me", "how do you say", "what does", "translate",
        "これは何", "意味は", "使い方",
    ]
    if any(x in t for x in jp_learning_triggers):
        return "japanese_learning"

    # ── Help / Explanation request ─────────────
    help_triggers = [
        "help", "how do", "how to", "can you explain", "what is", "what does",
        "tell me about", "explain", "why does", "why is", "i don't understand",
        "giúp", "làm sao", "cách nào", "là gì", "tại sao", "giải thích",
        "도와줘", "어떻게", "뭐야", "설명해",
        "教えて", "どうやって", "なんで",
    ]
    if any(x in t for x in help_triggers):
        return "help_request"

    # ── Food talk ──────────────────────────────
    food_triggers = [
        "cookie", "cookies", "bake", "food", "eat", "hungry", "recipe",
        "ramen", "pho", "bánh", "ăn", "đói", "ngon", "nấu", "món",
        "먹", "맛있", "요리", "배고", "라면", "치킨",
        "食べ", "おいしい", "ラーメン",
    ]
    if any(x in t for x in food_triggers):
        return "food_talk"

    # ── Music / SKZ talk ──────────────────────
    music_triggers = [
        "stray kids", "skz", "straykids", "kpop", "k-pop", "song", "mv",
        "album", "concert", "comeback", "dance", "choreo", "stage",
        "chan", "minho", "changbin", "hyunjin", "jisung", "seungmin", "i.n", "jeongin",
        "nhạc", "bài hát", "nghe nhạc",
        "노래", "춤", "컴백", "무대",
        "音楽", "ダンス",
    ]
    if any(x in t for x in music_triggers):
        return "music_talk"

    # ── Vent / Rant ────────────────────────────
    vent_triggers = [
        "i hate", "i can't", "this is so", "so tired", "i'm done", "im done",
        "ugh", "why is everything", "i want to cry", "i feel so", "i've been",
        "so alone", "lonely", "nobody", "no one", "i don't know what",
        "i just feel", "it's been hard", "been struggling", "can't stop",
        "vcl", "vl", "bực", "chán", "mệt", "stress", "tức", "ghét",
        "짜증", "힘들", "지겨워", "싫어",
        "つかれた", "もう嫌", "最悪",
    ]
    if len(t) > 100 or any(x in t for x in vent_triggers):
        return "vent"

    # ── Joke / Troll ──────────────────────────
    # (checked after vent so "vcl" in an emotional context hits vent first)
    joke_triggers = [
        "lmao", "lmfao", "💀", "hahaha", "hehehehe", "kkkk", "kkkkk",
        "😂", "🤣", "bruh", "bro what", "no way",
        "=))", "haha", "hihi", "hehe",
        "ㅋㅋㅋ", "ㅋㅋㅋㅋ",
        "www", "草",
    ]
    if any(x in t for x in joke_triggers):
        return "joke"

    # ── Compliment ────────────────────────────
    compliment_triggers = [
        "you're so", "ur so", "i love you", "ily", "love u", "best boy",
        "so cute", "adorable", "amazing", "i like you", "my fav",
        "thích felix", "yêu", "dễ thương",
        "좋아", "사랑해", "귀여워", "최고야",
        "かわいい", "好き", "大好き",
    ]
    if any(x in t for x in compliment_triggers):
        return "compliment"

    # ── Question ──────────────────────────────
    if t.endswith("?") or "?" in t:
        return "question"

    return "chat"