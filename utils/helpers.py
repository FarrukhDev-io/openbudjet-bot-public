import logging
from aiogram import Bot
import config

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin yoki super admin ekanligini tekshirish"""
    return user_id in config.ADMIN_IDS or user_id == config.SUPER_ADMIN_ID

async def notify_admins(bot: Bot, text: str, reply_markup=None) -> None:
    """Barcha adminlarga xabar yuborish"""
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception as e:
            logger.warning("Admin %d ga xabar yuborilmadi: %s", admin_id, e)
