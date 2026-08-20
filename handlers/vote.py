import logging
import asyncio
import aiohttp
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

import config
import keyboards as kb
import utils

logger = logging.getLogger(__name__)
router = Router()

from utils import check_rate_limit, fetch_captcha, send_otp, verify_otp, submit_vote
from utils.helpers import is_admin



class VoteState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_captcha = State()
    waiting_for_otp = State()
    waiting_for_card = State()



@router.callback_query(F.data == "start_vote")
async def callback_start_vote(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _begin_vote(callback.message, state, callback.from_user)


@router.message(F.text == "🗳 Ovoz berish")
async def cmd_vote(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await _begin_vote(message, state, message.from_user)


async def _begin_vote(message: types.Message, state: FSMContext, user: types.User) -> None:
    from handlers.user import is_voting_period, days_until_voting
    if not is_voting_period():
        days = days_until_voting()
        if days > 0:
            await message.answer(
                f"⏳ <b>Ovoz berish hali boshlanmagan!</b>\n\n"
                f"📅 Boshlanishi: <b>22-avgust 2026</b>\n"
                f"📅 Tugashi: <b>31-avgust 2026</b>\n"
                f"⏱ Qoldi: <b>{days} kun</b>\n\n"
                "Sabr qiling, sizni xabardor qilamiz! 🔔",
                reply_markup=kb.main_keyboard(is_user_admin=is_admin(user.id)),
            )
        else:
            await message.answer("🔴 <b>Ovoz berish davri tugagan.</b>", reply_markup=kb.main_keyboard(is_user_admin=is_admin(user.id)))
        return



    await message.answer(
        "📱 <b>Telefon raqamingizni ulashing</b> yoki qo'lda kiriting:\n\n"
        "<i>Format: 901234567 (9 xonali) yoki 998901234567</i>",
        reply_markup=kb.phone_keyboard(),
    )
    await state.set_state(VoteState.waiting_for_phone)


@router.message(VoteState.waiting_for_phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext, session: aiohttp.ClientSession) -> None:
    phone = utils.clean_phone_number(message.contact.phone_number)
    await _process_phone_number(message, state, phone, session)


@router.message(VoteState.waiting_for_phone, F.text)
async def process_phone_text(message: types.Message, state: FSMContext, session: aiohttp.ClientSession) -> None:
    if message.text in ("🔙 Orqaga", "❌ Bekor qilish"):
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        return

    phone = message.text.strip().replace("+", "").replace(" ", "").replace("-", "")
    if not phone.isdigit():
        await message.answer(
            "❌ Telefon raqami noto'g'ri! Faqat raqam kiriting.\n"
            "Masalan: <code>901234567</code>",
            reply_markup=kb.phone_keyboard(),
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
            reply_markup=kb.phone_keyboard(),
        )
        return
    await _process_phone_number(message, state, phone, session)


async def _process_phone_number(message: types.Message, state: FSMContext, phone: str, session: aiohttp.ClientSession) -> None:
    await state.update_data(phone_number=phone)
    status_msg = await message.answer(
        f"✅ Telefon: <code>+{phone}</code>\n\n⏳ Captcha yuklanmoqda...",
        reply_markup=ReplyKeyboardRemove(),
    )
    if not session:
        await status_msg.edit_text("❌ HTTP sessiya xatosi. /start bosing.")
        await state.clear()
        return

    try:
        captcha_data = await fetch_captcha(session)
        captcha_key = captcha_data.get("captchaKey") or captcha_data.get("captcha_key")
        captcha_image = captcha_data.get("image")

        if not captcha_key or not captcha_image:
            await status_msg.edit_text("❌ Captcha olishda xato yuz berdi. Iltimos, /start bosing.")
            await state.clear()
            return

        await state.update_data(captcha_key=captcha_key)
        # FIX (Roast R4): Offloading CPU-bound base64 decoding to a worker thread to protect async event loop
        image_bytes = await asyncio.to_thread(utils.base64_to_bytes, captcha_image)
        photo = types.BufferedInputFile(image_bytes, filename="captcha.jpg")

        await status_msg.delete()
        await message.answer_photo(
            photo=photo,
            caption=(
                "🔐 <b>Rasmda ko'rsatilgan hisob natijasini yozing:</b>\n\n"
                "<i>Bekor qilish: ❌ Bekor qilish</i>"
            ),
            reply_markup=kb.cancel_keyboard(),
        )
        await state.set_state(VoteState.waiting_for_captcha)

    except aiohttp.ClientError as e:
        logger.exception("Captcha client error")
        from handlers.user import days_until_voting
        days = days_until_voting()
        msg_text = (
            f"⏳ Captcha hozir mavjud emas\n\nOvoz berish <b>22-avgustda</b> boshlanadi.\nQoldi: <b>{days} kun</b>"
            if days > 0 else "❌ Captcha serveri ishlamayapti. Iltimos keyinroq qayta urinib ko'ring."
        )
        await status_msg.edit_text(msg_text, reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
    except Exception as e:
        logger.exception("Unexpected error in process_phone_number")
        await status_msg.edit_text("❌ Xato yuz berdi. Iltimos keyinroq urinib ko'ring.\n/start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()


# ==============================================================================
# OpenBudget API Client methods have been refactored into utils/openbudget.py
# for strict adherence to SRP (Single Responsibility Principle).
# ==============================================================================


@router.message(VoteState.waiting_for_captcha)
async def process_captcha(message: types.Message, state: FSMContext, session: aiohttp.ClientSession) -> None:
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        return

    text = message.text.strip() if message.text else ""
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return

    data = await state.get_data()
    phone_number = data["phone_number"]
    captcha_key = data["captcha_key"]
    status_msg = await message.answer("⏳ SMS yuborilmoqda...")

    if not session:
        await status_msg.edit_text("❌ Tizim sessiyasida xatolik. /start bosing.")
        await state.clear()
        return

    if not await check_rate_limit(phone_number, message.from_user.id):
        await status_msg.edit_text("❌ SMS yuborish limiti oshdi. 10 daqiqadan so'ng qayta urining.", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
        return

    try:
        otp_data = await send_otp(session, phone_number, captcha_key, int(text))
        await state.update_data(otp_key=otp_data.get("otpKey", ""))
        retry_after = otp_data.get("retryAfter", 60)

        await status_msg.edit_text(
            f"✅ <b>SMS yuborildi!</b> +{phone_number}\n\n"
            f"📲 SMS kodni kiriting:\n"
            f"<i>(Qayta yuborish: {retry_after} soniyadan keyin)</i>",
        )
        await message.answer("SMS kodni kiriting:", reply_markup=kb.cancel_keyboard())
        await state.set_state(VoteState.waiting_for_otp)

    except ValueError as e:
        logger.warning("Send OTP logic warning: %s", e)
        await status_msg.edit_text("❌ Kiritilgan ma'lumotlarda xatolik mavjud. Qaytadan boshlang: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
    except Exception as e:
        logger.exception("OTP error")
        await status_msg.edit_text("❌ Xizmatda kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()


@router.message(VoteState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext, session: aiohttp.ClientSession) -> None:
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("🏠 Bosh sahifa", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        return

    otp = message.text.strip() if message.text else ""
    if not otp.isdigit() or len(otp) < 4:
        await message.answer("❌ SMS kod noto'g'ri. Qaytadan kiriting:")
        return

    data = await state.get_data()
    phone_number = data["phone_number"]
    status_msg = await message.answer("⏳ Kod tekshirilmoqda...")

    if not session:
        await status_msg.edit_text("❌ Tizim xatosi. /start bosing.")
        await state.clear()
        return

    try:
        auth_data = await verify_otp(session, phone_number, otp)
        access_token = auth_data.get("access_token")

        if not access_token:
            await status_msg.edit_text("❌ Token olinmadi. /start bosing.", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
            await state.clear()
            return

        await status_msg.edit_text("✅ Autentifikatsiya muvaffaqiyatli!\n⏳ Ovoz berilmoqda...")
        await submit_vote(session, access_token, config.INITIATIVE_UUID)

        data = await state.get_data()
        ref_by = data.get("ref_by")

        await state.clear()

        # Send notification to the configured Telegram group (Only Phone & Username Format)
        user = message.from_user
        username_str = f"@{user.username}" if user.username else f"Ism: {user.full_name}"
        group_text = f"🗳 +{phone_number} | {username_str}"

        try:
            await message.bot.send_message(
                chat_id=config.GROUP_ID,
                text=group_text,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.exception("Guruhga xabar yuborishda xatolik yuz berdi: %s", e)

        # Notify the referrer
        if ref_by:
            try:
                await message.bot.send_message(
                    chat_id=ref_by,
                    text=(
                        f"🎉 Siz taklif qilgan do'stingiz muvaffaqiyatli ovoz berdi!\n"
                        "Taklif qilganingiz uchun rahmat! 🙏"
                    )
                )
            except Exception as ref_err:
                logger.warning("Inviter %d ga referral xabari yuborilmadi: %s", ref_by, ref_err)

        await status_msg.edit_text(
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Ovozingiz muvaffaqiyatli qabul qilindi. Ovoz berganingiz uchun rahmat! 🙏",
            reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id))
        )
    except ValueError as e:
        logger.warning("Verify OTP value warning: %s", e)
        await status_msg.edit_text("❌ Kiritilgan kod yoki ma'lumot xato. Qaytadan boshlang: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
    except Exception as e:
        logger.exception("Verify OTP runtime error")
        await status_msg.edit_text("❌ Ovoz berish jarayonida xatolik yuz berdi. Iltimos qaytadan urinib ko'ring: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
