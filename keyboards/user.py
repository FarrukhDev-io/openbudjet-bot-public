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


def vote_options_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⚡ Rasmiy Botda ovoz berish (Oson & Tez)",
            url=f"https://t.me/openbudget_official_2_bot?start={config.INITIATIVE_PUB_ID}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🌐 Saytda ko'rish va ovoz berish",
            url=config.INITIATIVE_URL
        )
    )
    return builder.as_markup()


def initiative_inline_keyboard() -> InlineKeyboardMarkup:
    return vote_options_keyboard()


def withdraw_inline_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Pulni yechib olish", callback_data="request_withdraw"))
    return builder.as_markup()



