"""
OpenBudget.uz Telegram Ovoz Berish Boti & Web API Server
======================================================
- Ovoz berish (captcha + OTP)
- Admin panel (statistika, ovozlar, to'lovlar)
- Web API Server for Telegram Mini App
- Referral tizimi
- Karta raqami + to'lov tasdiqlash
"""

import asyncio
import base64
import logging
import os
import random
from typing import Any, Awaitable, Callable

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from dotenv import load_dotenv

import database as db

load_dotenv()

# ==============================================================================
# SOZLAMALAR
# ==============================================================================

TOKEN          = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))

INITIATIVE_UUID   = os.getenv("INITIATIVE_UUID", "49912c4c-d184-4112-81b4-9a809d841845")
INITIATIVE_PUB_ID = os.getenv("INITIATIVE_PUB_ID", "055521975013")
INITIATIVE_URL    = f"https://openbudget.uz/boards/initiatives/initiative/55/{INITIATIVE_UUID}"

API_BASE           = "https://openbudget.uz/api"
CAPTCHA_URL        = f"{API_BASE}/v2/vote/captcha-2"
SEND_OTP_URL       = f"{API_BASE}/v1/login/send-otp"
VERIFY_OTP_URL     = f"{API_BASE}/v1/login/verify-otp"
INITIATIVE_URL_API = f"{API_BASE}/v1/initiatives/{INITIATIVE_UUID}"
FILE_URL           = f"{API_BASE}/v2/info/file"

VOTING_START  = os.getenv("VOTING_START", "2026-08-22")
VOTING_END    = os.getenv("VOTING_END", "2026-08-31")
REWARD_AMOUNT = int(os.getenv("REWARD_AMOUNT", "15000"))  # so'm

VOTE_URL: str | None = None
VOTE_CANDIDATES = [
    f"{API_BASE}/v2/vote/add",
    f"{API_BASE}/v1/vote/add",
    f"{API_BASE}/v2/vote",
    f"{API_BASE}/v1/vote",
    f"{API_BASE}/v2/initiatives/{INITIATIVE_UUID}/vote",
    f"{API_BASE}/v1/initiatives/{INITIATIVE_UUID}/vote",
    f"{API_BASE}/v2/boards/initiatives/vote",
    f"{API_BASE}/v1/boards/initiatives/vote",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global HTTP Session (startup'da ochiladi)
http_session: aiohttp.ClientSession | None = None

# ==============================================================================
# ADMIN TEKSHIRISH
# ==============================================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id == SUPER_ADMIN_ID

def is_super_admin(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID

# ==============================================================================
# FSM HOLATLARI
# ==============================================================================

class VoteState(StatesGroup):
    waiting_for_phone   = State()
    waiting_for_captcha = State()
    waiting_for_otp     = State()
    waiting_for_card    = State()

class AdminState(StatesGroup):
    waiting_reject_note = State()  # To'lovni rad etish sababini yozish uchun
    waiting_search_query = State()  # Foydalanuvchi qidirish uchun

# ==============================================================================
# KLAVIATURALAR
# ==============================================================================

def main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🗳 Ovoz berish"),
        KeyboardButton(text="📋 Loyiha haqida"),
    )
    builder.row(
        KeyboardButton(text="👥 Referral"),
        KeyboardButton(text="ℹ️ Yordam"),
    )
    builder.row(KeyboardButton(text="📞 Bog'lanish"))
    return builder.as_markup(resize_keyboard=True)


def phone_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True))
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def initiative_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🌐 Saytda ko'rish", url=INITIATIVE_URL))
    builder.row(InlineKeyboardButton(text="🗳 Ovoz berish", callback_data="start_vote"))
    return builder.as_markup()


def admin_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="📋 Ovozlar ro'yxati"),
    )
    builder.row(
        KeyboardButton(text="💳 Kutayotgan to'lovlar"),
        KeyboardButton(text="✅ To'langan to'lovlar"),
    )
    builder.row(
        KeyboardButton(text="👥 Top referrallar"),
        KeyboardButton(text="🔍 Foydalanuvchi qidirish"),
    )
    builder.row(KeyboardButton(text="🏠 Bosh sahifa"))
    return builder.as_markup(resize_keyboard=True)


def payment_action_keyboard(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ To'landi", callback_data=f"pay_confirm_{request_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{request_id}"),
    )
    return builder.as_markup()

# ==============================================================================
# YORDAMCHI FUNKSIYALAR
# ==============================================================================

def generate_captcha_header() -> str:
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


def is_voting_period() -> bool:
    from datetime import date
    today = date.today()
    try:
        start = date.fromisoformat(VOTING_START)
        end   = date.fromisoformat(VOTING_END)
        return start <= today <= end
    except Exception:
        return True # Default to True if date formatting fails


def days_until_voting() -> int:
    from datetime import date
    today = date.today()
    try:
        start = date.fromisoformat(VOTING_START)
        return max(0, (start - today).days)
    except Exception:
        return 0


def base64_to_bytes(b64_string: str) -> bytes:
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    return base64.b64decode(b64_string)


def mask_card(card: str) -> str:
    digits = card.replace(" ", "").replace("-", "")
    if len(digits) >= 8:
        return f"{digits[:4]} **** **** {digits[-4:]}"
    return card


def validate_card_luhn(card: str) -> bool:
    """Karta raqamini Luhn algoritmi bilan tekshirish"""
    digits = [int(d) for d in card if d.isdigit()]
    if len(digits) not in (16, 18):
        return False
    # Faqat Uzcard (8600) va Humo (9860) prefikslarini tekshirish
    prefix = "".join(map(str, digits[:4]))
    if prefix not in ("8600", "9860", "5614", "6262"): # Uzcard, Humo, va ba'zi cobadging prefikslar
        return False
        
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            double_digit = digit * 2
            if double_digit > 9:
                double_digit -= 9
            checksum += double_digit
        else:
            checksum += digit
    return checksum % 10 == 0


async def get_initiative_info(session: aiohttp.ClientSession) -> dict:
    async with session.get(INITIATIVE_URL_API) as resp:
        resp.raise_for_status()
        return await resp.json()


async def get_initiative_image(session: aiohttp.ClientSession, file_id: str) -> bytes:
    url = f"{FILE_URL}/{file_id}?type=LARGE"
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.read()


async def fetch_captcha(session: aiohttp.ClientSession) -> dict:
    last_error = None
    for attempt in range(1, 4):
        headers = {
            "Access-Captcha": generate_captcha_header(),
            "Accept": "application/json",
            "Origin": "https://openbudget.uz",
            "Referer": "https://openbudget.uz/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        try:
            async with session.get(CAPTCHA_URL, headers=headers) as resp:
                if resp.status == 500:
                    await asyncio.sleep(2 * attempt)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            last_error = e
            if e.status == 500:
                await asyncio.sleep(2 * attempt)
                continue
            raise
    raise aiohttp.ClientError("Captcha serveri hozir ishlamayapti.")


async def send_otp(session, phone_number, captcha_key, captcha_result) -> dict:
    if len(phone_number) == 9:
        phone_number = "998" + phone_number
    payload = {
        "phone_number": phone_number,
        "captcha_key": captcha_key,
        "captcha_result": captcha_result,
    }
    async with session.post(SEND_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def verify_otp(session, phone_number, otp) -> dict:
    payload = {"phone_number": phone_number, "otp": otp}
    async with session.post(VERIFY_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def submit_vote(session, access_token, initiative_uuid) -> dict:
    global VOTE_URL
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if VOTE_URL:
        payload = {"initiative_id": initiative_uuid}
        async with session.post(VOTE_URL, json=payload, headers=headers) as resp:
            data = await resp.json(content_type=None)
            if resp.status in (200, 201):
                return data
            raise ValueError(f"Vote xato ({resp.status}): {data.get('message', str(data))}")

    for url in VOTE_CANDIDATES:
        for payload in [
            {"initiative_id": initiative_uuid},
            {"id": initiative_uuid},
            {"uuid": initiative_uuid},
            {"initiative_uuid": initiative_uuid},
        ]:
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    try:
                        last_body = await resp.json(content_type=None)
                    except Exception:
                        last_body = {}
                    if resp.status == 404:
                        break
                    if resp.status in (200, 201):
                        VOTE_URL = url
                        return last_body
                    if resp.status == 401:
                        raise ValueError("Token yaroqsiz. /start bosing.")
                    if resp.status in (400, 422):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower():
                            VOTE_URL = url
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        continue
            except aiohttp.ClientConnectorError:
                continue
    raise ValueError(
        "⚠️ Ovoz berish endpointi aniqlanmadi.\n"
        "Ovoz berish davri (22-avgust) boshlanganida qaytadan urinib ko'ring."
    )


async def notify_admins(bot: Bot, text: str, reply_markup=None):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning("Admin %d ga xabar yuborilmadi: %s", admin_id, e)

# ==============================================================================
# DISPATCHER
# ==============================================================================

dp = Dispatcher(storage=MemoryStorage())

# ==============================================================================
# UMUMIY HANDLERLAR
# ==============================================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    ref_by = None

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_by = int(args[1][4:])
        except ValueError:
            pass

    await db.add_user(
        tg_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        ref_by=ref_by,
    )
    if ref_by:
        await db.add_referral(inviter_id=ref_by, invited_id=user.id)

    if is_admin(user.id):
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="🗳 Ovoz berish"),
            KeyboardButton(text="📋 Loyiha haqida"),
        )
        builder.row(
            KeyboardButton(text="👥 Referral"),
            KeyboardButton(text="ℹ️ Yordam"),
        )
        builder.row(
            KeyboardButton(text="📞 Bog'lanish"),
            KeyboardButton(text="⚙️ Admin panel"),
        )
        kb = builder.as_markup(resize_keyboard=True)
    else:
        kb = main_keyboard()

    if is_voting_period():
        period_text = "🟢 <b>Ovoz berish davri FAOL!</b>"
    else:
        days = days_until_voting()
        if days > 0:
            period_text = f"⏳ Ovoz berish boshlanishiga <b>{days} kun</b> qoldi (22-avgust)"
        else:
            period_text = "🔴 Ovoz berish davri tugagan"

    await message.answer(
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "🗳 <b>OpenBudget.uz Ovoz Berish Botiga xush kelibsiz!</b>\n\n"
        f"{period_text}\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=kb,
    )


@dp.message(F.text.in_({"🔙 Orqaga", "❌ Bekor qilish", "🏠 Bosh sahifa"}))
async def cmd_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh sahifa", reply_markup=main_keyboard())


@dp.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "Bu bot orqali OpenBudget.uz saytidagi loyihaga ovoz bera olasiz.\n\n"
        "<b>Qanday ishlaydi:</b>\n"
        "1️⃣ «🗳 Ovoz berish» tugmasini bosing\n"
        "2️⃣ Telefon raqamingizni ulashing\n"
        "3️⃣ Captcha rasmidagi javobni yozing\n"
        "4️⃣ Telefoningizga kelgan SMS kodni kiriting\n"
        "5️⃣ Ovoz berildi! ✅\n"
        "6️⃣ Karta raqamingizni kiriting — mukofot olasiz\n\n"
        "❓ Muammo bo'lsa: /start",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text == "📞 Bog'lanish")
async def cmd_contact(message: types.Message):
    await message.answer(
        "📞 <b>Bog'lanish</b>\n\n"
        "👤 <b>Romitan tuman Attaron mahalla yoshlar yetakchisi</b>\n"
        "📱 Telefon: <a href='tel:+998943238586'>+998 94 323 85 86</a>\n"
        "💬 Telegram: @joshqinjumayev\n\n"
        f"🌐 Loyiha: <a href='{INITIATIVE_URL}'>openbudget.uz</a>",
        reply_markup=main_keyboard(),
    )

# ==============================================================================
# LOYIHA HAQIDA
# ==============================================================================

@dp.message(F.text == "📋 Loyiha haqida")
async def cmd_initiative_info(message: types.Message):
    msg = await message.answer("⏳ Ma'lumot yuklanmoqda...")
    try:
        global http_session
        info = await get_initiative_info(http_session)
        title       = info.get("title") or "Attaron kishlog'ini asfaltlashtirish"
        description = info.get("description", "")
        region      = info.get("region_title", "")
        district    = info.get("district_title", "")
        quarter     = info.get("quarter_title", "")
        vote_count  = info.get("vote_count", 0)
        category    = info.get("category_title", "")
        images      = info.get("images", [])

        text = (
            f"📌 <b>{title}</b>\n\n"
            f"📍 <b>Joylashuv:</b> {region}, {district}, {quarter}\n"
            f"🏷 <b>Toifa:</b> {category}\n"
            f"🗳 <b>Ovozlar soni:</b> {vote_count}\n\n"
            f"📝 <b>Tavsif:</b> {description}"
        )
        await msg.delete()
        if images:
            try:
                media_group = []
                for i, img_id in enumerate(images[:2]):
                    img_bytes = await get_initiative_image(http_session, img_id)
                    photo = types.BufferedInputFile(img_bytes, filename=f"img_{i}.jpg")
                    if i == 0:
                        media_group.append(
                            types.InputMediaPhoto(media=photo, caption=text, parse_mode="HTML")
                        )
                    else:
                        media_group.append(types.InputMediaPhoto(media=photo))
                await message.answer_media_group(media=media_group)
                await message.answer("👇", reply_markup=initiative_inline_keyboard())
                return
            except Exception as img_err:
                logger.warning("Rasm yuklanmadi: %s", img_err)
        await message.answer(text, reply_markup=initiative_inline_keyboard())
    except Exception as e:
        logger.error("Initiative info error: %s", e)
        await msg.edit_text(
            f"📌 <b>Loyiha:</b> Attaron kishlog'ini asfaltlashtirish\n"
            f"🔑 ID: <code>{INITIATIVE_PUB_ID}</code>\n"
            f"🌐 <a href='{INITIATIVE_URL}'>Saytda ko'rish</a>\n\n"
            f"❌ Ma'lumot yuklanmadi: {e}",
            reply_markup=initiative_inline_keyboard(),
        )


# ==============================================================================
# REFERRAL
# ==============================================================================

@dp.message(F.text == "👥 Referral")
async def cmd_referral(message: types.Message):
    bot_info = await message.bot.get_me()
    link = db.get_referral_link(message.from_user.id, bot_info.username)
    stats = await db.get_referral_stats(message.from_user.id)

    await message.answer(
        "👥 <b>Referral tizimi</b>\n\n"
        f"Do'stlaringizni taklif qiling va statistikangizni kuzating!\n\n"
        f"📊 <b>Sizning statistikangiz:</b>\n"
        f"👤 Taklif qilganlar: <b>{stats['total']} kishi</b>\n"
        f"✅ Ovoz berganlar: <b>{stats['voted']} kishi</b>\n\n"
        f"🔗 <b>Sizning havolangiz:</b>\n"
        f"<code>{link}</code>\n\n"
        "Ushbu havolani do'stlaringizga yuboring!",
        reply_markup=main_keyboard(),
    )

# ==============================================================================
# OVOZ BERISH — BOSQICHLAR
# ==============================================================================

@dp.callback_query(F.data == "start_vote")
async def callback_start_vote(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await _begin_vote(callback.message, state, callback.from_user)


@dp.message(F.text == "🗳 Ovoz berish")
async def cmd_vote(message: types.Message, state: FSMContext):
    await state.clear()
    await _begin_vote(message, state, message.from_user)


async def _begin_vote(message: types.Message, state: FSMContext, user):
    if not is_voting_period():
        days = days_until_voting()
        if days > 0:
            await message.answer(
                f"⏳ <b>Ovoz berish hali boshlanmagan!</b>\n\n"
                f"📅 Boshlanishi: <b>{VOTING_START}</b>\n"
                f"📅 Tugashi: <b>{VOTING_END}</b>\n"
                f"⏱ Qoldi: <b>{days} kun</b>\n\n"
                "Sabr qiling, sizni xabardor qilamiz! 🔔",
                reply_markup=main_keyboard(),
            )
        else:
            await message.answer("🔴 <b>Ovoz berish davri tugagan.</b>", reply_markup=main_keyboard())
        return

    # Allaqachon ovoz berganmi?
    if await db.has_voted(user.id):
        payment = await db.get_user_payment(user.id)
        if payment:
            status_map = {
                "pending":  "⏳ Kutilmoqda — admin tasdiqlashi kutilmoqda.",
                "paid":     "✅ To'lov tasdiqlandi va yuborildi!",
                "rejected": f"❌ To'lov rad etildi. Sabab: {payment.get('admin_note', 'Noaniq')}",
            }
            status_text = status_map.get(payment["status"], payment["status"])
            await message.answer(
                f"✅ Siz allaqachon ovoz bergansiz!\n\n"
                f"💳 To'lov holati: {status_text}",
                reply_markup=main_keyboard(),
            )
        else:
            await message.answer(
                "✅ Siz allaqachon ovoz bergansiz!\n\n"
                "💳 Mukofot olish uchun karta raqamingizni kiriting:",
                reply_markup=cancel_keyboard(),
            )
            await state.set_state(VoteState.waiting_for_card)
        return

    await message.answer(
        "📱 <b>Telefon raqamingizni ulashing</b> yoki qo'lda kiriting:\n\n"
        "<i>Format: 998901234567</i>",
        reply_markup=phone_keyboard(),
    )
    await state.set_state(VoteState.waiting_for_phone)


# ---------- TELEFON ----------

@dp.message(VoteState.waiting_for_phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number.replace("+", "").replace(" ", "")
    if phone.startswith("7") and len(phone) == 11:
        phone = "998" + phone[2:]
    elif len(phone) == 9:
        phone = "998" + phone
    elif len(phone) == 10 and phone.startswith("0"):
        phone = "998" + phone[1:]
    elif not (len(phone) == 12 and phone.startswith("998")):
        if not phone.startswith("998"):
            phone = "998" + phone[-9:]
    await _process_phone_number(message, state, phone)


@dp.message(VoteState.waiting_for_phone, F.text)
async def process_phone_text(message: types.Message, state: FSMContext):
    if message.text in ("🔙 Orqaga", "❌ Bekor qilish"):
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=main_keyboard())
        return

    phone = message.text.strip().replace("+", "").replace(" ", "").replace("-", "")
    if not phone.isdigit():
        await message.answer(
            "❌ Telefon raqami noto'g'ri! Faqat raqam kiriting.\n"
            "Masalan: <code>901234567</code>",
            reply_markup=phone_keyboard(),
        )
        return

    if len(phone) == 9:
        phone = "998" + phone
    elif len(phone) == 10 and phone.startswith("0"):
        phone = "998" + phone[1:]
    elif len(phone) == 12 and phone.startswith("998"):
        pass
    else:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Qaytadan kiriting:",
            reply_markup=phone_keyboard(),
        )
        return
    await _process_phone_number(message, state, phone)

async def _process_phone_number(message: types.Message, state: FSMContext, phone: str):
    await state.update_data(phone_number=phone)
    status_msg = await message.answer(
        f"✅ Telefon: <code>+{phone}</code>\n\n⏳ Captcha yuklanmoqda...",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        global http_session
        captcha_data = await fetch_captcha(http_session)

        captcha_key   = captcha_data.get("captchaKey") or captcha_data.get("captcha_key")
        captcha_image = captcha_data.get("image")

        if not captcha_key or not captcha_image:
            await status_msg.edit_text("❌ Captcha olishda xato. /start bosing.")
            await state.clear()
            return

        await state.update_data(captcha_key=captcha_key)
        image_bytes = base64_to_bytes(captcha_image)
        photo = types.BufferedInputFile(image_bytes, filename="captcha.jpg")

        await status_msg.delete()
        await message.answer_photo(
            photo=photo,
            caption=(
                "🔐 <b>Rasmda ko'rsatilgan hisob natijasini yozing:</b>\n\n"
                "<i>Bekor qilish: ❌ Bekor qilish</i>"
            ),
            reply_markup=cancel_keyboard(),
        )
        await state.set_state(VoteState.waiting_for_captcha)

    except Exception as e:
        logger.error("Captcha error: %s", e)
        await status_msg.edit_text("❌ Captcha olishda xato yuz berdi. Iltimos qayta urinib ko'ring.", reply_markup=main_keyboard())
        await state.clear()


# ---------- CAPTCHA ----------

@dp.message(VoteState.waiting_for_captcha)
async def process_captcha(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=main_keyboard())
        return

    text = message.text.strip() if message.text else ""
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return

    data         = await state.get_data()
    phone_number = data["phone_number"]
    captcha_key  = data["captcha_key"]
    status_msg   = await message.answer("⏳ SMS yuborilmoqda...")

    try:
        global http_session
        otp_data = await send_otp(http_session, phone_number, captcha_key, int(text))

        await state.update_data(otp_key=otp_data.get("otpKey", ""))
        retry_after = otp_data.get("retryAfter", 60)

        await status_msg.edit_text(
            f"✅ <b>SMS yuborildi!</b> +{phone_number}\n\n"
            f"📲 SMS kodni kiriting:\n"
            f"<i>(Qayta yuborish: {retry_after} soniyadan keyin)</i>",
        )
        await message.answer("SMS kodni kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(VoteState.waiting_for_otp)

    except Exception as e:
        logger.error("Send OTP error: %s", e)
        await status_msg.edit_text("❌ SMS yuborishda xato. Captcha xato bo'lishi mumkin. Qaytadan /start bosing.", reply_markup=main_keyboard())
        await state.clear()


# ---------- OTP ----------

@dp.message(VoteState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=main_keyboard())
        return

    otp = message.text.strip() if message.text else ""
    if not otp.isdigit() or len(otp) < 4:
        await message.answer("❌ SMS kod noto'g'ri. Qaytadan kiriting:")
        return

    data         = await state.get_data()
    phone_number = data["phone_number"]
    status_msg   = await message.answer("⏳ Kod tekshirilmoqda...")

    try:
        global http_session
        auth_data    = await verify_otp(http_session, phone_number, otp)
        access_token = auth_data.get("access_token")

        if not access_token:
            await status_msg.edit_text("❌ Token olinmadi. /start bosing.", reply_markup=main_keyboard())
            await state.clear()
            return

        await status_msg.edit_text("✅ Tasdiqlandi!\n⏳ Ovoz berilmoqda...")
        await submit_vote(http_session, access_token, INITIATIVE_UUID)

        # DB ga saqlash
        await db.add_vote(tg_id=message.from_user.id, phone=phone_number)
        await db.set_user_phone(message.from_user.id, phone_number)
        
        # Taklif qilgan odam bo'lsa referral voted qilinadi
        user_db = await db.get_user(message.from_user.id)
        if user_db and user_db.get("ref_by"):
            await db.set_vote_confirmed(message.from_user.id)

        await status_msg.edit_text(
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✅ Loyihaga ovoz muvaffaqiyatli berildi!\n\n"
            f"💰 <b>Mukofot: {REWARD_AMOUNT:,} so'm</b>\n\n"
            "💳 Pul olish uchun karta raqamingizni kiriting:\n"
            "<i>(Uzcard yoki Humo: 16 ta raqam)</i>",
        )
        await message.answer("Karta raqamini kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(VoteState.waiting_for_card)

    except Exception as e:
        logger.error("OTP/vote error: %s", e)
        await status_msg.edit_text("❌ Xatolik yuz berdi. SMS kod xato yoki ovoz berish imkoni yo'q.", reply_markup=main_keyboard())
        await state.clear()

# ---------- KARTA RAQAMI ----------

@dp.message(VoteState.waiting_for_card)
async def process_card(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "⚠️ Karta raqami kiritilmadi.\n"
            "Keyinroq «🗳 Ovoz berish» tugmasini bosib karta raqamingizni kiritishingiz mumkin.",
            reply_markup=main_keyboard(),
        )
        return

    card = message.text.strip().replace(" ", "").replace("-", "") if message.text else ""

    if not validate_card_luhn(card):
        await message.answer(
            "❌ Karta raqami xato!\n\n"
            "Faqat to'g'ri Uzcard yoki Humo karta raqamini kiriting (8600 yoki 9860 bilan boshlanadi):",
            reply_markup=cancel_keyboard(),
        )
        return

    user      = message.from_user
    db_user   = await db.get_user(user.id)
    phone     = db_user.get("phone", "") if db_user else ""
    full_name = user.full_name or ""

    # DB ga saqlash
    request_id = await db.add_payment_request(
        tg_id=user.id,
        phone=phone,
        full_name=full_name,
        card_number=card,
    )

    await state.clear()

    await message.answer(
        f"✅ <b>Karta raqami qabul qilindi!</b>\n\n"
        f"💳 Karta: <code>{mask_card(card)}</code>\n"
        f"💰 Miqdor: <b>{REWARD_AMOUNT:,} so'm</b>\n\n"
        "⏳ <b>Admin tasdiqlashini kuting.</b>\n"
        "Tasdiqlanganda sizga xabar yuboriladi.",
        reply_markup=main_keyboard(),
    )

    # Adminlarga xabar
    username_str = f"@{user.username}" if user.username else "—"
    admin_text = (
        f"💳 <b>Yangi to'lov so'rovi #{request_id}</b>\n\n"
        f"👤 Ism: {full_name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {username_str}\n"
        f"📞 Telefon: +{phone}\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"💰 Miqdor: <b>{REWARD_AMOUNT:,} so'm</b>"
    )
    await notify_admins(
        message.bot,
        admin_text,
        reply_markup=payment_action_keyboard(request_id),
    )

# ==============================================================================
# ADMIN PANEL (BOT ICHIDAGI)
# ==============================================================================

@dp.message(F.text == "⚙️ Admin panel")
async def cmd_admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yo'q.")
        return
    await state.clear()
    await message.answer(
        "⚙️ <b>Admin panel</b>\n\nXush kelibsiz!",
        reply_markup=admin_main_keyboard(),
    )


@dp.message(Command("admin"))
async def cmd_admin_command(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yo'q.")
        return
    await state.clear()
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=admin_main_keyboard())


@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    stats = await db.get_stats()
    await message.answer(
        "📊 <b>Umumiy statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🗳 Jami ovozlar: <b>{stats['total_votes']}</b>\n"
        f"✅ Tasdiqlangan: <b>{stats['confirmed']}</b>\n"
        f"📅 Bugungi ovozlar: <b>{stats['today_votes']}</b>\n"
        f"👤 Referrallar: <b>{stats['total_refs']}</b>\n\n"
        f"💳 Kutayotgan to'lovlar: <b>{stats['pending_pays']}</b>\n"
        f"✅ To'langan: <b>{stats['paid_count']}</b>\n"
        f"💰 Jami to'langan: <b>{stats['total_paid_sum']:,} so'm</b>",
        reply_markup=admin_main_keyboard(),
    )


@dp.message(F.text == "📋 Ovozlar ro'yxati")
async def admin_votes_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    votes = await db.get_votes_list(limit=20, offset=0)
    if not votes:
        await message.answer("📭 Hozircha ovozlar yo'q.", reply_markup=admin_main_keyboard())
        return

    lines = ["📋 <b>So'nggi 20 ovoz:</b>\n"]
    for v in votes:
        username = f"@{v['username']}" if v.get("username") else v.get("full_name", "—")
        confirmed = "✅" if v["confirmed"] else "⏳"
        lines.append(
            f"{confirmed} #{v['id']} | {username}\n"
            f"   📞 +{v['phone']} | 🕐 {v['voted_at'][:16]}"
        )

    await message.answer("\n".join(lines), reply_markup=admin_main_keyboard())


@dp.message(F.text == "💳 Kutayotgan to'lovlar")
async def admin_pending_payments(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    payments = await db.get_pending_payments()
    if not payments:
        await message.answer("✅ Kutayotgan to'lovlar yo'q.", reply_markup=admin_main_keyboard())
        return

    await message.answer(
        f"💳 <b>Kutayotgan to'lovlar: {len(payments)} ta</b>",
        reply_markup=admin_main_keyboard(),
    )
    for p in payments:
        username = f"@{p['username']}" if p.get("username") else p.get("full_name") or "—"
        text = (
            f"💳 <b>So'rov #{p['id']}</b>\n"
            f"👤 {username}\n"
            f"📞 +{p['phone']}\n"
            f"💳 Karta: <code>{p['card_number']}</code>\n"
            f"💰 {p['amount']:,} so'm\n"
            f"🕐 {p['requested_at'][:16]}"
        )
        await message.answer(text, reply_markup=payment_action_keyboard(p["id"]))


@dp.message(F.text == "✅ To'langan to'lovlar")
async def admin_paid_payments(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    payments = await db.get_all_payments(status="paid", limit=20)
    if not payments:
        await message.answer("📭 To'langan to'lovlar yo'q.", reply_markup=admin_main_keyboard())
        return

    lines = [f"✅ <b>To'langan to'lovlar ({len(payments)} ta):</b>\n"]
    for p in payments:
        username = f"@{p['username']}" if p.get("username") else p.get("full_name") or "—"
        lines.append(
            f"#{p['id']} | {username}\n"
            f"   💳 {mask_card(p['card_number'])} | {p['processed_at'][:16] if p['processed_at'] else '—'}"
        )
    await message.answer("\n".join(lines), reply_markup=admin_main_keyboard())


@dp.message(F.text == "👥 Top referrallar")
async def admin_top_referrers(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    top = await db.get_top_referrers(limit=10)
    if not top:
        await message.answer("📭 Referrallar yo'q.", reply_markup=admin_main_keyboard())
        return

    lines = ["👥 <b>Top referrallar:</b>\n"]
    for i, r in enumerate(top, 1):
        username = f"@{r['username']}" if r.get("username") else r.get("full_name") or "—"
        lines.append(
            f"{i}. {username}\n"
            f"   👤 {r['total']} taklif | ✅ {r['voted_count'] or 0} ovoz bergan"
        )
    await message.answer("\n".join(lines), reply_markup=admin_main_keyboard())


@dp.message(F.text == "🔍 Foydalanuvchi qidirish")
async def admin_search_prompt(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔍 Foydalanuvchi qidirish uchun uning <b>Telegram ID</b> yoki <b>Telefon raqamini</b> kiriting:\n(Masalan: 998901234567)",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminState.waiting_search_query)


@dp.message(AdminState.waiting_search_query)
async def admin_search_process(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=admin_main_keyboard())
        return

    query = message.text.strip().replace("+", "")
    await state.clear()
    
    # Qidiruv ID yoki Telefon bo'yicha
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        if query.isdigit():
            cursor = await conn.execute(
                "SELECT * FROM users WHERE tg_id = ? OR phone LIKE ?", (query, f"%{query}")
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE username LIKE ? OR full_name LIKE ?", (f"%{query}%", f"%{query}%")
            )
        users = await cursor.fetchall()

    if not users:
        await message.answer("❌ Mos foydalanuvchi topilmadi.", reply_markup=admin_main_keyboard())
        return

    text_lines = []
    for u in users:
        voted_status = "✅ Ovoz bergan" if u["voted"] else "❌ Ovoz bermagan"
        username_str = f"@{u['username']}" if u['username'] else "—"
        text_lines.append(
            f"👤 <b>{u['full_name']}</b>\n"
            f"🆔 Telegram ID: <code>{u['tg_id']}</code>\n"
            f"📱 Username: {username_str}\n"
            f"📞 Telefon: +{u['phone'] or 'Kiritilmagan'}\n"
            f"🗳 Holati: {voted_status}\n"
            f"📅 Ro'yxatdan o'tdi: {u['joined_at'][:16]}\n"
            "━━━━━━━━━━━━━━━━━━"
        )
    
    await message.answer("\n".join(text_lines), reply_markup=admin_main_keyboard())

# ---------- TO'LOV TASDIQLASH (INLINE) ----------

@dp.callback_query(F.data.startswith("pay_confirm_"))
async def callback_pay_confirm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment    = await db.get_payment_request(request_id)

    if not payment:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(f"ℹ️ Allaqachon: {payment['status']}", show_alert=True)
        return

    await db.update_payment_status(request_id, "paid", callback.from_user.id)

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>TO'LANDI</b> — admin: {callback.from_user.full_name}"
    )
    await callback.answer("✅ To'lov tasdiqlandi!")

    try:
        await callback.bot.send_message(
            payment["tg_id"],
            f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"💰 <b>{payment['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
            f"💳 Karta: <code>{mask_card(payment['card_number'])}</code>\n\n"
            f"Ovoz berganingiz uchun rahmat! 🙏",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)


@dp.callback_query(F.data.startswith("pay_reject_"))
async def callback_pay_reject(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment    = await db.get_payment_request(request_id)

    if not payment:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(f"ℹ️ Allaqachon: {payment['status']}", show_alert=True)
        return

    # Admin keyingi yuboradigan xabarni rad etish sababi sifatida qabul qilamiz
    await state.set_state(AdminState.waiting_reject_note)
    await state.update_data(reject_req_id=request_id, reject_msg=callback.message)
    
    await callback.message.reply("❌ <b>Ushbu to'lovni rad etish sababini yozing:</b>", reply_markup=cancel_keyboard())
    await callback.answer()


@dp.message(AdminState.waiting_reject_note)
async def process_reject_note(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=admin_main_keyboard())
        return

    note = message.text.strip()
    state_data = await state.get_data()
    request_id = state_data["reject_req_id"]
    orig_msg = state_data["reject_msg"]
    
    await state.clear()

    payment = await db.get_payment_request(request_id)
    if not payment:
        await message.answer("❌ To'lov topilmadi.")
        return

    await db.update_payment_status(request_id, "rejected", message.from_user.id, note=note)

    await orig_msg.edit_text(
        orig_msg.text + f"\n\n❌ <b>RAD ETILDI</b>\nSabab: {note}\nAdmin: {message.from_user.full_name}"
    )
    await message.answer("❌ Rad etish tasdiqlandi va foydalanuvchiga xabar yuborildi.", reply_markup=admin_main_keyboard())

    try:
        await message.bot.send_message(
            payment["tg_id"],
            f"❌ <b>To'lov so'rovingiz rad etildi.</b>\n\n"
            f"📝 <b>Sabab:</b> {note}\n\n"
            f"Muammo bo'lsa admin bilan bog'laning: @joshqinjumayev",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)

# ==============================================================================
# WEB API SERVER FOR TELEGRAM MINI APP
# ==============================================================================

async def api_stats(request: web.Request) -> web.Response:
    if not is_admin(int(request.query.get("admin_id", 0))):
        return web.json_response({"error": "Unauthorized"}, status=401)
    stats = await db.get_stats()
    return web.json_response(stats, headers={"Access-Control-Allow-Origin": "*"})


async def api_payments(request: web.Request) -> web.Response:
    if not is_admin(int(request.query.get("admin_id", 0))):
        return web.json_response({"error": "Unauthorized"}, status=401)
    status = request.query.get("status") # pending, paid, rejected
    payments = await db.get_all_payments(status=status, limit=100)
    return web.json_response(payments, headers={"Access-Control-Allow-Origin": "*"})


async def api_payment_action(request: web.Request) -> web.Response:
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
        
    data = await request.json()
    admin_id = int(data.get("admin_id", 0))
    if not is_admin(admin_id):
        return web.json_response({"error": "Unauthorized"}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    req_id = int(data.get("id"))
    action = data.get("action") # paid or rejected
    note = data.get("note", "")

    payment = await db.get_payment_request(req_id)
    if not payment:
        return web.json_response({"error": "Payment request not found"}, status=404, headers={"Access-Control-Allow-Origin": "*"})

    await db.update_payment_status(req_id, action, admin_id, note)

    # Foydalanuvchiga Telegram xabar yuborish
    bot = request.app['bot']
    try:
        if action == "paid":
            await bot.send_message(
                payment["tg_id"],
                f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                f"💰 <b>{payment['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
                f"💳 Karta: <code>{mask_card(payment['card_number'])}</code>",
            )
        else:
            await bot.send_message(
                payment["tg_id"],
                f"❌ <b>To'lov so'rovingiz rad etildi.</b>\n\n"
                f"📝 <b>Sabab:</b> {note}",
            )
    except Exception as e:
        logger.warning("Foydalanuvchiga API orqali xabar ketmadi: %s", e)

    return web.json_response({"success": True}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })

# Web App serve index
async def api_index(request: web.Request) -> web.Response:
    index_path = os.path.join(os.path.dirname(__file__), "adminpanel-vite/dist/index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="Admin Panel Mini App dist folder not found. Please build front-end using: npm run build")


async def init_web_app(bot: Bot) -> web.Application:
    app = web.Application()
    app['bot'] = bot

    # CORS
    app.router.add_options('/{tail:.*}', handle_options)

    # API endpoints
    app.router.add_get('/api/stats', api_stats)
    app.router.add_get('/api/payments', api_payments)
    app.router.add_post('/api/payments/action', api_payment_action)

    # Static assets for React Mini App
    dist_dir = os.path.join(os.path.dirname(__file__), "adminpanel-vite/dist")
    if os.path.exists(dist_dir):
        app.router.add_static('/assets/', path=os.path.join(dist_dir, "assets"), name="assets")
    
    app.router.add_get('/', api_index)
    return app


async def start_web_server(bot: Bot):
    app = await init_web_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    # 8000 portda ishga tushirish (xostingda sozlash oson bo'ladi)
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logger.info("Web API Server 8000 portda ishga tushdi.")

# ==============================================================================
# MAIN
# ==============================================================================

import aiosqlite

async def main():
    await db.init_db()
    
    global http_session
    http_session = aiohttp.ClientSession()

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    
    # Web API Serverini background'da ishga tushirish
    asyncio.create_task(start_web_server(bot))
    
    logger.info("Bot ishga tushdi | Super admin: %d | Adminlar: %s", SUPER_ADMIN_ID, ADMIN_IDS)
    try:
        await dp.start_polling(bot)
    finally:
        await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
