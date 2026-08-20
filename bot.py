import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import user, vote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot")

# Global HTTP Session (startup'da ochiladi)
http_session: aiohttp.ClientSession | None = None


async def main():
    global http_session
    # FIX (Roast R3): Resilient ClientSession with connection limits to avoid FD exhaustion
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
    http_session = aiohttp.ClientSession(connector=connector)

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    
    # Store dynamic data for handlers
    dp["session"] = http_session

    # Include modular routers
    dp.include_routers(
        user.router,
        vote.router
    )

    logger.info("Bot Polling process started | Admin IDs: %s", config.ADMIN_IDS)
    try:
        await dp.start_polling(bot)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Exit signal received. Shutting down bot...")
    finally:
        # Graceful Shutdown implementation to close session pools cleanly
        logger.info("Closing HTTP Session...")
        if http_session:
            await http_session.close()
        logger.info("Graceful shutdown completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
