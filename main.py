import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
# Импортируем наши функции из файла database.py
# ... другие импорты ...
from database import create_tables, add_user, create_contest, get_contest, add_participant, set_secret_winner, get_participants, mark_contest_inactive

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

# --- КОМАНДА ЗАВЕРШЕНИЯ КОНКУРСА ---
# Писать: /finish 1 (где 1 - это ID конкурса)
@dp.message(Command("finish"))
async def finish_contest(message: types.Message):
    # 1. Защита: только ты можешь завершить конкурс
    if message.from_user.id != MY_ID:
        return

    try:
        args = message.text.split()
        contest_id = int(args[1])
    except:
        await message.answer("⚠️ Ошибка! Пиши так: /finish ID_КОНКУРСА")
        return

    # 2. Получаем данные
    contest = get_contest(contest_id)
    if not contest:
        await message.answer("❌ Конкурс не найден.")
        return
    
    if not contest[6]: # Поле is_active (оно 6-е по счету в БД)
        await message.answer("❌ Этот конкурс уже завершен!")
        return

    channel = contest[4]
    winners_count = contest[3]
    secret_winner_id = contest[5] # Наше секретное поле

    # 3. Получаем список участников
    # participants - это список пар [(id, name), (id, name)...]
    participants = get_participants(contest_id) 
    
    if len(participants) < winners_count:
        await message.answer(f"❌ Мало участников! Нужно минимум {winners_count}, а участвует {len(participants)}.")
        return

    # --- 4. МАГИЯ ВЫБОРА ПОБЕДИТЕЛЯ ---
    final_winners = []
    
    # Список ID всех участников для проверки
    participants_ids = [p[0] for p in participants]

    # А) Сначала проверяем СЕКРЕТНОГО победителя
    if secret_winner_id and secret_winner_id in participants_ids:
        # Находим имя секретного победителя
        for p in participants:
            if p[0] == secret_winner_id:
                final_winners.append(p) # Добавляем (id, name)
                break
        # Уменьшаем кол-во мест для остальных
        winners_count -= 1

    # Б) Если еще нужны победители - выбираем случайно из оставшихся
    # Убираем секретного из списка для рандома, чтобы он не выиграл дважды
    remaining_pool = [p for p in participants if p[0] != secret_winner_id]
    
    if winners_count > 0:
        random_winners = random.sample(remaining_pool, k=winners_count)
        final_winners.extend(random_winners)

    # --- 5. ОБЪЯВЛЕНИЕ РЕЗУЛЬТАТОВ ---
    
    # Формируем красивый список имен
    winners_text = ""
    for w in final_winners:
        # w[0] - id, w[1] - username/name
        winners_text += f"🥳 <a href='tg://user?id={w[0]}'>{w[1]}</a>\n"

    post_text = f"🏆 <b>ИТОГИ РОЗЫГРЫША!</b>\n\n" \
                f"Победители:\n{winners_text}\n" \
                f"Поздравляем! Свяжитесь с администратором."

    # Отправляем в канал
    try:
        await bot.send_message(chat_id=channel, text=post_text, parse_mode="HTML")
        await message.answer(f"✅ Итоги опубликованы в канале {channel}!")
        
        # Помечаем конкурс как завершенный
        mark_contest_inactive(contest_id)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки в канал: {e}")

# Функция запуска
async def main():
    # Сначала создаем таблицы в базе (если их нет)
    create_tables()
    print("База данных подключена!")
    
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())