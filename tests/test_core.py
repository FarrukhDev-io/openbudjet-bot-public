import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# FIX (Roast R4): Real Automated Unit & Integration Tests to prevent regressions in production
from handlers.api import verify_telegram_init_data
from utils.limiter import check_rate_limit
from database.models import create_withdrawal_request, get_balance, add_balance, deduct_balance

def test_verify_telegram_init_data_invalid():
    """Verify that initData verification returns None for malformed/missing hash payloads"""
    res = verify_telegram_init_data("user=abc", "fake_token")
    assert res is None

@pytest.mark.asyncio
async def test_rate_limiter_in_memory_fallback():
    """Verify that if Redis fails, the rate limiter successfully falls back to local memory constraints"""
    from utils.limiter import otp_limit_cache
    otp_limit_cache.clear()

    with patch("utils.limiter.is_rate_limited", side_effect=Exception("Redis offline")):
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
    
    mock_transaction_mgr = MagicMock()
    mock_transaction_mgr.__aenter__ = AsyncMock()
    mock_transaction_mgr.__aexit__ = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=mock_transaction_mgr)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn

    with patch("database.models.get_conn", return_value=mock_context):
        res = await create_withdrawal_request(999999, "998901234567", "Test User", "8600123456789012")
        assert res is None

@pytest.mark.asyncio
async def test_create_withdrawal_request_insufficient_balance():
    """Verify that withdrawal request returns None if user balance is 0 or less"""
    mock_conn = AsyncMock()
    # Mock return value for "SELECT balance FROM users WHERE tg_id = $1 FOR UPDATE"
    mock_conn.fetchrow.return_value = {"balance": 0}
    
    mock_transaction_mgr = MagicMock()
    mock_transaction_mgr.__aenter__ = AsyncMock()
    mock_transaction_mgr.__aexit__ = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=mock_transaction_mgr)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn

    with patch("database.models.get_conn", return_value=mock_context):
        res = await create_withdrawal_request(12345, "998901234567", "Test User", "8600123456789012")
        assert res is None

@pytest.mark.asyncio
async def test_create_withdrawal_request_already_pending():
    """Verify that withdrawal request returns None if there is a pending request already"""
    mock_conn = AsyncMock()
    # 1. First fetchrow returns user balance
    mock_conn.fetchrow.return_value = {"balance": 15000}
    # 2. First fetchval returns existing pending payment ID
    mock_conn.fetchval.return_value = 999  # Existing payment request
    
    mock_transaction_mgr = MagicMock()
    mock_transaction_mgr.__aenter__ = AsyncMock()
    mock_transaction_mgr.__aexit__ = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=mock_transaction_mgr)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn

    with patch("database.models.get_conn", return_value=mock_context):
        res = await create_withdrawal_request(12345, "998901234567", "Test User", "8600123456789012")
        assert res is None

@pytest.mark.asyncio
async def test_create_withdrawal_request_success():
    """Verify that withdrawal request successfully returns the request ID when all constraints are met"""
    mock_conn = AsyncMock()
    # 1. First fetchrow returns user balance
    mock_conn.fetchrow.return_value = {"balance": 15000}
    # 2. fetchval is called twice:
    #    - First for pending requests (returns None)
    #    - Second for insert returning request ID (returns 777)
    mock_conn.fetchval.side_effect = [None, 777]
    
    mock_transaction_mgr = MagicMock()
    mock_transaction_mgr.__aenter__ = AsyncMock()
    mock_transaction_mgr.__aexit__ = AsyncMock(return_value=False)
    mock_conn.transaction = MagicMock(return_value=mock_transaction_mgr)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn

    with patch("database.models.get_conn", return_value=mock_context):
        res = await create_withdrawal_request(12345, "998901234567", "Test User", "8600123456789012")
        assert res == 777
