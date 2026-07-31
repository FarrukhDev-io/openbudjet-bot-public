import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import database as db
import keyboards as kb
import utils
from utils.helpers import is_admin


logger = logging.getLogger(__name__)
router = Router()


class AdminState(StatesGroup):
    waiting_reject_note = State()



async def notify_admins(bot: types.Bot, text: str, reply_markup=None) -> None:
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning("Admin %d ga xabar yuborilmadi: %s", admin_id, e)


@router.message(F.text == "⚙️ Admin panel")
async def cmd_admin_panel(message: types.Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yo'q.")
        return
    await state.clear()
    await message.answer(
        "⚙️ <b>Admin panel</b>\n\nXush kelibsiz!",
        reply_markup=kb.admin_main_keyboard(),
    )


@router.message(Command("admin"))
async def cmd_admin_command(message: types.Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yo'q.")
        return
    await state.clear()
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_main_keyboard())


@router.message(F.text == "📊 Statistika")
async def admin_stats(message: types.Message) -> None:
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
        reply_markup=kb.admin_main_keyboard(),
    )


@router.message(F.text == "📋 Ovozlar ro'yxati")
async def admin_votes_list(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    votes = await db.get_votes_list(limit=20, offset=0)
    if not votes:
        await message.answer("📭 Hozircha ovozlar yo'q.", reply_markup=kb.admin_main_keyboard())
        return

    lines = ["📋 <b>So'nggi 20 ovoz:</b>\n"]
    for v in votes:
        username = f"@{v['username']}" if v.get("username") else v.get("full_name", "—")
        confirmed = "✅" if v["confirmed"] else "⏳"
        lines.append(
            f"{confirmed} #{v['id']} | {username}\n"
            f"   📞 +{v['phone']} | 🕐 {v['voted_at'][:16]}"
        )
    await message.answer("\n".join(lines), reply_markup=kb.admin_main_keyboard())


@router.message(F.text == "💳 Kutayotgan to'lovlar")
async def admin_pending_payments(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    payments = await db.get_pending_payments()
    if not payments:
        await message.answer("✅ Kutayotgan to'lovlar yo'q.", reply_markup=kb.admin_main_keyboard())
        return

    await message.answer(
        f"💳 <b>Kutayotgan to'lovlar: {len(payments)} ta</b>",
        reply_markup=kb.admin_main_keyboard(),
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
        await message.answer(text, reply_markup=kb.payment_action_keyboard(p["id"], p["card_number"], p["amount"]))


@router.message(F.text == "✅ To'langan to'lovlar")
async def admin_paid_payments(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    payments = await db.get_all_payments(status="paid", limit=20)
    if not payments:
        await message.answer("📭 To'langan to'lovlar yo'q.", reply_markup=kb.admin_main_keyboard())
        return

    lines = [f"✅ <b>To'langan to'lovlar ({len(payments)} ta):</b>\n"]
    for p in payments:
        username = f"@{p['username']}" if p.get("username") else p.get("full_name") or "—"
        lines.append(
            f"#{p['id']} | {username}\n"
            f"   💳 {utils.mask_card(p['card_number'])} | {p['processed_at'][:16] if p['processed_at'] else '—'}"
        )
    await message.answer("\n".join(lines), reply_markup=kb.admin_main_keyboard())


@router.message(F.text == "👥 Top referrallar")
async def admin_top_referrers(message: types.Message) -> None:
    if not is_admin(message.from_user.id):
        return
    top = await db.get_top_referrers(limit=10)
    if not top:
        await message.answer("📭 Referrallar yo'q.", reply_markup=kb.admin_main_keyboard())
        return

    lines = ["👥 <b>Top referrallar:</b>\n"]
    for i, r in enumerate(top, 1):
        username = f"@{r['username']}" if r.get("username") else r.get("full_name") or "—"
        lines.append(
            f"{i}. {username}\n"
            f"   👤 {r['total']} taklif | ✅ {r['voted_count'] or 0} ovoz bergan"
        )
    await message.answer("\n".join(lines), reply_markup=kb.admin_main_keyboard())


@router.message(F.text == "🔍 Foydalanuvchi qidirish")
async def admin_search_prompt(message: types.Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔍 Telefon raqami, Telegram ID, ism yoki foydalanuvchi nomini kiriting:",
        reply_markup=kb.cancel_keyboard(),
    )
    await state.set_state(AdminState.waiting_reject_note)
    await state.update_data(search_mode=True)


@router.callback_query(F.data.startswith("pay_confirm_"))
async def callback_pay_confirm(callback: types.CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment = await db.get_payment_request(request_id)

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
        current_balance = await db.get_balance(payment["tg_id"])
        await callback.bot.send_message(
            payment["tg_id"],
            f"🎉 <b>To'lovingiz amalga oshirildi!</b>\n\n"
            f"💰 <b>{payment['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
            f"💳 Karta: <code>{utils.mask_card(payment['card_number'])}</code>\n\n"
            f"📊 Joriy balans: <b>{current_balance:,} so'm</b>\n\n"
            "🙏 Ovoz berganligi uchun rahmat!\n"
            "Do'stlaringizni ham taklif qiling 👥",
        )
    except Exception as e:
        logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)


@router.callback_query(F.data.startswith("pay_reject_"))
async def callback_pay_reject(callback: types.CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[-1])
    payment = await db.get_payment_request(request_id)

    if not payment:
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    if payment["status"] != "pending":
        await callback.answer(f"ℹ️ Allaqachon: {payment['status']}", show_alert=True)
        return

    await state.set_state(AdminState.waiting_reject_note)
    await state.update_data(
        reject_request_id=request_id,
        admin_msg_id=callback.message.message_id,
        admin_chat_id=callback.message.chat.id,
        admin_msg_text=callback.message.text,
        search_mode=False
    )

    await callback.message.answer(
        f"✍️ <b>So'rov #{request_id} uchun rad etish sababini yozing:</b>\n"
        f"(Ushbu xabar foydalanuvchiga yuboriladi)",
        reply_markup=kb.cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminState.waiting_reject_note)
async def process_admin_waiting_note(message: types.Message, state: FSMContext) -> None:
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("⚙️ Admin panel", reply_markup=kb.admin_main_keyboard())
        return

    data = await state.get_data()
    search_mode = data.get("search_mode", False)

    if search_mode:
        query = message.text.strip()
        users = await db.search_users(query)
        if not users:
            await message.answer("🔍 Hech qanday foydalanuvchi topilmadi.", reply_markup=kb.admin_main_keyboard())
            await state.clear()
            return

        lines = [f"🔍 Qidiruv natijalari ({len(users)} ta):\n"]
        for u in users:
            username_str = f"@{u['username']}" if u['username'] else "yo'q"
            phone_str = f"+{u['phone']}" if u['phone'] else "kiritilmagan"
            voted_str = "✅ Ovoz bergan" if u['voted'] else "❌ Ovoz bermagan"
            confirmed_str = "tasdiqlangan" if u['vote_confirmed'] else "kutilmoqda"
            lines.append(
                f"👤 {u['full_name']} | ID: <code>{u['tg_id']}</code>\n"
                f"   Username: {username_str} | Tel: {phone_str}\n"
                f"   Holat: {voted_str} ({confirmed_str})\n"
            )
        await message.answer("\n".join(lines), reply_markup=kb.admin_main_keyboard())
        await state.clear()
    else:
        reject_request_id = data.get("reject_request_id")
        if not reject_request_id:
            await message.answer("❌ Xatolik yuz berdi: So'rov ID topilmadi.", reply_markup=kb.admin_main_keyboard())
            await state.clear()
            return

        note = message.text.strip()
        payment = await db.get_payment_request(reject_request_id)
        if not payment:
            await message.answer("❌ So'rov topilmadi!", reply_markup=kb.admin_main_keyboard())
            await state.clear()
            return

        await db.update_payment_status(reject_request_id, "rejected", message.from_user.id, note)
        await db.add_balance(payment["tg_id"], payment["amount"])

        await message.answer(
            f"❌ <b>To'lov so'rovi #{reject_request_id} rad etildi va pul balansga qaytarildi.</b>\n"
            f"Eslatma: <i>{note}</i>",
            reply_markup=kb.admin_main_keyboard()
        )

        msg_id = data.get("admin_msg_id")
        chat_id = data.get("admin_chat_id")
        if msg_id and chat_id:
            try:
                original_text = data.get("admin_msg_text", "")
                await message.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=original_text + f"\n\n❌ <b>RAD ETILDI</b> — admin: {message.from_user.full_name}\nEslatma: <i>{note}</i>"
                )
            except Exception as e:
                logger.warning("Admin xabarini tahrirlashda xato: %s", e)

        try:
            await message.bot.send_message(
                payment["tg_id"],
                f"❌ <b>To'lov so'rovingiz rad etildi.</b>\n\n"
                f"📝 Sababi: {note}\n"
                f"💰 <b>{payment['amount']:,} so'm</b> balansingizga qaytarildi!\n\n"
                f"Muammo bo'lsa admin bilan bog'laning: {config.ADMIN_TELEGRAM}",
            )
        except Exception as e:
            logger.warning("Foydalanuvchiga xabar yuborilmadi: %s", e)

        await state.clear()
