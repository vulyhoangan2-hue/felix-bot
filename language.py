def detect_language(text):

    korean = sum(
        1 for c in text
        if '\uac00' <= c <= '\ud7a3'
    )

    japanese = sum(
        1 for c in text
        if '\u3040' <= c <= '\u30ff'
    )

    vietnamese = sum(
        1 for c in text
        if c in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
    )

    if korean:
        return "Korean"

    if japanese:
        return "Japanese"

    if vietnamese:
        return "Vietnamese"

    return "English"


language_modes = {}


def set_language_mode(user_id, language):
    language_modes[user_id] = language


def get_language_mode(user_id):
    return language_modes.get(user_id)