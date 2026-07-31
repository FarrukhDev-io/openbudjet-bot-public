import logging
import asyncio
import aiohttp
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove

import config
import database as db
import keyboards as kb
import utils

logger = logging.getLogger(__name__)
router = Router()

from utils import check_rate_limit
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

    if await db.has_voted(user.id):
        payment = await db.get_user_payment(user.id)
        if payment:
            status_map = {
                "pending": "⏳ Kutilmoqda — admin 4-6 soat ichida tasdiqlaydi",
                "paid": "✅ To'lov tasdiqlandi va yuborildi!",
                "rejected": "❌ To'lov rad etildi. Admin bilan bog'laning.",
            }
            status_text = status_map.get(payment["status"], payment["status"])
            await message.answer(
                f"✅ Siz allaqachon ovoz bergansiz!\n\n"
                f"💳 To'lov holati: {status_text}",
                reply_markup=kb.main_keyboard(is_user_admin=is_admin(user.id)),
            )
        else:
            await message.answer(
                "✅ Siz allaqachon ovoz bergansiz!\n\n"
                "💳 Mukofot olish uchun karta raqamingizni kiriting:",
                reply_markup=kb.cancel_keyboard(),
            )
            await state.set_state(VoteState.waiting_for_card)
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
        image_bytes = utils.base64_to_bytes(captcha_image)
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


async def fetch_captcha(session: aiohttp.ClientSession) -> dict:
    for attempt in range(1, 4):
        headers = {
            "Access-Captcha": utils.generate_captcha_header(),
            "Accept": "application/json",
            "Origin": "https://openbudget.uz",
            "Referer": "https://openbudget.uz/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        try:
            async with session.get(config.CAPTCHA_URL, headers=headers) as resp:
                if resp.status == 500:
                    await asyncio.sleep(2 * attempt)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 500:
                await asyncio.sleep(2 * attempt)
                continue
            raise
    raise aiohttp.ClientError("Captcha serveri hozir ishlamayapti.")


async def send_otp(session: aiohttp.ClientSession, phone_number: str, captcha_key: str, captcha_result: int) -> dict:
    if len(phone_number) == 9:
        phone_number = "998" + phone_number
    payload = {
        "phone_number": phone_number,
        "captcha_key": captcha_key,
        "captcha_result": captcha_result,
    }
    async with session.post(config.SEND_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def verify_otp(session: aiohttp.ClientSession, phone_number: str, otp: str) -> dict:
    payload = {"phone_number": phone_number, "otp": otp}
    async with session.post(config.VERIFY_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def submit_vote(session: aiohttp.ClientSession, access_token: str, initiative_uuid: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    vote_url = await db.get_config("VOTE_URL")
    if vote_url:
        payload = {"initiative_id": initiative_uuid}
        async with session.post(vote_url, json=payload, headers=headers) as resp:
            try:
                data = await resp.json(content_type=None)
            except Exception:
                data = {}
            if resp.status in (200, 201):
                error_msg = data.get("message", "") if isinstance(data, dict) else ""
                if "already" in error_msg.lower() or "voted" in error_msg.lower() or data.get("status") == "ERROR":
                    raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                return data
            raise ValueError(f"Vote xato ({resp.status}): {data.get('message', str(data))}")

    for url in config.VOTE_CANDIDATES:
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
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower() or last_body.get("status") == "ERROR":
                            await db.set_config("VOTE_URL", url)
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        await db.set_config("VOTE_URL", url)
                        return last_body
                    if resp.status == 401:
                        raise ValueError("Token yaroqsiz. /start bosing.")
                    if resp.status in (400, 422):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower():
                            await db.set_config("VOTE_URL", url)
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        continue
            except aiohttp.ClientConnectorError:
                continue
    raise ValueError(
        "⚠️ Ovoz berish endpointi aniqlanmadi.\n"
        "Ovoz berish davri boshlanganida qaytadan urinib ko'ring."
    )


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

    if not check_rate_limit(phone_number, message.from_user.id):
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

        await db.add_vote(tg_id=message.from_user.id, phone=phone_number)
        await db.set_user_phone(message.from_user.id, phone_number)
        await db.add_balance(message.from_user.id, config.REWARD_AMOUNT)

        # Check for inviter and award referral bonus
        db_user = await db.get_user(message.from_user.id)
        if db_user and db_user.get("ref_by"):
            inviter_id = db_user["ref_by"]
            await db.add_balance(inviter_id, config.REFERRAL_REWARD)
            # Update referrals table
            async with db.get_conn() as conn:
                await conn.execute(
                    "UPDATE referrals SET invited_voted = 1 WHERE invited_id = $1",
                    message.from_user.id
                )
            try:
                await message.bot.send_message(
                    inviter_id,
                    f"🎉 Taklif qilgan do'stingiz +{phone_number} ovoz berdi!\n"
                    f"💰 Balansingizga <b>{config.REFERRAL_REWARD:,} so'm</b> bonus qo'shildi!"
                )
            except Exception as ref_err:
                logger.warning("Inviter %d ga xabar yuborilmadi: %s", inviter_id, ref_err)

        new_balance = await db.get_balance(message.from_user.id)
        logger.info("Ovoz berildi | tg_id=%d | phone=%s | new_balance=%d", message.from_user.id, phone_number, new_balance)

        await status_msg.edit_text(
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✅ <a href='{config.INITIATIVE_URL}'>Loyiha</a>ga ovoz muvaffaqiyatli berildi!\n\n"
            f"💰 <b>{config.REWARD_AMOUNT:,} so'm</b> hisobingizga qo'shildi!\n"
            f"📊 Joriy balansingiz: <b>{new_balance:,} so'm</b>\n\n"
            "💳 Pulni yechib olish uchun bosh sahifadagi <b>💰 Balansim</b> bo'limiga o'ting.",
            reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id))
        )
        await state.clear()

    except ValueError as e:
        logger.warning("Verify OTP value warning: %s", e)
        await status_msg.edit_text("❌ Kiritilgan kod yoki ma'lumot xato. Qaytadan boshlang: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()
    except Exception as e:
        logger.exception("Verify OTP runtime error")
        await status_msg.edit_text("❌ Ovoz berish jarayonida xatolik yuz berdi. Iltimos qaytadan urinib ko'ring: /start", reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)))
        await state.clear()


@router.message(VoteState.waiting_for_card)
async def process_card(message: types.Message, state: FSMContext) -> None:
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "🏠 Bosh sahifa",
            reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)),
        )
        return

    card = message.text.strip().replace(" ", "").replace("-", "") if message.text else ""

    if not utils.validate_uz_card(card):
        await message.answer(
            "❌ Karta raqami noto'g'ri yoki qo'llab-quvvatlanmaydi!\n"
            "Faqat 16 xonali Uzcard (8600...) yoki Humo (9860...) kartalarini kiriting:\n"
            "<i>Masalan: 8600123456789012</i>",
            reply_markup=kb.cancel_keyboard(),
        )
        return

    user = message.from_user
    db_user = await db.get_user(user.id)
    phone = db_user.get("phone", "") if db_user else ""
    full_name = user.full_name or ""
    balance = await db.get_balance(user.id)

    if balance <= 0:
        await state.clear()
        await message.answer(
            "❌ Balansingizda pul qolmagan yoki allaqachon to'lov so'rovi yuborilgan.",
            reply_markup=kb.main_keyboard(is_user_admin=is_admin(user.id))
        )
        return

    # Add payment request with the user's full balance
    request_id = await db.add_payment_request(
        tg_id=user.id,
        phone=phone,
        full_name=full_name,
        card_number=card,
        amount=balance
    )

    # Deduct balance immediately to prevent double spending
    await db.deduct_balance(user.id, balance)

    await state.clear()

    await message.answer(
        f"✅ <b>Karta raqami qabul qilindi!</b>\n\n"
        f"💳 Karta: <code>{utils.mask_card(card)}</code>\n"
        f"💰 Miqdor: <b>{balance:,} so'm</b>\n\n"
        "⏳ <b>Admin tasdiqlashini kuting.</b>\n"
        "Tasdiqlash <b>4–6 soat</b> vaqt olishi mumkin.\n\n"
        "✅ Tasdiqlanganda sizga xabar yuboriladi.",
        reply_markup=kb.main_keyboard(is_user_admin=is_admin(message.from_user.id)),
    )

    username_str = f"@{user.username}" if user.username else "—"
    admin_text = (
        f"💳 <b>Yangi to'lov so'rovi #{request_id}</b>\n\n"
        f"👤 Ism: {full_name}\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"📱 Username: {username_str}\n"
        f"📞 Telefon: +{phone}\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"💰 Miqdor: <b>{balance:,} so'm</b>"
    )
    # Import locally to avoid circular dependency
    from handlers.admin import notify_admins
    await notify_admins(
        message.bot,
        admin_text,
        reply_markup=kb.payment_action_keyboard(request_id, card, balance),
    )
