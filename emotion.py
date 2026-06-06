def detect_emotion(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["vc", "vl", "wtf", "bực", "điên"]):
        return "frustrated"

    if any(x in t for x in ["haha", "=))", "vui", "okie"]):
        return "happy"

    if any(x in t for x in ["buồn", "chán", "mệt", "stress"]):
        return "sad"

    if "!" in t:
        return "excited"

    return "neutral"