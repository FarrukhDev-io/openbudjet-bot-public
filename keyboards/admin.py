from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


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
