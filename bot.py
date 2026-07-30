import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
import database as db
from handlers.vote import JSONStorage
from handlers import user_router, vote_router, admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Dispatcher initialization with persistent JSON FSM storage
dp = Dispatcher(storage=JSONStorage())

# Register routers
dp.include_router(admin_router)
dp.include_router(vote_router)
dp.include_router(user_router)


@dp.startup()
async def on_startup(bot: Bot) -> None:
    # Single reusable HTTP session initialized at dispatcher startup
    session = aiohttp.ClientSession()
    dp.workflow_data["session"] = session
    logger.info("Aiohttp ClientSession muvaffaqiyatli ochildi.")


@dp.shutdown()
async def on_shutdown(bot: Bot) -> None:
    # Close HTTP session at dispatcher shutdown
    session = dp.workflow_data.get("session")
    if session:
        await session.close()
        logger.info("Aiohttp ClientSession yopildi.")


async def main() -> None:
    await db.init_db()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    logger.info("Bot ishga tushdi | Super admin: %d | Adminlar: %s", config.SUPER_ADMIN_ID, config.ADMIN_IDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
