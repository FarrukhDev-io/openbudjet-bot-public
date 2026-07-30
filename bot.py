import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database as db
from handlers import user, vote, admin
from handlers.api import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Global HTTP Session (startup'da ochiladi)
http_session: aiohttp.ClientSession | None = None


async def main():
    await db.init_db_pool()
    await db.init_db()

    global http_session
    http_session = aiohttp.ClientSession()

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
        vote.router,
        admin.router
    )

    # Web API Serverini background'da ishga tushirish
    asyncio.create_task(start_web_server(bot))

    logger.info("Bot ishga tushdi | Asosiy adminlar: %s", config.ADMIN_IDS)
    try:
        await dp.start_polling(bot)
    finally:
        await http_session.close()
        await db.close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())
