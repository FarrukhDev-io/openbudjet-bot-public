# OpenBudjet Bot — Senior Developer AI Guide

> Bu fayl loyihada ishlaydigan har qanday AI agent uchun yozilgan.
> Siz bu loyihani o'qiyotgan AI sifatida, quyidagi qoidalarga **qat'iy** rioya qiling.
> Kod yozishdan oldin bu faylni **to'liq** o'qing.

---

## 🗺 Loyiha Arxitekturasi (Folder Structure)

```
openbudjet-bot/
│
├── bot.py                    # Faqat ishga tushirish (Entrypoint). Bu yerga handler yozma!
├── config.py                 # Barcha sozlamalar (.env dan o'qiladi). Hardcode qilma!
├── requirements.txt
├── .env                      # Maxfiy ma'lumotlar. Bu faylga tegma!
│
├── database/
│   ├── connection.py         # PostgreSQL pool va get_conn() context manager
│   ├── models.py             # Barcha async SQL funksiyalari (CRUD)
│   └── __init__.py           # Public API: faqat kerakli funksiyalarni export qil
│
├── handlers/
│   ├── user.py               # /start, /help, referral, loyiha haqida
│   ├── vote.py               # FSM: Telefon → Captcha → OTP → Karta
│   ├── admin.py              # Admin panel, statistika, to'lovlarni tasdiqlash
│   ├── api.py                # aiohttp Web API endpoints (Mini App uchun)
│   └── __init__.py
│
├── keyboards/
│   ├── user.py               # Foydalanuvchi klaviaturalari
│   ├── admin.py              # Admin klaviaturalari (P2P deep link tugmalari)
│   └── __init__.py
│
├── utils/
│   ├── validation.py         # Luhn algoritmi, karta/telefon formatlash, P2P havolalar
│   ├── captcha.py            # Captcha header generatsiyasi, base64, HTTP helpers
│   ├── limiter.py            # OTP Rate Limiter (10 daqiqada max 3 ta SMS)
│   └── __init__.py
│
└── adminpanel-vite/          # React + TypeScript + Tailwind CSS v4 (Mini App)
    └── src/
        ├── types/index.ts
        ├── hooks/useTelegram.ts
        ├── components/
        │   ├── ui/Button.tsx, Card.tsx, Modal.tsx
        │   ├── StatsGrid.tsx
        │   ├── TabNavigation.tsx
        │   ├── PaymentCard.tsx
        │   ├── BulkActionBar.tsx
        │   └── RejectModal.tsx
        └── App.tsx
```

---

## ⚠️ Doiraviy Import (Circular Import) Qoidasi

Bu loyihaning **eng xavfli** muammosi — doiraviy importlar.

### Qoidalar:
- `handlers/vote.py` hech qachon `handlers/admin.py` dan import qilma.
- `handlers/admin.py` hech qachon `handlers/vote.py` dan import qilma.
- Handler fayllar faqat quyidagilardan import qilishi mumkin:
  - `config` ✅
  - `database` (paket sifatida: `import database as db`) ✅
  - `keyboards` (paket sifatida: `import keyboards as kb`) ✅
  - `utils` (paket sifatida: `import utils`) ✅
- Agar handler ichida boshqa handler funksiyasi kerak bo'lsa, uni **`utils/` ga ko'chir**.

### Mushtarak funksiyalar qayerda turishi kerak:
```
is_admin()          → utils/validation.py yoki config.py da tekshir
is_voting_period()  → utils/validation.py
notify_admins()     → utils/helpers.py (alohida fayl)
mask_card()         → utils/validation.py
generate_p2p_links()→ utils/validation.py
```

---

## 🔐 Xavfsizlik Qoidalari (Security Rules)

1. **Hech qachon kod ichiga maxfiy ma'lumot yozma:**
   - Token, parol, API key → `.env` faylida bo'lishi shart.
   - `config.py` faqat `os.getenv()` orqali o'qiydi.

2. **Barcha foydalanuvchi kiritgan ma'lumotlarni tekshir:**
   - Telefon raqami → `utils/validation.py:clean_phone_number()`
   - Karta raqami → `utils/validation.py:validate_uz_card()` (Luhn + prefix)
   - OTP kodi → faqat raqam, minimum 4 ta belgi

3. **Bir telefon — bir ovoz, bir to'lov:**
   - `votes` jadvalida `phone` ustunida `UNIQUE` cheklov bor.
   - `payment_requests` jadvalida `phone` ustunida `UNIQUE` cheklov bor.
   - Bu cheklovlarga `ON CONFLICT DO NOTHING` bilan muomala qil.

4. **Rate Limiting:**
   - OTP yuborishda: 10 daqiqada max 3 ta urinish (telefon + tg_id bo'yicha).
   - `utils/limiter.py:check_rate_limit(phone, tg_id)` → `True` bo'lsagina davom et.

5. **Admin autentifikatsiyasi:**
   - Handler boshida `if not is_admin(user.id): return` — bu qatorni o'chirishga haqing yo'q.
   - Web API endpointlarda `admin_id` parametrini `config.ADMIN_IDS` bilan tekshir.

6. **Xato xabarlarini foydalanuvchiga bermа:**
   - `logger.exception("...")` bilan loglash ✅
   - `await message.answer(f"Xato: {e}")` ❌ — ichki xatolarni ko'rsatma.

---

## 🗄️ Database Qoidalari (PostgreSQL + asyncpg)

### Muhim farqlar (SQLite vs PostgreSQL):
| SQLite | PostgreSQL |
|--------|------------|
| `?` placeholder | `$1, $2, $3` placeholder |
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| `datetime('now','localtime')` | `NOW()` yoki `CURRENT_TIMESTAMP` |
| `INSERT OR IGNORE` | `ON CONFLICT (col) DO NOTHING` |
| `INSERT OR REPLACE` | `ON CONFLICT (col) DO UPDATE SET ...` |

### Connection Pool ishlatish usuli:
```python
# XATO usul:
conn = await asyncpg.connect(DATABASE_URL)

# TO'G'RI usul (get_conn() context manager):
async with get_conn() as conn:
    row = await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)
    return dict(row) if row else None
```

### Record → dict o'girish:
```python
# asyncpg Record ni dict ga to'g'ri o'girish:
return dict(row)  # ✅
# yoki list uchun:
return [dict(r) for r in rows]  # ✅
```

---

## ⚡ Async Qoidalar

- Barcha database funksiyalari `async def` bo'lishi shart.
- Barcha handler funksiyalari `async def` bo'lishi shart.
- `aiohttp.ClientSession` faqat bitta marta yaratiladi (`bot.py:main()` da).
- Session `dispatcher.workflow_data["session"]` orqali handlerlarga uzatiladi.
- Handler ichida sessiyani `message.bot.dispatcher.workflow_data.get("session")` bilan olish.

---

## 🧩 Modullar o'rtasidagi Xabar Uzatish (Dependency Flow)

```
config.py           ← Hech narsadan import qilmaydi
    ↓
database/           ← Faqat config dan import qiladi
    ↓
utils/              ← Faqat config dan import qiladi
    ↓
keyboards/          ← Faqat config dan import qiladi
    ↓
handlers/           ← config, database, keyboards, utils dan import qiladi
    ↓
bot.py              ← Hammasini yig'adi va ishga tushiradi
```

> ⚠️ Bu oqimga **XILOF** bo'lgan har qanday import doiraviy importga olib keladi.

---

## 💳 P2P To'lov Havolalari (Payment Deep Links)

Karta raqami va summa berilganda, to'lov havolalarini yaratish:

```python
# utils/validation.py da:
def generate_p2p_links(card_number: str, amount: int) -> dict:
    return {
        "click": f"https://my.click.uz/services/p2p?card_number={card_number}&amount={amount}",
        "payme": f"https://checkout.paycom.uz/card-to-card?to={card_number}&amount={amount * 100}",
        "uzum":  f"https://uzumbank.uz/transfer?card={card_number}&amount={amount}",
    }
```

Bu havolalar **admin bildirishnomasiga** `InlineKeyboardButton(url=...)` sifatida qo'shiladi.

---

## 🌐 Web API Server (Mini App uchun)

Barcha API endpointlar `handlers/api.py` da joylashadi:

| Method | Endpoint | Tavsif |
|--------|----------|--------|
| GET | `/api/stats?admin_id=...` | Statistika |
| GET | `/api/payments?admin_id=...&status=...` | To'lovlar ro'yxati |
| POST | `/api/payments/action` | Tasdiqlash/Rad etish |
| GET | `/` | React Mini App `index.html` |

- Har bir so'rovda `admin_id` ni `config.ADMIN_IDS` bilan tekshir.
- CORS headerlarini barcha javoblarga qo'sh (`Access-Control-Allow-Origin: *`).

---

## 🛠 Audit Log (Har bir admin amali yozib boriladi)

Admin to'lovni tasdiqlaganda yoki rad etganda:
```python
await db.add_audit_log(
    admin_id=callback.from_user.id,
    action="approve_payment",  # yoki "reject_payment"
    target_id=request_id,
    details=f"Karta: {payment['card_number']}"
)
```

---

## 🚫 Qatʼiyan Man Etilgan Harakatlar

1. `bot.py` ga handler yozma — faqat import va ishga tushirish.
2. `.env` faylini o'chirma yoki o'zgartirma.
3. Hardcoded telefon raqami, token, UUID yozma — barchasi `config.py` orqali.
4. Handler ichida `time.sleep()` ishlatma — faqat `await asyncio.sleep()`.
5. `requests` kutubxonasini ishlatma — faqat `aiohttp` (asinxron).
6. Bir handler faylidan boshqa handler faylini import qilma.
7. Foydalanuvchiga Python exception xabarini ko'rsatma.
8. `print()` ni log uchun ishlatma — faqat `logger.info/warning/error/exception()`.

---

## ✅ Kod Yozishdan Oldin Cheklov Ro'yxati (Pre-coding Checklist)

Har qanday o'zgartirish kiritishdan avval o'zingizga savol bering:

- [ ] Bu funksiya to'g'ri faylda joylashganmi? (Circular import yo'qmi?)
- [ ] Barcha foydalanuvchi kiritmalari validated bo'ldimi?
- [ ] Maxfiy ma'lumotlar hardcode qilinmadimi?
- [ ] Barcha DB so'rovlar `async/await` bilan yozildimi?
- [ ] Xato holatida foydalanuvchiga toza xabar berilyadimi?
- [ ] Admin amali `audit_logs` ga yozilyadimi?
- [ ] Kod PEP 8 standartiga muvofiqmi? (Type hints, docstrings)
- [ ] `python -m py_compile` xatosiz o'tdi?
