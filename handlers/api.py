import os
import logging
from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import database as db
from utils.validation import generate_p2p_links, mask_card
from utils.helpers import is_admin


logger = logging.getLogger(__name__)



async def api_stats(request: web.Request) -> web.Response:
    if not is_admin(int(request.query.get("admin_id", 0))):
        return web.json_response({"error": "Unauthorized"}, status=401)
    stats = await db.get_stats()
    return web.json_response(stats, headers={"Access-Control-Allow-Origin": "*"})


async def api_payments(request: web.Request) -> web.Response:
    if not is_admin(int(request.query.get("admin_id", 0))):
        return web.json_response({"error": "Unauthorized"}, status=401)
    status = request.query.get("status")  # pending, paid, rejected
    payments = await db.get_all_payments(status=status, limit=100)
    return web.json_response(payments, headers={"Access-Control-Allow-Origin": "*"})


async def api_payment_action(request: web.Request) -> web.Response:
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    data = await request.json()
    admin_id = int(data.get("admin_id", 0))
    if not is_admin(admin_id):
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
