"""
language.py — detects the dominant language in a message,
with support for mixed/code-switched messages common in multilingual group chats.
"""

def detect_language(text: str) -> str:
    """
    Returns the dominant language as a string.
    Handles code-switching (e.g. Vietnamese + English mixed).
    Priority: Korean > Japanese > Vietnamese > English
    because CJK scripts are unambiguous, while Latin script is shared.
    """
    t = text.strip()
    if not t:
        return "English"

    korean_chars = sum(1 for c in t if '\uac00' <= c <= '\ud7a3' or c in 'ㄱ-ㅎㅏ-ㅣ')
    japanese_chars = sum(1 for c in t if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    # Hiragana + Katakana only — kanji is shared with Chinese, don't count it

    vietnamese_markers = (
        "ăâđêôơư"
        "áàảãạấầẩẫậắằẳẵặéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
        "ĂÂĐÊÔƠƯ"
        "ÁÀẢÃẠẤẦẨẪẬẮẰẲẴẶÉÈẺẼẸÍÌỈĨỊÓÒỎÕỌÚÙỦŨỤÝỲỶỸỴ"
    )
    vietnamese_chars = sum(1 for c in t if c in vietnamese_markers)

    # Unambiguous script wins immediately
    if korean_chars > 0:
        return "Korean"
    if japanese_chars > 0:
        return "Japanese"

    # Vietnamese needs at least 1 diacritic marker
    if vietnamese_chars >= 1:
        return "Vietnamese"

    # Vietnamese-looking text without diacritics (typed fast/lazy)
    # Check for common Vietnamese words written without accents
    vn_bare_words = {
        "mày", "tao", "tui", "bạn", "ban", "minh", "mình",
        "không", "ko", "khong", "oke", "okie", "rồi", "roi",
        "được", "duoc", "dc", "thôi", "thoi", "vậy", "vay",
        "nha", "nhe", "nhen", "á", "ạ", "ơi", "oi",
        "bro", "mà", "ma", "hay", "sao", "vì", "vi",
        "có", "co", "với", "voi", "trong", "nên", "nen",
        "nma", "nhưng", "nhung", "haha", "hihi", "hehe",
        "trời", "troi", "ơi", "chời", "choi",
    }
    words_lower = set(t.lower().split())
    vn_hits = words_lower.intersection(vn_bare_words)
    if len(vn_hits) >= 2:
        return "Vietnamese"

    return "English"


def detect_mix(text: str) -> list[str]:
    """
    Returns all languages present in a message (for code-switching awareness).
    Useful for Felix to know he can mix languages back.
    """
    langs = []
    t = text.strip()

    korean_chars = sum(1 for c in t if '\uac00' <= c <= '\ud7a3')
    japanese_chars = sum(1 for c in t if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    vietnamese_markers = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
    vietnamese_chars = sum(1 for c in t if c in vietnamese_markers)

    if korean_chars > 0:
        langs.append("Korean")
    if japanese_chars > 0:
        langs.append("Japanese")
    if vietnamese_chars >= 1:
        langs.append("Vietnamese")

    # If Latin characters exist (beyond just CJK)
    latin_chars = sum(1 for c in t if c.isalpha() and c.isascii())
    if latin_chars > 3:
        langs.append("English")

    return langs if langs else ["English"]


# Per-user language mode override (if user explicitly sets a language)
language_modes: dict[str, str] = {}

def set_language_mode(user_id: str, language: str):
    language_modes[user_id] = language

def get_language_mode(user_id: str) -> str | None:
    return language_modes.get(user_id)