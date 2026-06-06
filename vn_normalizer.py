"""
vn_normalizer.py — normalizes Vietnamese internet slang and abbreviations
so the LLM understands what was actually said.

Strategy: normalize ONLY for the internal context passed to the model.
Keep the original text for display/history so the chat feels natural.
"""

import re

# ─────────────────────────────────────────────────────────────────
# Core VN slang → normalized form
# We normalize to something the model understands, not necessarily
# "proper" Vietnamese — just clear meaning.
# ─────────────────────────────────────────────────────────────────
VN_MAP = {
    # Swear-adjacent / emphasis
    "vc":   "vãi",
    "vl":   "vãi (rất mạnh)",
    "vcl":  "vãi cả (rất mạnh)",
    "cc":   "con c** (chửi)",
    "dm":   "đ** mẹ (chửi)",
    "clm":  "c*c lồn má (chửi)",

    # Negation / agreement shortcuts
    "k":    "không",
    "ko":   "không",
    "kh":   "không",
    "kp":   "không phải",
    "kbt":  "không biết",
    "cx":   "cũng",
    "cg":   "cũng",

    # Done / completed
    "r":    "rồi",
    "roi":  "rồi",
    "xr":   "xong rồi",

    # Okay / normal
    "oke":  "okay",
    "okie": "okay",
    "ok":   "okay",
    "bt":   "bình thường",
    "bth":  "bình thường",

    # Can / possible
    "dc":   "được",
    "đc":   "được",
    "dk":   "được",

    # Messaging / action
    "ib":   "inbox (nhắn tin riêng)",
    "rep":  "reply (trả lời)",
    "tag":  "tag (đề cập)",
    "cm":   "comment (bình luận)",

    # Feelings
    "tbt":  "thật buồn thật",
    "buon": "buồn",
    "chan": "chán",
    "met":  "mệt",

    # Filler / connector
    "nma":  "nhưng mà",
    "mà":   "mà (nhưng/thì)",
    "thôi": "thôi (kết thúc/chấp nhận)",
    "hên xui": "may rủi",
    "kiểu": "kiểu như (kind of)",
    "kieu": "kiểu như (kind of)",
    "vậy":  "vậy (like that / so)",

    # Time
    "h":    "giờ (now / hour)",
    "bh":   "bây giờ (right now)",
    "t":    "tao (I/me - informal)",
    "m":    "mày (you - informal)",
    "mk":   "mình (I/me - softer)",
    "mn":   "mọi người (everyone)",
    "a":    "anh (older brother/sir)",
    "c":    "chị (older sister/ma'am)",
    "e":    "em (younger sibling/self-humble)",

    # Reaction
    "haha": "haha (cười)",
    "hehe": "hehe (cười nhẹ)",
    "hihi": "hihi (cười dễ thương)",
}

# Phrases that appear as multi-word (check before single-word split)
VN_PHRASE_MAP = {
    "hên xui":      "may rủi (hit or miss)",
    "chill thôi":   "bình tĩnh thôi (just chill)",
    "thôi kệ":      "kệ nó (forget it)",
    "oke bro":      "okay bro",
    "đúng r":       "đúng rồi (yeah exactly)",
    "ừ r":          "ừ rồi (yeah already)",
    "out r":        "xong rồi / thoát rồi",
    "vào r":        "vào rồi (already in)",
    "biết r":       "biết rồi (I know already)",
    "no cap":       "thật sự (no cap)",
    "fr fr":        "thật sự (for real)",
}


def normalize(text: str) -> str:
    """
    Returns a normalized version of the input for LLM context.
    - Replaces known VN slang with clearer forms
    - Collapses excessive repeated characters (hahahaha → haha)
    - Preserves original structure otherwise
    """
    # Step 1: multi-word phrase replacement (case-insensitive)
    result = text
    for phrase, replacement in VN_PHRASE_MAP.items():
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        result = pattern.sub(replacement, result)

    # Step 2: word-level replacement
    words = result.split()
    normalized_words = []
    for word in words:
        # Strip punctuation for lookup but preserve it
        stripped = word.lower().strip(".,!?;:\"'()[]{}…")
        replacement = VN_MAP.get(stripped)
        if replacement:
            # Preserve trailing punctuation
            suffix = word[len(word.rstrip(".,!?;:\"'()[]{}…")):]
            normalized_words.append(replacement + suffix)
        else:
            normalized_words.append(word)
    result = " ".join(normalized_words)

    # Step 3: collapse 3+ repeated characters → max 2
    # e.g. "haaaaa" → "haa", "kkkkk" → "kk"
    result = re.sub(r"(.)\1{2,}", r"\1\1", result)

    return result


def normalize_display(text: str) -> str:
    """
    Lighter version for display — only collapses repeated chars,
    doesn't replace slang. Used when you want to keep the original vibe
    but just clean up the string a bit.
    """
    return re.sub(r"(.)\1{2,}", r"\1\1", text)