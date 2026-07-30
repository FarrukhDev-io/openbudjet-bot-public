import time

# In-memory sliding-window cache for OTP rate limits
otp_limit_cache = {}


def check_rate_limit(phone: str, tg_id: int) -> bool:
    """
    Telefon raqami yoki Telegram ID bo'yicha 10 daqiqalik oynada jami 3 ta OTP so'rovga cheklov qo'yadi.
    True qaytarsa - ruxsat berilgan, False - limitdan oshgan.
    """
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
