from datetime import datetime
from typing import Any, Dict, List, Optional
from database.connection import get_conn

# FIX (Roast R2): format_datetime_fields recursive helper was removed from models.py to prevent CPU bottlenecks.
# Datetime formatting is now delegated to the JSON serializer on the web API layer.


# ==============================================================================
# CONFIG
# ==============================================================================

async def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Konfiguratsiya qiymatini olish"""
    async with get_conn() as conn:
        val = await conn.fetchval("SELECT value FROM config WHERE key = $1", key)
        return val if val is not None else default


async def set_config(key: str, value: str) -> None:
    """Konfiguratsiya qiymatini saqlash/yangilash"""
    async with get_conn() as conn:
        await conn.execute(
            """INSERT INTO config (key, value) VALUES ($1, $2)
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
            key, value
        )


# ==============================================================================
# USERS
# ==============================================================================

async def add_user(tg_id: int, username: str, full_name: str, ref_by: Optional[int] = None) -> None:
    """Yangi foydalanuvchi qo'shish"""
    async with get_conn() as conn:
        await conn.execute("""
            INSERT INTO users (tg_id, username, full_name, ref_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (tg_id) DO NOTHING
        """, tg_id, username, full_name, ref_by)


async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchini ID bo'yicha olish"""
    async with get_conn() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE tg_id = $1", tg_id)
        return dict(row) if row else None


async def set_user_phone(tg_id: int, phone: str) -> None:
    """Foydalanuvchi telefon raqamini yangilash"""
    async with get_conn() as conn:
        await conn.execute("UPDATE users SET phone = $1 WHERE tg_id = $2", phone, tg_id)


async def set_user_voted(tg_id: int) -> None:
    """Foydalanuvchi ovoz berganligini belgilash"""
    async with get_conn() as conn:
        await conn.execute("UPDATE users SET voted = 1 WHERE tg_id = $1", tg_id)


async def set_vote_confirmed(tg_id: int) -> None:
    """Ovozni tasdiqlash va referrallarni yangilash"""
    async with get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute("UPDATE users SET vote_confirmed = 1 WHERE tg_id = $1", tg_id)
        await conn.execute(
            "UPDATE votes SET confirmed = 1, confirmed_at = $1 WHERE tg_id = $2 AND confirmed = 0",
            now, tg_id
        )
        await conn.execute(
            "UPDATE referrals SET invited_voted = 1 WHERE invited_id = $1",
            tg_id
        )


async def get_balance(tg_id: int) -> int:
    """Foydalanuvchi balansini olish"""
    async with get_conn() as conn:
        val = await conn.fetchval(
            "SELECT balance FROM users WHERE tg_id = $1", tg_id
        )
        return val or 0

async def add_balance(tg_id: int, amount: int) -> int:
    """Foydalanuvchi balansiga pul qo'shish, yangi balansni qaytaradi"""
    async with get_conn() as conn:
        new_balance = await conn.fetchval("""
            UPDATE users SET balance = balance + $1
            WHERE tg_id = $2
            RETURNING balance
        """, amount, tg_id)
        return new_balance or 0

async def deduct_balance(tg_id: int, amount: int) -> bool:
    """Balansdan pul ayirish. Yetarli bo'lmasa False qaytaradi"""
    async with get_conn() as conn:
        current = await conn.fetchval(
            "SELECT balance FROM users WHERE tg_id = $1", tg_id
        )
        if (current or 0) < amount:
            return False
        await conn.execute("""
            UPDATE users SET balance = balance - $1
            WHERE tg_id = $2
        """, amount, tg_id)
        return True


# ==============================================================================
# VOTES
# ==============================================================================

async def add_vote(tg_id: int, phone: str) -> None:
    """Ovoz yozuvini qo'shish"""
    async with get_conn() as conn:
        await conn.execute(
            "INSERT INTO votes (tg_id, phone) VALUES ($1, $2)",
            tg_id, phone
        )
        await conn.execute(
            "UPDATE users SET voted = 1, phone = $1 WHERE tg_id = $2",
            phone, tg_id
        )


async def get_vote(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchining so'nggi ovozini olish"""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM votes WHERE tg_id = $1 ORDER BY id DESC LIMIT 1", tg_id
        )
        return dict(row) if row else None


async def has_voted(tg_id: int) -> bool:
    """Foydalanuvchi ovoz berganligini tekshirish"""
    row = await get_vote(tg_id)
    return row is not None


# ==============================================================================
# PAYMENT REQUESTS
# ==============================================================================

async def add_payment_request(tg_id: int, phone: str, full_name: str, card_number: str, amount: int = 15000) -> int:
    """To'lov so'rovi qo'shish va yangi row ID sini qaytarish"""
    async with get_conn() as conn:
        row_id = await conn.fetchval(
            """INSERT INTO payment_requests (tg_id, phone, full_name, card_number, amount)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            tg_id, phone, full_name, card_number, amount
        )
        return row_id


async def get_payment_request(request_id: int) -> Optional[Dict[str, Any]]:
    """To'lov so'rovini ID bo'yicha olish"""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM payment_requests WHERE id = $1", request_id
        )
        return dict(row) if row else None


async def get_pending_payments() -> List[Dict[str, Any]]:
    """Kutilayotgan to'lovlarni olish"""
    async with get_conn() as conn:
        rows = await conn.fetch(
            "SELECT * FROM payment_requests WHERE status = 'pending' ORDER BY id DESC"
        )
        return [dict(r) for r in rows]


async def update_payment_status(request_id: int, status: str, admin_id: int, note: str = "") -> None:
    """To'lov statusini va admin eslatmasini yangilash"""
    async with get_conn() as conn:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute(
            """UPDATE payment_requests
               SET status = $1, processed_at = $2, processed_by = $3, admin_note = $4
               WHERE id = $5""",
            status, now, admin_id, note, request_id
        )
    await add_audit_log(admin_id, f"{status}_payment", request_id, f"Note: {note}")


async def get_user_payment(tg_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchining so'nggi to'lov so'rovini olish"""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM payment_requests WHERE tg_id = $1 ORDER BY id DESC LIMIT 1",
            tg_id
        )
        return dict(row) if row else None


async def create_withdrawal_request(tg_id: int, phone: str, full_name: str, card_number: str) -> Optional[int]:
    """
    FIX (Roast R3): Anti Double-Spending with Pessimistic Locking.
    Performs balance check, duplicate check, payment request creation, and balance deduction 
    inside a single atomic PostgreSQL transaction with SELECT FOR UPDATE row-level locking.
    """
    async with get_conn() as conn:
        async with conn.transaction():
            # 1. Lock the user row using SELECT FOR UPDATE to prevent race conditions
            row = await conn.fetchrow(
                "SELECT balance FROM users WHERE tg_id = $1 FOR UPDATE",
                tg_id
            )
            if not row:
                return None
            
            balance = row["balance"]
            if balance <= 0:
                return None
            
            # 2. Check if there is already a pending request to prevent duplicate submissions
            pending = await conn.fetchval(
                "SELECT id FROM payment_requests WHERE tg_id = $1 AND status = 'pending' FOR UPDATE",
                tg_id
            )
            if pending:
                return None

            # 3. Create the payment request
            request_id = await conn.fetchval(
                """INSERT INTO payment_requests (tg_id, phone, full_name, card_number, amount)
                   VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                tg_id, phone, full_name, card_number, balance
            )
            
            # 4. Deduct the user's balance
            await conn.execute(
                "UPDATE users SET balance = balance - $1 WHERE tg_id = $2",
                balance, tg_id
            )
            
            return request_id


# ==============================================================================
# REFERRALS
# ==============================================================================

async def add_referral(inviter_id: int, invited_id: int) -> None:
    """Referral qo'shish"""
    if inviter_id == invited_id:
        return
    async with get_conn() as conn:
        await conn.execute(
            """INSERT INTO referrals (inviter_id, invited_id) VALUES ($1, $2)
               ON CONFLICT (invited_id) DO NOTHING""",
            inviter_id, invited_id
        )


async def get_referral_stats(tg_id: int) -> Dict[str, int]:
    """Referral statistikasini olish"""
    async with get_conn() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM referrals WHERE inviter_id = $1", tg_id)
        voted = await conn.fetchval(
            "SELECT COUNT(*) FROM referrals WHERE inviter_id = $1 AND invited_voted = 1",
            tg_id
        )
        return {"total": total or 0, "voted": voted or 0}


def get_referral_link(tg_id: int, bot_username: str) -> str:
    """Referral havolasini olish (sinxron)"""
    return f"https://t.me/{bot_username}?start=ref_{tg_id}"


# ==============================================================================
# ADMIN STATISTIKA & SEARCH
# ==============================================================================

async def get_stats() -> Dict[str, Any]:
    """Jami bot statistikasini olish"""
    async with get_conn() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_votes = await conn.fetchval("SELECT COUNT(*) FROM votes")
        confirmed = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE confirmed = 1")
        today_votes = await conn.fetchval(
            "SELECT COUNT(*) FROM votes WHERE CAST(voted_at AS DATE) = CURRENT_DATE"
        )
        total_refs = await conn.fetchval("SELECT COUNT(*) FROM referrals")
        pending_pays = await conn.fetchval(
            "SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"
        )
        paid_count = await conn.fetchval(
            "SELECT COUNT(*) FROM payment_requests WHERE status = 'paid'"
        )
        total_paid_sum = await conn.fetchval(
            "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE status = 'paid'"
        )

        return {
            "total_users": total_users or 0,
            "total_votes": total_votes or 0,
            "confirmed": confirmed or 0,
            "today_votes": today_votes or 0,
            "total_refs": total_refs or 0,
            "pending_pays": pending_pays or 0,
            "paid_count": paid_count or 0,
            "total_paid_sum": total_paid_sum or 0,
        }


async def get_votes_list(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Ovozlar ro'yxatini olish"""
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT v.id, v.tg_id, v.phone, v.voted_at, v.confirmed,
                   u.username, u.full_name
            FROM votes v
            LEFT JOIN users u ON v.tg_id = u.tg_id
            ORDER BY v.id DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        return [dict(r) for r in rows]


async def get_top_referrers(limit: int = 10) -> List[Dict[str, Any]]:
    """Eng ko'p taklif qilganlarni olish"""
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT r.inviter_id, u.username, u.full_name,
                   COUNT(*) as total,
                   SUM(r.invited_voted) as voted_count
            FROM referrals r
            LEFT JOIN users u ON r.inviter_id = u.tg_id
            GROUP BY r.inviter_id, u.username, u.full_name
            ORDER BY voted_count DESC, total DESC
            LIMIT $1
        """, limit)
        return [dict(r) for r in rows]


async def get_all_payments(status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """To'lovlar ro'yxatini olish"""
    async with get_conn() as conn:
        if status:
            rows = await conn.fetch("""
                SELECT p.*, u.username, u.full_name as u_full_name
                FROM payment_requests p
                LEFT JOIN users u ON p.tg_id = u.tg_id
                WHERE p.status = $1
                ORDER BY p.id DESC LIMIT $2 OFFSET $3
            """, status, limit, offset)
        else:
            rows = await conn.fetch("""
                SELECT p.*, u.username, u.full_name as u_full_name
                FROM payment_requests p
                LEFT JOIN users u ON p.tg_id = u.tg_id
                ORDER BY p.id DESC LIMIT $1 OFFSET $2
            """, limit, offset)
        return [dict(r) for r in rows]


async def search_users(query: str) -> List[Dict[str, Any]]:
    """Foydalanuvchilarni qidirish"""
    async with get_conn() as conn:
        if query.isdigit():
            rows = await conn.fetch("""
                SELECT * FROM users 
                WHERE tg_id = $1 OR phone LIKE $2 OR phone LIKE $3
            """, int(query), f"%{query}%", f"%{query.strip('+')}%")
        else:
            rows = await conn.fetch("""
                SELECT * FROM users 
                WHERE username LIKE $1 OR full_name LIKE $2
            """, f"%{query}%", f"%{query}%")
        return [dict(r) for r in rows]


# ==============================================================================
# AUDIT LOGS
# ==============================================================================

async def add_audit_log(admin_id: int, action: str, target_id: Optional[int] = None, details: Optional[str] = None) -> None:
    """Audit log yozuvini qo'shish"""
    async with get_conn() as conn:
        await conn.execute(
            """INSERT INTO audit_logs (admin_id, action, target_id, details)
               VALUES ($1, $2, $3, $4)""",
            admin_id, action, target_id, details
        )
