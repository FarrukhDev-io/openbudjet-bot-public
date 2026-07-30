import config

def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin yoki super admin ekanligini tekshirish"""
    return user_id in config.ADMIN_IDS or user_id == config.SUPER_ADMIN_ID
