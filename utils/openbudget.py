import asyncio
import aiohttp
import logging
from typing import Dict, Any

import config
import database as db
from utils.captcha import generate_captcha_header

logger = logging.getLogger("utils.openbudget")

# FIX (Roast R3): Resilient client limits and timeouts to prevent File Descriptor exhaustion
TIMEOUT = aiohttp.ClientTimeout(total=10)


async def fetch_captcha(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """OpenBudget API'dan captcha yuklash (Exponential backoff retry va timeout bilan)"""
    for attempt in range(1, 4):
        # FIX (Roast R4): Offloading CPU-bound header generation to a thread to prevent event loop lag
        captcha_header = await asyncio.to_thread(generate_captcha_header)
        headers = {
            "Access-Captcha": captcha_header,
            "Accept": "application/json",
            "Origin": "https://openbudget.uz",
            "Referer": "https://openbudget.uz/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        try:
            # FIX (Roast R3): Added timeout constraint
            async with session.get(config.CAPTCHA_URL, headers=headers, timeout=TIMEOUT) as resp:
                if resp.status == 500:
                    logger.warning("OpenBudget Captcha returned 500. Retrying in %d seconds...", 2 ** attempt)
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == 3:
                logger.exception("Failed to fetch captcha from OpenBudget after 3 attempts: %s", e)
                raise aiohttp.ClientError("Captcha serveri hozir ishlamayapti.") from e
            await asyncio.sleep(2 ** attempt)
    raise aiohttp.ClientError("Captcha serveri hozir ishlamayapti.")


async def send_otp(session: aiohttp.ClientSession, phone_number: str, captcha_key: str, captcha_result: int) -> Dict[str, Any]:
    """SMS kod (OTP) jo'natish so'rovi (Resilient timeouts va retries)"""
    if len(phone_number) == 9:
        phone_number = "998" + phone_number
    payload = {
        "phone_number": phone_number,
        "captcha_key": captcha_key,
        "captcha_result": captcha_result,
    }
    
    for attempt in range(1, 4):
        try:
            async with session.post(config.SEND_OTP_URL, json=payload, timeout=TIMEOUT) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise ValueError(data.get("message", f"Xato: {resp.status}"))
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == 3:
                logger.exception("Failed to send OTP after 3 attempts: %s", e)
                raise
            await asyncio.sleep(2 ** attempt)


async def verify_otp(session: aiohttp.ClientSession, phone_number: str, otp: str, otp_key: str = "") -> Dict[str, Any]:
    """SMS kod (OTP)ni verifikatsiya qilish"""
    if len(phone_number) == 9:
        phone_number = "998" + phone_number
    payload = {
        "phone_number": phone_number,
        "otp_code": otp,
        "otp_key": otp_key,
    }
    
    for attempt in range(1, 4):
        try:
            async with session.post(config.VERIFY_OTP_URL, json=payload, timeout=TIMEOUT) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise ValueError(data.get("message", f"Xato: {resp.status}"))
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == 3:
                logger.exception("Failed to verify OTP after 3 attempts: %s", e)
                raise
            await asyncio.sleep(2 ** attempt)


async def submit_vote(session: aiohttp.ClientSession, access_token: str, initiative_uuid: str) -> Dict[str, Any]:
    """OpenBudget'da ovoz berish amalini bajarish"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    vote_url = None
    try:
        vote_url = await db.get_config("VOTE_URL")
    except Exception as e:
        logger.warning("DB config olinmadi: %s", e)
    
    if vote_url:
        payload = {"initiative_id": initiative_uuid}
        for attempt in range(1, 4):
            try:
                async with session.post(vote_url, json=payload, headers=headers, timeout=TIMEOUT) as resp:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        data = {}
                    if resp.status in (200, 201):
                        error_msg = data.get("message", "") if isinstance(data, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower() or data.get("status") == "ERROR":
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        return data
                    raise ValueError(f"Vote xato ({resp.status}): {data.get('message', str(data))}")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == 3:
                    logger.exception("Failed to submit vote to cached URL: %s", e)
                    raise
                await asyncio.sleep(2 ** attempt)

    # Fallback to candidates list
    for url in config.VOTE_CANDIDATES:
        for payload in [
            {"initiative_id": initiative_uuid},
            {"id": initiative_uuid},
            {"uuid": initiative_uuid},
            {"initiative_uuid": initiative_uuid},
        ]:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=TIMEOUT) as resp:
                    try:
                        last_body = await resp.json(content_type=None)
                    except Exception:
                        last_body = {}
                    if resp.status == 404:
                        break
                    if resp.status in (200, 201):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower() or last_body.get("status") == "ERROR":
                            try:
                                await db.set_config("VOTE_URL", url)
                            except Exception:
                                pass
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        try:
                            await db.set_config("VOTE_URL", url)
                        except Exception:
                            pass
                        return last_body
                    if resp.status == 401:
                        raise ValueError("Token yaroqsiz. /start bosing.")
                    if resp.status in (400, 422):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower():
                            try:
                                await db.set_config("VOTE_URL", url)
                            except Exception:
                                pass
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        continue
            except (aiohttp.ClientError, asyncio.TimeoutError):
                continue
                continue
    raise ValueError(
        "⚠️ Ovoz berish endpointi aniqlanmadi.\n"
        "Ovoz berish davri boshlanganida qaytadan urinib ko'ring."
    )
