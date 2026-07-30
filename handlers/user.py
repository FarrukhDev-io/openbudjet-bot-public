import logging
from datetime import date
import aiohttp
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import config
import database as db
import keyboards as kb
from utils.helpers import is_admin


logger = logging.getLogger(__name__)
router = Router()



def is_voting_period() -> bool:
    today = date.today()
    start = date.fromisoformat(config.VOTING_START)
    end = date.fromisoformat(config.VOTING_END)
    return start <= today <= end


def days_until_voting() -> int:
    today = date.today()
    start = date.fromisoformat(config.VOTING_START)
    return max(0, (start - today).days)


async def get_initiative_info(session: aiohttp.ClientSession) -> dict:
    async with session.get(config.INITIATIVE_URL_API) as resp:
        resp.raise_for_status()
        return await resp.json()


async def get_initiative_image(session: aiohttp.ClientSession, file_id: str) -> bytes:
    url = f"{config.FILE_URL}/{file_id}?type=LARGE"
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.read()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
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

    user_is_admin = is_admin(user.id)
    keyboard = kb.main_keyboard(is_user_admin=user_is_admin)

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
        reply_markup=keyboard,
    )


@router.message(F.text.in_({"🔙 Orqaga", "❌ Bekor qilish", "🏠 Bosh sahifa"}))
async def cmd_back(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏠 Bosh sahifa", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))


@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: types.Message) -> None:
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
        reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)),
    )


@router.message(F.text == "💰 Balansim")
async def cmd_balance(message: types.Message) -> None:
    user_id = message.from_user.id
    balance = await db.get_balance(user_id)
    payment = await db.get_user_payment(user_id)

    if payment:
        status_map = {
            "pending": "⏳ To'lov kutilmoqda",
            "paid": "✅ To'lov amalga oshirildi",
            "rejected": f"❌ Rad etildi: {payment.get('admin_note', '') or ''}",
        }
        payment_status = status_map.get(payment["status"], payment["status"])
        payment_text = (
            f"\n\n💳 <b>So'nggi to'lov:</b>\n"
            f"  Karta: <code>{payment['card_number'][:4]} **** **** {payment['card_number'][-4:]}</code>\n"
            f"  Holat: {payment_status}"
        )
    else:
        payment_text = "\n\n💳 Hali to'lov so'rovi yo'q"

    await message.answer(
        f"💰 <b>Hisobingiz</b>\n\n"
        f"📊 Joriy balans: <b>{balance:,} so'm</b>\n"
        f"🎁 Ovoz uchun mukofot: <b>{config.REWARD_AMOUNT:,} so'm</b>"
        f"{payment_text}",
        reply_markup=kb.main_keyboard(is_user_admin=is_admin(user_id)),
    )


@router.message(F.text == "📞 Bog'lanish")
async def cmd_contact(message: types.Message) -> None:
    admin_tg = config.ADMIN_TELEGRAM.lstrip("@")
    dev_tg = config.DEVELOPER_TELEGRAM.lstrip("@")
    await message.answer(
        "📞 <b>Asosiy bog'lanish va qo'llab-quvvatlash:</b>\n\n"
        "👤 <b>Mahalla Yoshlar Yetakchisi</b>\n"
        f"📱 Telefon: <a href='tel:{config.ADMIN_PHONE}'>{config.ADMIN_PHONE}</a>\n"
        f"💬 Telegram: <a href='https://t.me/{admin_tg}'>@{admin_tg}</a>\n\n"
        f"🌐 Loyiha havolasi: <a href='{config.INITIATIVE_URL}'>openbudget.uz</a>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🛠 <b>Dasturiy yordam va muallif:</b> <a href='https://t.me/{dev_tg}'>@{dev_tg}</a>",
        reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)),
    )


@router.message(F.text == "📋 Loyiha haqida")
async def cmd_initiative_info(message: types.Message, session: aiohttp.ClientSession) -> None:
    msg = await message.answer("⏳ Ma'lumot yuklanmoqda...")
    if not session:
        await msg.edit_text("❌ HTTP sessiyani yuklashda xatolik. Keyinroq qayta urinib ko'ring.")
        return

    try:
        info = await get_initiative_info(session)
        title = info.get("title") or "Attaron kishlog'ini asfaltlashtirish"
        description = info.get("description", "")
        region = info.get("region_title", "")
        district = info.get("district_title", "")
        quarter = info.get("quarter_title", "")
        vote_count = info.get("vote_count", 0)
        category = info.get("category_title", "")
        images = info.get("images", [])

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
                await message.answer("👇", reply_markup=kb.initiative_inline_keyboard())
                return
            except Exception as img_err:
                logger.warning("Rasm yuklanmadi: %s", img_err)
        await message.answer(text, reply_markup=kb.initiative_inline_keyboard())
    except Exception as e:
        logger.exception("Initiative info error")
        await msg.edit_text(
            f"📌 <b>Loyiha:</b> Attaron kishlog'ini asfaltlashtirish\n"
            f"🔑 ID: <code>{config.INITIATIVE_PUB_ID}</code>\n"
            f"🌐 <a href='{config.INITIATIVE_URL}'>Saytda ko'rish</a>\n\n"
            f"❌ Ma'lumot yuklanmadi. Iltimos keyinroq qayta urinib ko'ring.",
            reply_markup=kb.initiative_inline_keyboard(),
        )


@router.message(F.text == "👥 Referral")
async def cmd_referral(message: types.Message) -> None:
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
        reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)),
    )
