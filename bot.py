import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Создаём объект бота (глобально)
bot = Bot(token=os.getenv('BOT_TOKEN'))

# Создаём диспетчер
dp = Dispatcher()
