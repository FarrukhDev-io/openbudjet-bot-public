import time
import logging
from rate_limiter import is_rate_limited

logger = logging.getLogger("utils.limiter")

# Fallback in-memory sliding-window cache for OTP rate limits when Redis is down
otp_limit_cache = {}


async def check_rate_limit(phone: str, tg_id: int) -> bool:
    """
    Telefon raqami yoki Telegram ID bo'yicha 10 daqiqalik oynada jami 3 ta OTP so'rovga cheklov qo'yadi.
    Avval Redis orqali tekshiradi, agar ulanib bo'lmasa local in-memory fallback qiladi.
    True qaytarsa - ruxsat berilgan, False - limitdan oshgan.
    """
    # 1. Try Redis distributed rate limiting (Primary)
    try:
        # Check limit for both phone and tg_id separately
        phone_limited = await is_rate_limited(f"phone:{phone}", max_requests=3, window_seconds=600)
        tg_limited = await is_rate_limited(f"tg_id:{tg_id}", max_requests=3, window_seconds=600)
        if phone_limited or tg_limited:
            return False
        return True
    except Exception as e:
        logger.warning("Redis rate limiter failed, falling back to local memory: %s", e)

    # 2. Local memory fallback (Secondary)
    now = time.time()
    ten_minutes_ago = now - 600

    # Eski ma'lumotlarni tozalash
    for key in list(otp_limit_cache.keys()):
        otp_limit_cache[key] = [t for t in otp_limit_cache[key] if t > ten_minutes_ago]
        if not otp_limit_cache[key]:
            del otp_limit_cache[key]

    # Phone yoki Tg ID ga bog'liq barcha so'rov vaqtlarini yig'ish
    phone_requests = []
    tg_requests = []

    for (p, t), ts in otp_limit_cache.items():
        if p == phone:
            phone_requests.extend(ts)
        if t == tg_id:
            tg_requests.extend(ts)

    # 10 daqiqalik oyna ichidagilarini filtrlash
    phone_requests = [t for t in phone_requests if t > ten_minutes_ago]
    tg_requests = [t for t in tg_requests if t > ten_minutes_ago]

    if len(phone_requests) >= 3 or len(tg_requests) >= 3:
        return False

    # Yangi so'rovni qo'shish
    key = (phone, tg_id)
    if key not in otp_limit_cache:
        otp_limit_cache[key] = []
    otp_limit_cache[key].append(now)
    return True
