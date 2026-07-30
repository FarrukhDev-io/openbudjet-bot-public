"""
OpenBudget.uz Telegram Ovoz Berish Boti
========================================
- Ovoz berish (captcha + OTP)
- Admin panel (statistika, ovozlar, to'lovlar)
- Referral tizimi
- Karta raqami + to'lov tasdiqlash
"""

import asyncio
import base64
import logging
import os
import random

import aiohttp
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
# FOOTER
# ==============================================================================

# ==============================================================================
# MIDDLEWARE — (footer olib tashlandi)
# ==============================================================================

from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any

# ==============================================================================
# SOZLAMALAR
# ==============================================================================

TOKEN          = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "0"))
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))

INITIATIVE_UUID   = "49912c4c-d184-4112-81b4-9a809d841845"
INITIATIVE_PUB_ID = "055521975013"
INITIATIVE_URL    = f"https://openbudget.uz/boards/initiatives/initiative/55/{INITIATIVE_UUID}"

API_BASE           = "https://openbudget.uz/api"
CAPTCHA_URL        = f"{API_BASE}/v2/vote/captcha-2"
SEND_OTP_URL       = f"{API_BASE}/v1/login/send-otp"
VERIFY_OTP_URL     = f"{API_BASE}/v1/login/verify-otp"
INITIATIVE_URL_API = f"{API_BASE}/v1/initiatives/{INITIATIVE_UUID}"
FILE_URL           = f"{API_BASE}/v2/info/file"

VOTING_START  = "2026-08-22"
VOTING_END    = "2026-08-31"
REWARD_AMOUNT = 15_000  # so'm

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

# ==============================================================================
# ADMIN TEKSHIRISH
# ==============================================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

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
    waiting_reject_note = State()

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
    start = date.fromisoformat(VOTING_START)
    end   = date.fromisoformat(VOTING_END)
    return start <= today <= end


def days_until_voting() -> int:
    from datetime import date
    today = date.today()
    start = date.fromisoformat(VOTING_START)
    return max(0, (start - today).days)


def base64_to_bytes(b64_string: str) -> bytes:
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    return base64.b64decode(b64_string)


def mask_card(card: str) -> str:
    """Karta raqamini qisman yashirish: 8600 **** **** 1234"""
    digits = card.replace(" ", "").replace("-", "")
    if len(digits) >= 8:
        return f"{digits[:4]} **** **** {digits[-4:]}"
    return card


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
                    last_status = resp.status
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
    """Barcha adminlarga xabar yuborish (footer yo'q — bot.send_message ishlatiladi)"""
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

    # Foydalanuvchini DB ga qo'shish
    user = message.from_user
    ref_by = None

    # Referral parametrini tekshirish: /start ref_12345
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_by = int(args[1][4:])
        except ValueError:
            pass

    db.add_user(
        tg_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "",
        ref_by=ref_by,
    )
    if ref_by:
        db.add_referral(inviter_id=ref_by, invited_id=user.id)

    # Admin bo'lsa admin paneli tugmasini ko'rsatish
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
        "6️⃣ Karta raqamingizni kiriting — 15 000 so'm olasiz\n\n"
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
        f"🌐 Loyiha: <a href='{INITIATIVE_URL}'>openbudget.uz</a>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🛠 <b>Bot muallifi:</b> <a href='https://t.me/sadullaef_06'>@sadullaef_06</a>",
        reply_markup=main_keyboard(),
    )

# ==============================================================================
# LOYIHA HAQIDA
# ==============================================================================

@dp.message(F.text == "📋 Loyiha haqida")
async def cmd_initiative_info(message: types.Message):
    msg = await message.answer("⏳ Ma'lumot yuklanmoqda...")
    try:
        async with aiohttp.ClientSession() as session:
            info = await get_initiative_info(session)
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
                        img_bytes = await get_initiative_image(session, img_id)
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
    stats = db.get_referral_stats(message.from_user.id)

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
                f"📅 Boshlanishi: <b>22-avgust 2026</b>\n"
                f"📅 Tugashi: <b>31-avgust 2026</b>\n"
                f"⏱ Qoldi: <b>{days} kun</b>\n\n"
                "Sabr qiling, sizni xabardor qilamiz! 🔔",
                reply_markup=main_keyboard(),
            )
        else:
            await message.answer("🔴 <b>Ovoz berish davri tugagan.</b>", reply_markup=main_keyboard())
        return

    # Allaqachon ovoz berganmi?
    if db.has_voted(user.id):
        payment = db.get_user_payment(user.id)
        if payment:
            status_map = {
                "pending":  "⏳ Kutilmoqda — admin 4-6 soat ichida tasdiqlaydi",
                "paid":     "✅ To'lov tasdiqlandi va yuborildi!",
                "rejected": "❌ To'lov rad etildi. Admin bilan bog'laning.",
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
            "• <code>901234567</code> (9 raqam)\n"
            "• <code>998901234567</code> (12 raqam)\n\n"
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
        async with aiohttp.ClientSession() as session:
            captcha_data = await fetch_captcha(session)

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

    except aiohttp.ClientError as e:
        logger.error("Captcha error: %s", e)
        days = days_until_voting()
        msg_text = (
            f"⏳ Captcha hozir mavjud emas\n\nOvoz berish <b>22-avgustda</b> boshlanadi.\nQoldi: <b>{days} kun</b>"
            if days > 0 else "❌ Captcha serveri ishlamayapti. Keyinroq urinib ko'ring."
        )
        await status_msg.edit_text(msg_text, reply_markup=main_keyboard())
        await state.clear()
    except Exception as e:
        await status_msg.edit_text(f"❌ Xato: {e}\n/start", reply_markup=main_keyboard())
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
        async with aiohttp.ClientSession() as session:
            otp_data = await send_otp(session, phone_number, captcha_key, int(text))

        await state.update_data(otp_key=otp_data.get("otpKey", ""))
        retry_after = otp_data.get("retryAfter", 60)

        await status_msg.edit_text(
            f"✅ <b>SMS yuborildi!</b> +{phone_number}\n\n"
            f"📲 SMS kodni kiriting:\n"
            f"<i>(Qayta yuborish: {retry_after} soniyadan keyin)</i>",
        )
        await message.answer("SMS kodni kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(VoteState.waiting_for_otp)

    except ValueError as e:
        await status_msg.edit_text(f"❌ {e}\n\nQaytadan: /start", reply_markup=main_keyboard())
        await state.clear()
    except Exception as e:
        await status_msg.edit_text(f"❌ {e}\n/start", reply_markup=main_keyboard())
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
        async with aiohttp.ClientSession() as session:
            auth_data    = await verify_otp(session, phone_number, otp)
            access_token = auth_data.get("access_token")

            if not access_token:
                await status_msg.edit_text("❌ Token olinmadi. /start bosing.", reply_markup=main_keyboard())
                await state.clear()
                return

            await status_msg.edit_text("✅ Autentifikatsiya muvaffaqiyatli!\n⏳ Ovoz berilmoqda...")
            vote_result = await submit_vote(session, access_token, INITIATIVE_UUID)

        # DB ga saqlash
        db.add_vote(tg_id=message.from_user.id, phone=phone_number)
        db.set_user_phone(message.from_user.id, phone_number)
        logger.info("Ovoz berildi | tg_id=%d | phone=%s", message.from_user.id, phone_number)

        user = message.from_user
        await status_msg.edit_text(
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✅ <a href='{INITIATIVE_URL}'>Loyiha</a>ga ovoz muvaffaqiyatli berildi!\n\n"
            f"💰 <b>Mukofot: {REWARD_AMOUNT:,} so'm</b>\n\n"
            "💳 Pul olish uchun karta raqamingizni kiriting:\n"
            "<i>(16 ta raqam, bo'sh joylarsiz)</i>",
        )
        await message.answer("Karta raqamini kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(VoteState.waiting_for_card)

    except ValueError as e:
        await status_msg.edit_text(f"❌ {e}\n\n/start", reply_markup=main_keyboard())
        await state.clear()
    except Exception as e:
        logger.error("OTP/vote error: %s", e)
        await status_msg.edit_text(f"❌ Kutilmagan xato: {e}\n/start", reply_markup=main_keyboard())
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

    if not card.isdigit() or len(card) not in (16, 18):
        await message.answer(
            "❌ Karta raqami noto'g'ri!\n\n"
            "16 ta raqam kiriting (bo'sh joylarsiz):\n"
            "<i>Masalan: 8600123456789012</i>",
            reply_markup=cancel_keyboard(),
        )
        return

    user      = message.from_user
    db_user   = db.get_user(user.id)
    phone     = db_user.get("phone", "") if db_user else ""
    full_name = user.full_name or ""

    # DB ga saqlash
    request_id = db.add_payment_request(
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
        "Tasdiqlash <b>4–6 soat</b> vaqt olishi mumkin.\n\n"
        "✅ Tasdiqlanganda sizga xabar yuboriladi.",
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
# ADMIN PANEL
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


# ---------- STATISTIKA ----------

@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    stats = db.get_stats()
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


# ---------- OVOZLAR RO'YXATI ----------

@dp.message(F.text == "📋 Ovozlar ro'yxati")
async def admin_votes_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    votes = db.get_votes_list(limit=20, offset=0)
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


# ---------- KUTAYOTGAN TO'LOVLAR ----------

@dp.message(F.text == "💳 Kutayotgan to'lovlar")
async def admin_pending_payments(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    payments = db.get_pending_payments()
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


# ---------- TO'LANGAN TO'LOVLAR ----------

@dp.message(F.text == "✅ To'langan to'lovlar")
async def admin_paid_payments(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    payments = db.get_all_payments(status="paid", limit=20)
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


# ---------- TOP REFERRALLAR ----------

@dp.message(F.text == "👥 Top referrallar")
async def admin_top_referrers(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    top = db.get_top_referrers(limit=10)
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

# ---------- FOYDALANUVCHI QIDIRISH ----------

@dp.message(F.text == "🔍 Foydalanuvchi qidirish")
async def admin_search_prompt(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔍 Telefon raqami yoki Telegram ID kiriting:",
        reply_markup=cancel_keyboard(),
    )
    await state.set_state(AdminState.waiting_reject_note)
    await state.update_data(search_mode=True)


# ---------- TO'LOV TASDIQLASH (INLINE) ----------

@dp.callback_query(F.data.startswith("pay_confirm_"))
async def callback_pay_confirm(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment    = db.get_payment_request(request_id)

    if not payment:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(f"ℹ️ Allaqachon: {payment['status']}", show_alert=True)
        return

    db.update_payment_status(request_id, "paid", callback.from_user.id)

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>TO'LANDI</b> — admin: {callback.from_user.full_name}"
    )
    await callback.answer("✅ To'lov tasdiqlandi!")

    # Foydalanuvchiga xabar
    try:
        await callback.bot.send_message(
            payment["tg_id"],
            f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"💰 <b>{payment['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
            f"💳 Karta: <code>{mask_card(payment['card_number'])}</code>\n\n"
            f"🙏 Ovoz berganligi uchun rahmat!\n"
            f"Do'stlaringizni ham taklif qiling 👥",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)


@dp.callback_query(F.data.startswith("pay_reject_"))
async def callback_pay_reject(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment    = db.get_payment_request(request_id)

    if not payment:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(f"ℹ️ Allaqachon: {payment['status']}", show_alert=True)
        return

    db.update_payment_status(request_id, "rejected", callback.from_user.id)

    await callback.message.edit_text(
        callback.message.text + f"\n\n❌ <b>RAD ETILDI</b> — admin: {callback.from_user.full_name}"
    )
    await callback.answer("❌ Rad etildi.")

    # Foydalanuvchiga xabar
    try:
        await callback.bot.send_message(
            payment["tg_id"],
            f"❌ <b>To'lov so'rovingiz rad etildi.</b>\n\n"
            f"Muammo bo'lsa admin bilan bog'laning: @joshqinjumayev",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)


# ==============================================================================
# MAIN
# ==============================================================================

async def main():
    db.init_db()
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Bot ishga tushdi | Super admin: %d | Adminlar: %s", SUPER_ADMIN_ID, ADMIN_IDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
