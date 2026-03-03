# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import async_session, init_db
from app.handlers import setup_routers
from app.payment_checker import check_pending_payments

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def db_middleware(handler, event, data):
    async with async_session() as session:
        data["session"] = session
        return await handler(event, data)


async def main():
    # Ждём БД
    for i in range(30):
        try:
            await init_db()
            logger.info("✅ Database connected!")
            break
        except Exception as e:
            logger.warning(f"⏳ Waiting for database... ({i+1}/30): {e}")
            await asyncio.sleep(2)
    else:
        logger.error("❌ Could not connect to database!")
        return
    
    # Бот
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.include_router(setup_routers())
    
    logger.info("🚀 Bot starting...")
    
    # Запускаем параллельно:
    # 1. Бота (polling Telegram)
    # 2. Проверку платежей (polling Robokassa)
    await asyncio.gather(
        dp.start_polling(bot),
        check_pending_payments(bot)
    )


if __name__ == "__main__":
    asyncio.run(main())