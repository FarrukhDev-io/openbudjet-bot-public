import asyncio
import aiohttp
from typing import Dict, Any

import config
import database as db
from utils.captcha import generate_captcha_header


async def fetch_captcha(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """OpenBudget API'dan captcha yuklash (500 xato bo'lsa qayta urinadi)"""
    for attempt in range(1, 4):
        headers = {
            "Access-Captcha": generate_captcha_header(),
            "Accept": "application/json",
            "Origin": "https://openbudget.uz",
            "Referer": "https://openbudget.uz/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        }
        try:
            async with session.get(config.CAPTCHA_URL, headers=headers) as resp:
                if resp.status == 500:
                    await asyncio.sleep(2 * attempt)
                    continue
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            if e.status == 500:
                await asyncio.sleep(2 * attempt)
                continue
            raise
    raise aiohttp.ClientError("Captcha serveri hozir ishlamayapti.")


async def send_otp(session: aiohttp.ClientSession, phone_number: str, captcha_key: str, captcha_result: int) -> Dict[str, Any]:
    """SMS kod (OTP) jo'natish so'rovi"""
    if len(phone_number) == 9:
        phone_number = "998" + phone_number
    payload = {
        "phone_number": phone_number,
        "captcha_key": captcha_key,
        "captcha_result": captcha_result,
    }
    async with session.post(config.SEND_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def verify_otp(session: aiohttp.ClientSession, phone_number: str, otp: str) -> Dict[str, Any]:
    """SMS kod (OTP)ni verifikatsiya qilish"""
    payload = {"phone_number": phone_number, "otp": otp}
    async with session.post(config.VERIFY_OTP_URL, json=payload) as resp:
        data = await resp.json()
        if resp.status != 200:
            raise ValueError(data.get("message", f"Xato: {resp.status}"))
        return data


async def submit_vote(session: aiohttp.ClientSession, access_token: str, initiative_uuid: str) -> Dict[str, Any]:
    """OpenBudget'da ovoz berish amalini bajarish"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    vote_url = await db.get_config("VOTE_URL")
    if vote_url:
        payload = {"initiative_id": initiative_uuid}
        async with session.post(vote_url, json=payload, headers=headers) as resp:
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

    for url in config.VOTE_CANDIDATES:
        for payload in [
            {"initiative_id": initiative_uuid},
            {"id": initiative_uuid},
            {"uuid": initiative_uuid},
            {"initiative_uuid": initiative_uuid},
        ]:
            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    try:
                        last_body = await resp.json(content_type=None)
                    except Exception:
                        last_body = {}
                    if resp.status == 404:
                        break
                    if resp.status in (200, 201):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower() or last_body.get("status") == "ERROR":
                            await db.set_config("VOTE_URL", url)
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        await db.set_config("VOTE_URL", url)
                        return last_body
                    if resp.status == 401:
                        raise ValueError("Token yaroqsiz. /start bosing.")
                    if resp.status in (400, 422):
                        error_msg = last_body.get("message", "") if isinstance(last_body, dict) else ""
                        if "already" in error_msg.lower() or "voted" in error_msg.lower():
                            await db.set_config("VOTE_URL", url)
                            raise ValueError("Siz allaqachon bu loyihaga ovoz bergansiz!")
                        continue
            except aiohttp.ClientConnectorError:
                continue
    raise ValueError(
        "⚠️ Ovoz berish endpointi aniqlanmadi.\n"
        "Ovoz berish davri boshlanganida qaytadan urinib ko'ring."
    )
