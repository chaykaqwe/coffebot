import asyncio
from bot import bot, dp  # Импортируем бот и диспетчер
from handlers import router


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)  # Запускаем бота

if __name__ == "__main__":
    asyncio.run(main())
