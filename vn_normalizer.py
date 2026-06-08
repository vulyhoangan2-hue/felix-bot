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
    # Negation
    "k":    "không",
    "ko":   "không",
    "kh":   "không",
    "khg":  "không",
    "kp":   "không phải",
    "kbt":  "không biết",
    "đbt":  "không biết",

    # Done / completed
    "r":    "rồi",
    "rr":   "rồi",
    "xr":   "xong rồi",

    # Can / possible
    "dc":   "được",
    "đc":   "được",
    "dk":   "được",

    # Also / too
    "cx":   "cũng",
    "cg":   "cũng",

    # With
    "vs":   "với",

    # Now / time
    "h":    "giờ",
    "bh":   "bây giờ",
    "trc":  "trước",

    # People / pronouns
    "mk":   "mình",
    "mik":  "mình",
    "mn":   "mọi người",
    "ngta": "người ta",
    "tui":  "tôi",

    # What / how
    "j":    "gì",
    "v":    "vậy",
    "z":    "vậy",
    "vz":   "vậy",
    "ntn":  "như thế nào",
    "nt":   "như thế",

    # But
    "nma":  "nhưng mà",
    "nhma": "nhưng mà",

    # Okay / fine
    "oke":  "okay",
    "okie": "okay",
    "ok":   "okay",

    # Normal
    "bt":   "bình thường",
    "bth":  "bình thường",

    # Messaging
    "ib":   "inbox (nhắn riêng)",
    "rep":  "reply (trả lời)",

    # School
    "sv":   "sinh viên",
    "btvn": "bài tập về nhà",
    "gv":   "giáo viên",
    "hs":   "học sinh",
    "thay": "thầy",

    # Swear/emphasis (normalize for model understanding)
    "vc":   "vãi",
    "vl":   "vãi (rất mạnh)",
    "vcl":  "vãi cả (rất mạnh)",
    "dm":   "chửi thề nhẹ",
    "đm":   "chửi thề nhẹ",
}

VN_PHRASE_MAP = {
    "hên xui":      "may rủi (hit or miss)",
    "chill thôi":   "bình tĩnh thôi",
    "thôi kệ":      "kệ nó đi",
    "kệ đi":        "forget it",
    "oke bro":      "okay bro",
    "đúng r":       "đúng rồi",
    "ừ r":          "ừ rồi",
    "biết r":       "biết rồi",
    "hiểu r":       "hiểu rồi",
    "xong r":       "xong rồi",
    "out r":        "ra ngoài rồi / thoát rồi",
    "vào r":        "vào rồi",
    "no cap":       "thật sự",
    "fr fr":        "thật sự",
    "thật á":       "thật sao / really",
    "vậy á":        "oh vậy sao",
    "vậy hả":       "oh vậy sao",
    "thôi thì":     "well then / vậy thì",
    "từ từ đã":     "hold on / chờ chút",
    "tùy thôi":     "up to you / tùy",
    "chắc vậy":     "probably / I guess",
    "nma thôi":     "nhưng thôi / but forget it",
    "ừ mà thôi":    "yeah but whatever",
    "kiểu kiểu":    "kinda sorta / đại loại vậy",
    "cũng được":    "that works / okay sure",
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