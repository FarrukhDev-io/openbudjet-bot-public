import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# FIX (Roast R4): Real Automated Unit & Integration Tests to prevent regressions in production
from handlers.api import verify_telegram_init_data
from utils.limiter import check_rate_limit
from database.models import create_withdrawal_request


def test_verify_telegram_init_data_invalid():
    """Verify that initData verification returns None for malformed/missing hash payloads"""
    res = verify_telegram_init_data("user=abc", "fake_token")
    assert res is None


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_fallback():
    """Verify that if Redis fails, the rate limiter successfully falls back to local memory constraints"""
    # Clean fallback cache before running
    from utils.limiter import otp_limit_cache
    otp_limit_cache.clear()

    with patch("utils.limiter.is_rate_limited", side_effect=Exception("Redis offline")):
        # Max 3 requests allowed in 10 minutes
        res1 = await check_rate_limit("998901234567", 12345)
        res2 = await check_rate_limit("998901234567", 12345)
        res3 = await check_rate_limit("998901234567", 12345)
        res4 = await check_rate_limit("998901234567", 12345)

        assert res1 is True
        assert res2 is True
        assert res3 is True
        assert res4 is False  # 4th request must be rate limited


@pytest.mark.asyncio
async def test_create_withdrawal_request_no_user():
    """Verify that withdrawal request returns None if user does not exist in database"""
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None  # No user returned
    
    # Mock transaction as a MagicMock so calling it does not return a coroutine
    mock_transaction_mgr = MagicMock()
    mock_transaction_mgr.__aenter__ = AsyncMock()
    mock_transaction_mgr.__aexit__ = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=mock_transaction_mgr)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn

    with patch("database.models.get_conn", return_value=mock_context):
        res = await create_withdrawal_request(999999, "998901234567", "Test User", "8600123456789012")
        assert res is None
