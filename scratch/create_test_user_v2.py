import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db

async def make_specific_test_user():
    await db.init_db_pool()
    await db.init_db()

    target_tg_id = 1533310103
    test_phone = "998909876543"
    test_name = "Test User (1533310103)"

    print(f"ID: {target_tg_id} bo'yicha foydalanuvchi PostgreSQL'da sozlanmoqda...")

    async with db.get_conn() as conn:
        # 1. Foydalanuvchini qo'shish yoki yangilash
        await conn.execute("""
            INSERT INTO users (tg_id, username, full_name, phone, voted, balance)
            VALUES ($1, $2, $3, $4, 1, 15000)
            ON CONFLICT (tg_id) 
            DO UPDATE SET voted = 1, balance = 15000, phone = $4
        """, target_tg_id, "test_user", test_name, test_phone)

        # 2. votes jadvaliga ovoz qo'shish (agar bo'lmasa)
        await conn.execute("""
            INSERT INTO votes (tg_id, phone, confirmed)
            VALUES ($1, $2, 0)
            ON CONFLICT (phone) DO NOTHING
        """, target_tg_id, test_phone)

        # 3. Kutilayotgan eski to'lov so'rovlarini tozalash
        await conn.execute("""
            DELETE FROM payment_requests WHERE tg_id = $1 AND status = 'pending'
        """, target_tg_id)

    print(f"✅ Test foydalanuvchisi sozlandi!")
    print(f"  - Telegram ID: {target_tg_id}")
    balance = await db.get_balance(target_tg_id)
    print(f"  - Balans: {balance:,} so'm")

    await db.close_db_pool()

if __name__ == "__main__":
    asyncio.run(make_specific_test_user())
