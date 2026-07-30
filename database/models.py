from datetime import datetime
from typing import Any, Dict, List, Optional
from database.connection import get_conn


# ==============================================================================
# CONFIG
# ==============================================================================

async def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Konfiguratsiya qiymatini olish"""
    async with await get_conn() as conn:
        async with conn.execute("SELECT value FROM config WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["value"] if row else default


async def set_config(key: str, value: str) -> None:
    """Konfiguratsiya qiymatini saqlash/yangilash"""
    async with await get_conn() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
        await conn.commit()


# ==============================================================================
# USERS
# ==============================================================================

async def add_user(tg_id: int, username: str, full_name: str, ref_by: Optional[int] = None) -> None:
    """Yangi foydalanuvchi qo'shish"""
    async with await get_conn() as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO users (tg_id, username, full_name, ref_by)
            VALUES (?, ?, ?, ?)
        """, (tg_id, username, full_name, ref_by))
        await conn.commit()


async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchini ID bo'yicha olish"""
    async with await get_conn() as conn:
        async with conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_user_phone(tg_id: int, phone: str) -> None:
    """Foydalanuvchi telefon raqamini yangilash"""
    async with await get_conn() as conn:
        await conn.execute("UPDATE users SET phone = ? WHERE tg_id = ?", (phone, tg_id))
        await conn.commit()


async def set_user_voted(tg_id: int) -> None:
    """Foydalanuvchi ovoz berganligini belgilash"""
    async with await get_conn() as conn:
        await conn.execute("UPDATE users SET voted = 1 WHERE tg_id = ?", (tg_id,))
        await conn.commit()


async def set_vote_confirmed(tg_id: int) -> None:
    """Ovozni tasdiqlash va referrallarni yangilash"""
    async with await get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute("UPDATE users SET vote_confirmed = 1 WHERE tg_id = ?", (tg_id,))
        await conn.execute(
            "UPDATE votes SET confirmed = 1, confirmed_at = ? WHERE tg_id = ? AND confirmed = 0",
            (now, tg_id)
        )
        await conn.execute(
            "UPDATE referrals SET invited_voted = 1 WHERE invited_id = ?",
            (tg_id,)
        )
        await conn.commit()


# ==============================================================================
# VOTES
# ==============================================================================

async def add_vote(tg_id: int, phone: str) -> None:
    """Ovoz yozuvini qo'shish"""
    async with await get_conn() as conn:
        await conn.execute(
            "INSERT INTO votes (tg_id, phone) VALUES (?, ?)",
            (tg_id, phone)
        )
        await conn.execute(
            "UPDATE users SET voted = 1, phone = ? WHERE tg_id = ?",
            (phone, tg_id)
        )
        await conn.commit()


async def get_vote(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchining so'nggi ovozini olish"""
    async with await get_conn() as conn:
        async with conn.execute(
            "SELECT * FROM votes WHERE tg_id = ? ORDER BY id DESC LIMIT 1", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def has_voted(tg_id: int) -> bool:
    """Foydalanuvchi ovoz berganligini tekshirish"""
    row = await get_vote(tg_id)
    return row is not None


# ==============================================================================
# PAYMENT REQUESTS
# ==============================================================================

async def add_payment_request(tg_id: int, phone: str, full_name: str, card_number: str) -> int:
    """To'lov so'rovi qo'shish va yangi row ID sini qaytarish"""
    async with await get_conn() as conn:
        cursor = await conn.execute(
            """INSERT INTO payment_requests (tg_id, phone, full_name, card_number)
               VALUES (?, ?, ?, ?)""",
            (tg_id, phone, full_name, card_number)
        )
        row_id = cursor.lastrowid
        await conn.commit()
        return row_id


async def get_payment_request(request_id: int) -> Optional[Dict[str, Any]]:
    """To'lov so'rovini ID bo'yicha olish"""
    async with await get_conn() as conn:
        async with conn.execute(
            "SELECT * FROM payment_requests WHERE id = ?", (request_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_pending_payments() -> List[Dict[str, Any]]:
    """Kutilayotgan to'lovlarni olish"""
    async with await get_conn() as conn:
        async with conn.execute(
            "SELECT * FROM payment_requests WHERE status = 'pending' ORDER BY id DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def update_payment_status(request_id: int, status: str, admin_id: int, note: str = "") -> None:
    """To'lov statusini va admin eslatmasini yangilash"""
    async with await get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute(
            """UPDATE payment_requests
               SET status = ?, processed_at = ?, processed_by = ?, admin_note = ?
               WHERE id = ?""",
            (status, now, admin_id, note, request_id)
        )
        await conn.commit()


async def get_user_payment(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchining so'nggi to'lov so'rovini olish"""
    async with await get_conn() as conn:
        async with conn.execute(
            "SELECT * FROM payment_requests WHERE tg_id = ? ORDER BY id DESC LIMIT 1",
            (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ==============================================================================
# REFERRALS
# ==============================================================================

async def add_referral(inviter_id: int, invited_id: int) -> None:
    """Referral qo'shish"""
    if inviter_id == invited_id:
        return
    async with await get_conn() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
            (inviter_id, invited_id)
        )
        await conn.commit()


async def get_referral_stats(tg_id: int) -> Dict[str, int]:
    """Referral statistikasini olish"""
    async with await get_conn() as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (tg_id,)
        ) as cursor:
            total = (await cursor.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM referrals WHERE inviter_id = ? AND invited_voted = 1",
            (tg_id,)
        ) as cursor:
            voted = (await cursor.fetchone())[0]
        return {"total": total, "voted": voted}


def get_referral_link(tg_id: int, bot_username: str) -> str:
    """Referral havolasini olish (sinxron)"""
    return f"https://t.me/{bot_username}?start=ref_{tg_id}"


# ==============================================================================
# ADMIN STATISTIKA & SEARCH
# ==============================================================================

async def get_stats() -> Dict[str, Any]:
    """Jami bot statistikasini olish"""
    async with await get_conn() as conn:
        async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM votes") as cursor:
            total_votes = (await cursor.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM votes WHERE confirmed = 1") as cursor:
            confirmed = (await cursor.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM votes WHERE date(voted_at) = date('now','localtime')"
        ) as cursor:
            today_votes = (await cursor.fetchone())[0]
        async with conn.execute("SELECT COUNT(*) FROM referrals") as cursor:
            total_refs = (await cursor.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"
        ) as cursor:
            pending_pays = (await cursor.fetchone())[0]
        async with conn.execute(
            "SELECT COUNT(*) FROM payment_requests WHERE status = 'paid'"
        ) as cursor:
            paid_count = (await cursor.fetchone())[0]
        async with conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payment_requests WHERE status = 'paid'"
        ) as cursor:
            total_paid_sum = (await cursor.fetchone())[0]

        return {
            "total_users": total_users,
            "total_votes": total_votes,
            "confirmed": confirmed,
            "today_votes": today_votes,
            "total_refs": total_refs,
            "pending_pays": pending_pays,
            "paid_count": paid_count,
            "total_paid_sum": total_paid_sum,
        }


async def get_votes_list(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Ovozlar ro'yxatini olish"""
    async with await get_conn() as conn:
        async with conn.execute("""
            SELECT v.id, v.tg_id, v.phone, v.voted_at, v.confirmed,
                   u.username, u.full_name
            FROM votes v
            LEFT JOIN users u ON v.tg_id = u.tg_id
            ORDER BY v.id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_top_referrers(limit: int = 10) -> List[Dict[str, Any]]:
    """Eng ko'p taklif qilganlarni olish"""
    async with await get_conn() as conn:
        async with conn.execute("""
            SELECT r.inviter_id, u.username, u.full_name,
                   COUNT(*) as total,
                   SUM(r.invited_voted) as voted_count
            FROM referrals r
            LEFT JOIN users u ON r.inviter_id = u.tg_id
            GROUP BY r.inviter_id
            ORDER BY voted_count DESC, total DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_all_payments(status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """To'lovlar ro'yxatini olish"""
    async with await get_conn() as conn:
        if status:
            async with conn.execute("""
                SELECT p.*, u.username, u.full_name as u_full_name
                FROM payment_requests p
                LEFT JOIN users u ON p.tg_id = u.tg_id
                WHERE p.status = ?
                ORDER BY p.id DESC LIMIT ? OFFSET ?
            """, (status, limit, offset)) as cursor:
                rows = await cursor.fetchall()
        else:
            async with conn.execute("""
                SELECT p.*, u.username, u.full_name as u_full_name
                FROM payment_requests p
                LEFT JOIN users u ON p.tg_id = u.tg_id
                ORDER BY p.id DESC LIMIT ? OFFSET ?
            """, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def search_users(query: str) -> List[Dict[str, Any]]:
    """Foydalanuvchilarni qidirish"""
    async with await get_conn() as conn:
        if query.isdigit():
            async with conn.execute("""
                SELECT * FROM users 
                WHERE tg_id = ? OR phone LIKE ? OR phone LIKE ?
            """, (int(query), f"%{query}%", f"%{query.strip('+')}%")) as cursor:
                rows = await cursor.fetchall()
        else:
            async with conn.execute("""
                SELECT * FROM users 
                WHERE username LIKE ? OR full_name LIKE ?
            """, (f"%{query}%", f"%{query}%")) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]
