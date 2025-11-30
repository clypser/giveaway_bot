import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
# Импортируем наши функции из файла database.py
from database import create_tables, add_user

# --- ВСТАВЬ ТОКЕН ---
TOKEN = "8405257491:AAGgnOU2fQ211KyfibeBVCRmL3GM8AXHrHw"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Пытаемся записать человека в базу
    # (Функция вернет True, если это новый пользователь, и False, если старый)
    is_new = add_user(user_id, username)
    
    if is_new:
        await message.answer(f"Привет, {username}! Я тебя запомнил, ты теперь в базе!")
    else:
        await message.answer(f"С возвращением, {username}! Я тебя уже знаю.")

# Функция запуска
async def main():
    # Сначала создаем таблицы в базе (если их нет)
    create_tables()
    print("База данных подключена!")
    
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())