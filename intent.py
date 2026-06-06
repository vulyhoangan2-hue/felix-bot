def detect_intent(text: str) -> str:
    t = text.lower()

    if any(x in t for x in ["giúp", "help", "how", "làm sao"]):
        return "help_request"

    if t.endswith("?"):
        return "question"

    if any(x in t for x in ["vc", "vl", "=))", "haha", "kk"]):
        return "joke"

    if len(t) > 120:
        return "rant"

    return "chat"