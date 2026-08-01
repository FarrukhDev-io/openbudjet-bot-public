import asyncio
import logging
from aiohttp import web
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import database as db
from handlers.api import init_web_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api_server")


async def main():
    await db.init_db_pool()
    await db.init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FIX (Roast R3): Decoupling & SPOF elimination. Web API Server runs in its own process.
    app = await init_web_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # 0.0.0.0 is used to listen to external calls (e.g. from Railway gateway / reverse proxy)
    site = web.TCPSite(runner, '0.0.0.0', config.PORT)
    await site.start()
    
    logger.info("Web API Server started on port %d | Env: %s", config.PORT, config.ENVIRONMENT)
    
    # Keep server running until cancelled
    try:
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Exit signal received. Shutting down Web API Server...")
    finally:
        # FIX (Roast R3): Graceful Shutdown for database connection pools and web runners
        logger.info("Cleaning up Web App Runner...")
        await runner.cleanup()
        logger.info("Closing Database connection pool...")
        await db.close_db_pool()
        logger.info("Graceful shutdown completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
