import base64
import random


def generate_captcha_header() -> str:
    """Ovoz berish uchun maxsus xavfsizlik headeri yaratish"""
    def _ae(e=10, t=5):
        return int(random.random() * (e - t) + t)
    n = 12
    val = (
        "s" + str(_ae(-3) * n) +
        "e" + str(_ae(2, 19) * n) +
        "k" + str(_ae(10, 5) * n) +
        "r" + str(_ae(10, 4) * n) +
        "e" + str(_ae(10, 220)) +
        "t"
    )
    return base64.b64encode(val.encode()).decode()


def base64_to_bytes(b64_string: str) -> bytes:
    """Base64 rasmni baytlarga o'tkazish"""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    return base64.b64decode(b64_string)


def prepare_captcha_bytes(b64_string: str) -> bytes:
    """Base64 rasmni olib, Telegram qabul qiladigan va aniq ko'rinadigan qilib kattalashtiradi"""
    raw_bytes = base64_to_bytes(b64_string)
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        width, height = img.size
        new_img = img.resize((width * 3, height * 3), Image.Resampling.LANCZOS)
        out_io = io.BytesIO()
        new_img.save(out_io, format="PNG")
        return out_io.getvalue()
    except Exception:
        return raw_bytes

