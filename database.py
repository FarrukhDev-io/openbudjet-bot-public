"""
Database moduli — SQLite
Jadvallar: users, votes, referrals, payment_requests
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "bot_data.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Barcha jadvallarni yaratish"""
    conn = get_conn()
    cur = conn.cursor()

    # Foydalanuvchilar
    cur.execute("""
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

    # Ovozlar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id        INTEGER NOT NULL,
            phone        TEXT NOT NULL,
            voted_at     TEXT DEFAULT (datetime('now','localtime')),
            confirmed    INTEGER DEFAULT 0,
            confirmed_at TEXT
        )
    """)

    # Referrallar
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id     INTEGER NOT NULL,
            invited_id     INTEGER NOT NULL UNIQUE,
            joined_at      TEXT DEFAULT (datetime('now','localtime')),
            invited_voted  INTEGER DEFAULT 0
        )
    """)

    # To'lov so'rovlari (karta raqami)
    cur.execute("""
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

    conn.commit()
    conn.close()


# ==============================================================================
# USERS
# ==============================================================================

def add_user(tg_id: int, username: str, full_name: str, ref_by: int = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (tg_id, username, full_name, ref_by)
        VALUES (?, ?, ?, ?)
    """, (tg_id, username, full_name, ref_by))
    conn.commit()
    conn.close()


def get_user(tg_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_user_phone(tg_id: int, phone: str):
    conn = get_conn()
    conn.execute("UPDATE users SET phone = ? WHERE tg_id = ?", (phone, tg_id))
    conn.commit()
    conn.close()


def set_user_voted(tg_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET voted = 1 WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()


def set_vote_confirmed(tg_id: int):
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE users SET vote_confirmed = 1 WHERE tg_id = ?", (tg_id,))
    conn.execute(
        "UPDATE votes SET confirmed = 1, confirmed_at = ? WHERE tg_id = ? AND confirmed = 0",
        (now, tg_id)
    )
    conn.execute(
        "UPDATE referrals SET invited_voted = 1 WHERE invited_id = ?",
        (tg_id,)
    )
    conn.commit()
    conn.close()


# ==============================================================================
# VOTES
# ==============================================================================

def add_vote(tg_id: int, phone: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO votes (tg_id, phone) VALUES (?, ?)",
        (tg_id, phone)
    )
    conn.execute(
        "UPDATE users SET voted = 1, phone = ? WHERE tg_id = ?",
        (phone, tg_id)
    )
    conn.commit()
    conn.close()


def get_vote(tg_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM votes WHERE tg_id = ? ORDER BY id DESC LIMIT 1", (tg_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def has_voted(tg_id: int) -> bool:
    row = get_vote(tg_id)
    return row is not None


# ==============================================================================
# PAYMENT REQUESTS
# ==============================================================================

def add_payment_request(tg_id: int, phone: str, full_name: str, card_number: str) -> int:
    """To'lov so'rovi qo'shish. Qaytaradi: yangi row ID"""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO payment_requests (tg_id, phone, full_name, card_number)
           VALUES (?, ?, ?, ?)""",
        (tg_id, phone, full_name, card_number)
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_payment_request(request_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM payment_requests WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_payments() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM payment_requests WHERE status = 'pending' ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_payment_status(request_id: int, status: str, admin_id: int, note: str = ""):
    """status: 'paid' | 'rejected'"""
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE payment_requests
           SET status = ?, processed_at = ?, processed_by = ?, admin_note = ?
           WHERE id = ?""",
        (status, now, admin_id, note, request_id)
    )
    conn.commit()
    conn.close()


def get_user_payment(tg_id: int) -> dict | None:
    """Foydalanuvchining so'nggi to'lov so'rovi"""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM payment_requests WHERE tg_id = ? ORDER BY id DESC LIMIT 1",
        (tg_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ==============================================================================
# REFERRALS
# ==============================================================================

def add_referral(inviter_id: int, invited_id: int):
    if inviter_id == invited_id:
        return
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO referrals (inviter_id, invited_id) VALUES (?, ?)",
        (inviter_id, invited_id)
    )
    conn.commit()
    conn.close()


def get_referral_stats(tg_id: int) -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE inviter_id = ?", (tg_id,)
    ).fetchone()[0]
    voted = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE inviter_id = ? AND invited_voted = 1",
        (tg_id,)
    ).fetchone()[0]
    conn.close()
    return {"total": total, "voted": voted}


def get_referral_link(tg_id: int, bot_username: str) -> str:
    return f"https://t.me/{bot_username}?start=ref_{tg_id}"


# ==============================================================================
# ADMIN STATISTIKA
# ==============================================================================

def get_stats() -> dict:
    conn = get_conn()
    total_users   = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_votes   = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    confirmed     = conn.execute("SELECT COUNT(*) FROM votes WHERE confirmed = 1").fetchone()[0]
    today_votes   = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE date(voted_at) = date('now','localtime')"
    ).fetchone()[0]
    total_refs    = conn.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
    pending_pays  = conn.execute(
        "SELECT COUNT(*) FROM payment_requests WHERE status = 'pending'"
    ).fetchone()[0]
    paid_count    = conn.execute(
        "SELECT COUNT(*) FROM payment_requests WHERE status = 'paid'"
    ).fetchone()[0]
    total_paid_sum = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payment_requests WHERE status = 'paid'"
    ).fetchone()[0]
    conn.close()
    return {
        "total_users":    total_users,
        "total_votes":    total_votes,
        "confirmed":      confirmed,
        "today_votes":    today_votes,
        "total_refs":     total_refs,
        "pending_pays":   pending_pays,
        "paid_count":     paid_count,
        "total_paid_sum": total_paid_sum,
    }


def get_votes_list(limit: int = 20, offset: int = 0) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT v.id, v.tg_id, v.phone, v.voted_at, v.confirmed,
               u.username, u.full_name
        FROM votes v
        LEFT JOIN users u ON v.tg_id = u.tg_id
        ORDER BY v.id DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_top_referrers(limit: int = 10) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT r.inviter_id, u.username, u.full_name,
               COUNT(*) as total,
               SUM(r.invited_voted) as voted_count
        FROM referrals r
        LEFT JOIN users u ON r.inviter_id = u.tg_id
        GROUP BY r.inviter_id
        ORDER BY voted_count DESC, total DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_payments(status: str = None, limit: int = 20, offset: int = 0) -> list:
    conn = get_conn()
    if status:
        rows = conn.execute("""
            SELECT p.*, u.username, u.full_name as u_full_name
            FROM payment_requests p
            LEFT JOIN users u ON p.tg_id = u.tg_id
            WHERE p.status = ?
            ORDER BY p.id DESC LIMIT ? OFFSET ?
        """, (status, limit, offset)).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.*, u.username, u.full_name as u_full_name
            FROM payment_requests p
            LEFT JOIN users u ON p.tg_id = u.tg_id
            ORDER BY p.id DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
