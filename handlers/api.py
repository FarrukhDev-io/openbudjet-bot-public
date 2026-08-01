import os
import hmac
import hashlib
import urllib.parse
import json
import logging
from typing import Optional
from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db
from utils.validation import generate_p2p_links, mask_card
from utils.helpers import is_admin


logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Telegram WebApp'dan kelgan initData oqimining haqiqiyligini tekshiradi (Cryptographic hash validation).
    Muvaffaqiyatli tekshirilsa, foydalanuvchi ma'lumotlarini dict ko'rinishida qaytaradi, aks holda None.
    """
    try:
        # Query string ko'rinishidagi ma'lumotlarni parse qilish
        parsed_data = urllib.parse.parse_qsl(init_data)
        data_dict = dict(parsed_data)
        if "hash" not in data_dict:
            return None
        
        hash_value = data_dict.pop("hash")
        # Kalitlarni alifbo tartibida saralash
        sorted_items = sorted(data_dict.items())
        # Tekshiruv satrini yig'ish (data-check-string)
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_items)
        
        # Maxfiy kalitni generatsiya qilish: HMAC-SHA256(WebTelegramData, BOT_TOKEN)
        secret_key = hmac.new(b"WebTelegramData", bot_token.encode(), hashlib.sha256).digest()
        # Hash hisoblash: HMAC-SHA256(secret_key, data-check-string)
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if calculated_hash == hash_value:
            # Hash to'g'ri bo'lsa, 'user' JSON maydonini parse qilish
            return json.loads(data_dict.get("user", "{}"))
    except Exception as e:
        logger.warning("Telegram initData verification failed: %s", e)
    return None


def get_authenticated_admin_id(request: web.Request) -> Optional[int]:
    """
    Request'dan admin shaxsini autentifikatsiya qiladi va uning Telegram ID-sini qaytaradi.
    Production muhitda strictly Authorization sarlavhasidagi initData verifikatsiya qilinadi.
    Localhost-da esa developerlarga qulaylik uchun 'admin_id' query parametriga fallback qiladi.
    """
    # 1. Authorization sarlavhasini tekshirish (TMA WebApp InitData)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("tma "):
        init_data = auth_header[4:]
        user_data = verify_telegram_init_data(init_data, config.BOT_TOKEN)
        if user_data:
            admin_id = user_data.get("id")
            if admin_id and is_admin(admin_id):
                return admin_id

    # 2. X-Telegram-Init-Data sarlavhasini tekshirish (muqobil usul)
    init_data_header = request.headers.get("X-Telegram-Init-Data")
    if init_data_header:
        user_data = verify_telegram_init_data(init_data_header, config.BOT_TOKEN)
        if user_data:
            admin_id = user_data.get("id")
            if admin_id and is_admin(admin_id):
                return admin_id

    # 3. Faqat local testing/development uchun fallback (localhost bo'lsa)
    host = request.host.split(":")[0]
    if host in ("localhost", "127.0.0.1", "testserver"):
        admin_id_query = request.query.get("admin_id")
        if admin_id_query and admin_id_query.isdigit():
            admin_id = int(admin_id_query)
            if is_admin(admin_id):
                return admin_id

    return None


async def api_stats(request: web.Request) -> web.Response:
    # Adminni xavfsiz autentifikatsiyadan o'tkazish
    admin_id = get_authenticated_admin_id(request)
    if not admin_id:
        return web.json_response({"error": "Unauthorized"}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    stats = await db.get_stats()
    return web.json_response(stats, headers={"Access-Control-Allow-Origin": "*"})


async def api_payments(request: web.Request) -> web.Response:
    # Adminni xavfsiz autentifikatsiyadan o'tkazish
    admin_id = get_authenticated_admin_id(request)
    if not admin_id:
        return web.json_response({"error": "Unauthorized"}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    status = request.query.get("status")  # pending, paid, rejected
    payments = await db.get_all_payments(status=status, limit=100)
    return web.json_response(payments, headers={"Access-Control-Allow-Origin": "*"})


async def api_payment_action(request: web.Request) -> web.Response:
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        })

    data = await request.json()
    admin_id = get_authenticated_admin_id(request)
    
    # Localhost-da ishlayotganda POST body ichidagi admin_id ga fallback qilish
    if not admin_id:
        host = request.host.split(":")[0]
        if host in ("localhost", "127.0.0.1", "testserver"):
            body_admin_id = data.get("admin_id")
            if body_admin_id and str(body_admin_id).isdigit() and is_admin(int(body_admin_id)):
                admin_id = int(body_admin_id)

    if not admin_id:
        return web.json_response({"error": "Unauthorized"}, status=401, headers={"Access-Control-Allow-Origin": "*"})

    req_id = int(data.get("id"))
    action = data.get("action")  # paid or rejected
    note = data.get("note", "")

    payment = await db.get_payment_request(req_id)
    if not payment:
        return web.json_response({"error": "Payment request not found"}, status=404, headers={"Access-Control-Allow-Origin": "*"})

    await db.update_payment_status(req_id, action, admin_id, note)

    # Foydalanuvchiga Telegram xabar yuborish
    bot = request.app['bot']
    try:
        if action == "paid":
            links = generate_p2p_links(payment["card_number"], payment["amount"])
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💳 Click P2P", url=links["click"]),
                InlineKeyboardButton(text="💳 Payme P2P", url=links["payme"]),
                InlineKeyboardButton(text="💳 Uzum P2P", url=links["uzum"]),
            ]])
            await bot.send_message(
                payment["tg_id"],
                f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                f"💰 <b>{payment['amount']:,} so'm</b> kartangizga o'tkazildi.\n"
                f"💳 Karta: <code>{mask_card(payment['card_number'])}</code>",
                reply_markup=keyboard,
            )
        else:
            await db.add_balance(payment["tg_id"], payment["amount"])
            await bot.send_message(
                payment["tg_id"],
                f"❌ <b>To'lov so'rovingiz rad etildi.</b>\n\n"
                f"📝 <b>Sabab:</b> {note}\n"
                f"💰 <b>{payment['amount']:,} so'm</b> balansingizga qaytarildi!",
            )
    except Exception as e:
        logger.warning("Foydalanuvchiga API orqali xabar ketmadi: %s", e)

    return web.json_response({"success": True}, headers={"Access-Control-Allow-Origin": "*"})


async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })


async def api_index(request: web.Request) -> web.Response:
    # Serve built front-end assets (index.html)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "adminpanel-vite/dist/index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="Admin Panel Mini App dist folder not found. Please build front-end using: npm run build")


async def init_web_app(bot: Bot) -> web.Application:
    app = web.Application()
    app['bot'] = bot

    # CORS options
    app.router.add_options('/{tail:.*}', handle_options)

    # API Endpoints
    app.router.add_get('/api/stats', api_stats)
    app.router.add_get('/api/payments', api_payments)
    app.router.add_post('/api/payments/action', api_payment_action)

    # Serve static assets
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(base_dir, "adminpanel-vite/dist")
    if os.path.exists(dist_dir):
        app.router.add_static('/assets/', path=os.path.join(dist_dir, "assets"), name="assets")

    app.router.add_get('/', api_index)
    return app


async def start_web_server(bot: Bot):
    app = await init_web_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()
    logger.info("Web API Server %d portda ishga tushdi.", config.PORT)
