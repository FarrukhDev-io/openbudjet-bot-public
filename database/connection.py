import os
import asyncpg
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

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
    """Barcha jadvallarni yaratish va migratsiyalarni bajarish (PostgreSQL)"""
    async with get_conn() as conn:
        # 1. Foydalanuvchilar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                 SERIAL PRIMARY KEY,
                tg_id              BIGINT UNIQUE NOT NULL,
                username           VARCHAR(255),
                full_name          VARCHAR(255),
                phone              VARCHAR(50),
                ref_by             BIGINT,
                joined_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                voted              INTEGER DEFAULT 0,
                vote_confirmed     INTEGER DEFAULT 0,
                balance            BIGINT DEFAULT 0
            )
        """)

        # 2. Ovozlar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id           SERIAL PRIMARY KEY,
                tg_id        BIGINT NOT NULL,
                phone        VARCHAR(50) NOT NULL,
                voted_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed    INTEGER DEFAULT 0,
                confirmed_at TIMESTAMP
            )
        """)

        # 3. Referrallar jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id             SERIAL PRIMARY KEY,
                inviter_id     BIGINT NOT NULL,
                invited_id     BIGINT NOT NULL UNIQUE,
                joined_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                invited_voted  INTEGER DEFAULT 0
            )
        """)

        # 4. To'lov so'rovlari
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_requests (
                id           SERIAL PRIMARY KEY,
                tg_id        BIGINT NOT NULL,
                phone        VARCHAR(50),
                full_name    VARCHAR(255),
                card_number  VARCHAR(50) NOT NULL,
                amount       INTEGER DEFAULT 15000,
                status       VARCHAR(50) DEFAULT 'pending',
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by BIGINT,
                admin_note   TEXT
            )
        """)

        # 5. Konfiguratsiya jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   VARCHAR(255) PRIMARY KEY,
                value TEXT
            )
        """)

        # 6. Audit logs jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                action VARCHAR(255) NOT NULL,
                target_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. FSM Persistent Storage jadvali
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fsm_storage (
                chat_id    BIGINT NOT NULL,
                user_id    BIGINT NOT NULL,
                state      TEXT DEFAULT '',
                data       TEXT DEFAULT '{}',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)

        # ==============================================================================
        # MIGRATION: VARCHAR sanalarni native TIMESTAMP turiga o'tkazish (Ma'lumotlarni saqlagan holda)
        # ==============================================================================
        # Users migratsiyasi
        try:
            await conn.execute("ALTER TABLE users ALTER COLUMN joined_at TYPE TIMESTAMP USING joined_at::timestamp")
            await conn.execute("ALTER TABLE users ALTER COLUMN joined_at SET DEFAULT CURRENT_TIMESTAMP")
        except Exception:
            pass

        # Votes migratsiyasi
        try:
            await conn.execute("ALTER TABLE votes ALTER COLUMN voted_at TYPE TIMESTAMP USING voted_at::timestamp")
            await conn.execute("ALTER TABLE votes ALTER COLUMN voted_at SET DEFAULT CURRENT_TIMESTAMP")
            await conn.execute("ALTER TABLE votes ALTER COLUMN confirmed_at TYPE TIMESTAMP USING confirmed_at::timestamp")
        except Exception:
            pass

        # Referrals migratsiyasi
        try:
            await conn.execute("ALTER TABLE referrals ALTER COLUMN joined_at TYPE TIMESTAMP USING joined_at::timestamp")
            await conn.execute("ALTER TABLE referrals ALTER COLUMN joined_at SET DEFAULT CURRENT_TIMESTAMP")
        except Exception:
            pass

        # Payment Requests migratsiyasi
        try:
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN requested_at TYPE TIMESTAMP USING requested_at::timestamp")
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN requested_at SET DEFAULT CURRENT_TIMESTAMP")
            await conn.execute("ALTER TABLE payment_requests ALTER COLUMN processed_at TYPE TIMESTAMP USING processed_at::timestamp")
        except Exception:
            pass

        # Audit Logs migratsiyasi
        try:
            await conn.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp TYPE TIMESTAMP USING timestamp::timestamp")
            await conn.execute("ALTER TABLE audit_logs ALTER COLUMN timestamp SET DEFAULT CURRENT_TIMESTAMP")
        except Exception:
            pass

        # ==============================================================================
        # INDEKSLAR: Qidiruv va saralashni optimallashtirish (Full-Table scan dan himoya)
        # ==============================================================================
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_phone ON votes(phone)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_requests_phone ON payment_requests(phone)")
        
        # Chet kalitlar va ko'p filtrlanadigan maydonlar uchun indekslar
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_ref_by ON users(ref_by)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_tg_id ON votes(tg_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_referrals_inviter ON referrals(inviter_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_requests_tg_id ON payment_requests(tg_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id ON audit_logs(admin_id)")

