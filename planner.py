def build_plan(intent, emotion, profile):
    plan = {
        "tone": "neutral",
        "slang": profile.get("slang_level", 1),
        "emoji": 1,
        "length": "short"
    }

    # emotion rules
    if emotion == "frustrated":
        plan["tone"] = "calm"

    if emotion == "happy":
        plan["tone"] = "playful"
        plan["emoji"] = 2

    if emotion == "sad":
        plan["tone"] = "soft"

    # intent rules
    if intent == "help_request":
        plan["tone"] = "clear"
        plan["slang"] = 0
        plan["length"] = "medium"

    if intent == "joke":
        plan["tone"] = "playful"
        plan["emoji"] = 3

    return plan