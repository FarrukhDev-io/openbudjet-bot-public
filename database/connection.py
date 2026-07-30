import os
import aiosqlite

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_data.db"))


async def get_conn() -> aiosqlite.Connection:
    """Asinxron ma'lumotlar bazasi ulanishini qaytaradi"""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    """Barcha jadvallarni yaratish (Asinxron)"""
    async with await get_conn() as conn:
        async with conn.cursor() as cur:
            # Foydalanuvchilar jadvali
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id                 INTEGER PRIMARY KEY,
                    tg_id              INTEGER UNIQUE NOT NULL,
                    username           TEXT,
                    full_name          TEXT,
                    phone              TEXT,
                    ref_by             INTEGER,
                    joined_at          TEXT DEFAULT (datetime('now','localtime')),
                    voted              INTEGER DEFAULT 0,
                    vote_confirmed     INTEGER DEFAULT 0
                )
            """)

            # Ovozlar jadvali
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id        INTEGER NOT NULL,
                    phone        TEXT NOT NULL,
                    voted_at     TEXT DEFAULT (datetime('now','localtime')),
                    confirmed    INTEGER DEFAULT 0,
                    confirmed_at TEXT
                )
            """)

            # Referrallar jadvali
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id     INTEGER NOT NULL,
                    invited_id     INTEGER NOT NULL UNIQUE,
                    joined_at      TEXT DEFAULT (datetime('now','localtime')),
                    invited_voted  INTEGER DEFAULT 0
                )
            """)

            # To'lov so'rovlari (karta raqami)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS payment_requests (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id        INTEGER NOT NULL,
                    phone        TEXT,
                    full_name    TEXT,
                    card_number  TEXT NOT NULL,
                    amount       INTEGER DEFAULT 15000,
                    status       TEXT DEFAULT 'pending',
                    requested_at TEXT DEFAULT (datetime('now','localtime')),
                    processed_at TEXT,
                    processed_by INTEGER,
                    admin_note   TEXT
                )
            """)

            # Konfiguratsiya jadvali (VOTE_URL va boshqa sozlamalar uchun)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            await conn.commit()
