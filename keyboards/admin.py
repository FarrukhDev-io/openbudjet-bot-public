from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import config


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
    builder.row(
        KeyboardButton(
            text="🖥 Admin Panel (Web App)",
            web_app=WebAppInfo(url=config.WEBAPP_URL)
        )
    )
    builder.row(KeyboardButton(text="🏠 Bosh sahifa"))
    return builder.as_markup(resize_keyboard=True)


def payment_action_keyboard(request_id: int, card_number: str, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    click_url = f"https://my.click.uz/services/p2p?card_number={card_number}&amount={amount}"
    payme_url = f"https://checkout.paycom.uz/card-to-card?to={card_number}&amount={amount * 100}"
    uzum_url = f"https://uzumbank.uz/transfer?card={card_number}&amount={amount}"
    
    builder.row(
        InlineKeyboardButton(text="Click P2P", url=click_url),
        InlineKeyboardButton(text="Payme P2P", url=payme_url),
        InlineKeyboardButton(text="Uzum P2P", url=uzum_url),
    )
    builder.row(
        InlineKeyboardButton(text="✅ To'landi", callback_data=f"pay_confirm_{request_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject_{request_id}"),
    )
    return builder.as_markup()
