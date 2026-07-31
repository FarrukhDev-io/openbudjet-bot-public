import asyncio
import os
import sys
from dotenv import load_dotenv

# Loyiha root papkasini importlar uchun qo'shish
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db

async def make_test_user():
    print("PostgreSQL connection pool ishga tushmoqda...")
    await db.init_db_pool()
    await db.init_db()

    test_tg_id = 991729905  # Sizning Telegram ID (SUPER_ADMIN_ID)
    test_phone = "998991234567"
    test_name = "Farrukh (Test Admin)"

    print(f"\nID: {test_tg_id} bo'yicha test foydalanuvchisi sozlanmoqda...")

    async with db.get_conn() as conn:
        # 1. Foydalanuvchini qo'shish yoki yangilash
        await conn.execute("""
            INSERT INTO users (tg_id, username, full_name, phone, voted, balance)
            VALUES ($1, $2, $3, $4, 1, 15000)
            ON CONFLICT (tg_id) 
            DO UPDATE SET voted = 1, balance = 15000, phone = $4
        """, test_tg_id, "farrukh", test_name, test_phone)

        # 2. votes jadvaliga ovoz qo'shish (agar bo'lmasa)
        await conn.execute("""
            INSERT INTO votes (tg_id, phone, confirmed)
            VALUES ($1, $2, 0)
            ON CONFLICT (phone) DO NOTHING
        """, test_tg_id, test_phone)

        # 3. Kutilayotgan eski to'lov so'rovlarini tozalash (toza test uchun)
        await conn.execute("""
            DELETE FROM payment_requests WHERE tg_id = $1 AND status = 'pending'
        """, test_tg_id)

    print("✅ Test foydalanuvchisi muvaffaqiyatli sozlandi!")
    print(f"  - Telegram ID: {test_tg_id}")
    # Fetch current state from DB
    user_state = await db.get_user(test_tg_id)
    balance = await db.get_balance(test_tg_id)
    print(f"  - Balans: {balance:,} so'm")
    print(f"  - Ovoz bergan statusi: {user_state.get('voted')}")
    print(f"  - Telefon: {user_state.get('phone')}")
    print("\nEndi Telegram botga kirib «💰 Balansim» tugmasini bosib test qilishingiz mumkin! 🚀")

    await db.close_db_pool()

if __name__ == "__main__":
    asyncio.run(make_test_user())
