import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
from handlers import router
from logger import logger


async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='html'))
    dp = Dispatcher()

    # Подключаем роутер с обработчиками
    dp.include_router(router)

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
