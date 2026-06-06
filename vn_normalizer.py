import re

VN_MAP = {
    "vc": "vãi",
    "vl": "vãi lồn",
    "vcl": "vãi cả lồn",
    "k": "không",
    "ko": "không",
    "kh": "không",
    "dc": "được",
    "đc": "được",
    "r": "rồi",
    "roi": "rồi",
    "bt": "bình thường",
}

def normalize(text: str) -> str:
    t = text.lower()

    words = t.split()
    words = [VN_MAP.get(w, w) for w in words]
    t = " ".join(words)

    t = re.sub(r"(.)\1{2,}", r"\1\1", t)

    return t