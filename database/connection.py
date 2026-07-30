import os
import asyncpg
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/openbudget")

db_pool: Optional[asyncpg.Pool] = None


async def init_db_pool() -> None:
    """PostgreSQL ulanishlar pulini ishga tushirish"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(dsn=DATABASE_URL)


async def close_db_pool() -> None:
    """PostgreSQL ulanishlar pulini yopish"""
    global db_pool
    if db_pool is not None:
        await db_pool.close()
        db_pool = None


class AsyncConnectionContext:
    def __init__(self):
        self.conn = None

    async def __aenter__(self):
        global db_pool
        if db_pool is None:
            await init_db_pool()
        self.conn = await db_pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn and db_pool:
            await db_pool.release(self.conn)


def get_conn() -> AsyncConnectionContext:
    """Asinxron ma'lumotlar bazasi ulanishini context manager orqali olish"""
    return AsyncConnectionContext()


async def init_db() -> None:
    """Barcha jadvallarni yaratish (PostgreSQL)"""
    async with get_conn() as conn:
        # Foydalanuvchilar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                 SERIAL PRIMARY KEY,
                tg_id              BIGINT UNIQUE NOT NULL,
                username           VARCHAR(255),
                full_name          VARCHAR(255),
                phone              VARCHAR(50),
                ref_by             BIGINT,
                joined_at          VARCHAR(50) DEFAULT TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
                voted              INTEGER DEFAULT 0,
                vote_confirmed     INTEGER DEFAULT 0
            )
        """)

        # Ovozlar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id           SERIAL PRIMARY KEY,
                tg_id        BIGINT NOT NULL,
                phone        VARCHAR(50) NOT NULL,
                voted_at     VARCHAR(50) DEFAULT TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
                confirmed    INTEGER DEFAULT 0,
                confirmed_at VARCHAR(50)
            )
        """)

        # Referrallar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id             SERIAL PRIMARY KEY,
                inviter_id     BIGINT NOT NULL,
                invited_id     BIGINT NOT NULL UNIQUE,
                joined_at      VARCHAR(50) DEFAULT TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
                invited_voted  INTEGER DEFAULT 0
            )
        """)

        # To'lov so'rovlari (karta raqami)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_requests (
                id           SERIAL PRIMARY KEY,
                tg_id        BIGINT NOT NULL,
                phone        VARCHAR(50),
                full_name    VARCHAR(255),
                card_number  VARCHAR(50) NOT NULL,
                amount       INTEGER DEFAULT 15000,
                status       VARCHAR(50) DEFAULT 'pending',
                requested_at VARCHAR(50) DEFAULT TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'),
                processed_at VARCHAR(50),
                processed_by BIGINT,
                admin_note   TEXT
            )
        """)

        # Konfiguratsiya jadvali (VOTE_URL va boshqa sozlamalar uchun)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
        """)

        # Audit logs jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                action VARCHAR(255) NOT NULL,
                target_id INTEGER,
                details TEXT,
                timestamp VARCHAR(50) DEFAULT TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS')
            )
        """)

        # Unique indekslar
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_phone ON votes(phone)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_requests_phone ON payment_requests(phone)")
