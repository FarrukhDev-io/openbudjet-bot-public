from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import config


def main_keyboard(is_user_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🗳 Ovoz berish"),
        KeyboardButton(text="📋 Loyiha haqida"),
    )
    builder.row(
        KeyboardButton(text="💰 Balansim"),
        KeyboardButton(text="👥 Referral"),
    )
    builder.row(
        KeyboardButton(text="📞 Bog'lanish"),
        KeyboardButton(text="ℹ️ Yordam"),
    )
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
    builder.row(InlineKeyboardButton(text="🌐 Saytda ko'rish", url=config.INITIATIVE_URL))
    builder.row(InlineKeyboardButton(text="🗳 Ovoz berish", callback_data="start_vote"))
    return builder.as_markup()


def withdraw_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Pulni yechib olish", callback_data="request_withdraw"))
    return builder.as_markup()
