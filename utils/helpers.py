"""
utils/helpers.py — Shared utility functions used across handlers.

Note: Bu faylga faqat handler'lar orasida umumiy ishlatiladigan
funksiyalarni qo'shing. Circular import oldini olish uchun bu fayl
faqat config dan import qiladi.
"""
import config


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin yoki super-admin ekanligini tekshiradi."""
    return user_id in config.ADMIN_IDS or user_id == config.SUPER_ADMIN_ID
