"""
database/fsm_storage.py — PostgreSQL-based FSM Storage for aiogram 3.x

Bot qayta ishga tushsa ham foydalanuvchilarning FSM holati saqlanib qoladi.
"""
import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StorageKey

from database.connection import get_conn

logger = logging.getLogger(__name__)


class PgFSMStorage(BaseStorage):
    """
    Aiogram 3.x uchun PostgreSQL asosidagi FSM storage.
    Barcha state va data PostgreSQL `fsm_storage` jadvalida saqlanadi.
    """

    async def set_state(self, key: StorageKey, state: Optional[Any] = None) -> None:
        """FSM holatini o'rnatish yoki o'chirish."""
        state_str = None
        if state is not None:
            if hasattr(state, "state"):
                state_str = state.state
            else:
                state_str = str(state)

        async with get_conn() as conn:
            if state_str is None:
                await conn.execute(
                    "DELETE FROM fsm_storage WHERE chat_id = $1 AND user_id = $2",
                    key.chat_id,
                    key.user_id,
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO fsm_storage (chat_id, user_id, state, data)
                    VALUES ($1, $2, $3, '{}')
                    ON CONFLICT (chat_id, user_id)
                    DO UPDATE SET state = EXCLUDED.state,
                                  updated_at = NOW()
                    """,
                    key.chat_id,
                    key.user_id,
                    state_str,
                )

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """Joriy FSM holatini qaytarish."""
        async with get_conn() as conn:
            row = await conn.fetchval(
                "SELECT state FROM fsm_storage WHERE chat_id = $1 AND user_id = $2",
                key.chat_id,
                key.user_id,
            )
            return row if row else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """FSM ma'lumotlarini yozish (telefon, captcha_key, otp_key va boshqalar)."""
        async with get_conn() as conn:
            await conn.execute(
                """
                INSERT INTO fsm_storage (chat_id, user_id, state, data)
                VALUES ($1, $2, '', $3)
                ON CONFLICT (chat_id, user_id)
                DO UPDATE SET data = EXCLUDED.data,
                              updated_at = NOW()
                """,
                key.chat_id,
                key.user_id,
                json.dumps(data, ensure_ascii=False),
            )

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        """FSM ma'lumotlarini o'qish."""
        async with get_conn() as conn:
            raw: Optional[str] = await conn.fetchval(
                "SELECT data FROM fsm_storage WHERE chat_id = $1 AND user_id = $2",
                key.chat_id,
                key.user_id,
            )
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                logger.warning("PgFSMStorage: JSON decode failed for %s/%s", key.chat_id, key.user_id)
                return {}

    async def close(self) -> None:
        """Pool globally boshqariladi — bu yerda hech narsa yopilmaydi."""
        pass
