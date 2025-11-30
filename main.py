import asyncio
import logging
import json
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем функции из базы данных
from database import (
    create_tables, add_user, create_contest, get_contest, 
    add_participant, set_secret_winner, get_participants, mark_contest_inactive
)

# --- НАСТРОЙКИ (ЗАПОЛНИ ЭТО!) ---
TOKEN = "8405257491:AAGgnOU2fQ211KyfibeBVCRmL3GM8AXHrHw"
MY_ID = 12345678  # Твой ID цифрами
SITE_URL = "https://ТВОЙ-САЙТ.com/mini_app/index.html" # Ссылка на мини-апп

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 1. СТАРТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id, message.from_user.username)
    
    # Кнопка для открытия Web App
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🎁 Создать конкурс", web_app=types.WebAppInfo(url=SITE_URL))]],
        resize_keyboard=True
    )
    await message.answer(f"Привет! Нажми кнопку ниже, чтобы создать и настроить новый розыгрыш.", reply_markup=kb)

# --- 2. ПОЛУЧЕНИЕ ДАННЫХ ИЗ MINI APP ---
@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def parse_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)

        if data['action'] == 'create_contest':
            # Извлекаем данные, которые прислал сайт
            prize = data['prize']
            winners = int(data['winners'])
            channels = data['channels'] # Это список ['@a', '@b']
            end_time = data['end_time']
            description = data['description']

            # Сохраняем в БД
            contest_id = create_contest(
                message.from_user.id, 
                prize, 
                winners, 
                channels, 
                end_time, 
                description
            )

            # Формируем красивый отчет
            channels_str = ", ".join(channels)
            
            # Кнопка "Опубликовать"
            builder = InlineKeyboardBuilder()
            builder.button(text="📢 Опубликовать", callback_data=f"publish_{contest_id}")
            
            text = (
                f"✅ <b>Розыгрыш #{contest_id} создан!</b>\n\n"
                f"🏆 <b>Приз:</b> {prize}\n"
                f"👥 <b>Победителей:</b> {winners}\n"
                f"📢 <b>Каналы:</b> {channels_str}\n"
                f"📅 <b>Конец:</b> {end_time}\n"
                f"📝 <b>Условия:</b> {description}\n\n"
                f"Нажми кнопку ниже, чтобы отправить посты в каналы."
            )
            
            await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка обработки данных: {e}")

# --- 3. ПУБЛИКАЦИЯ В КАНАЛЫ ---
@dp.callback_query(F.data.startswith("publish_"))
async def publish_contest(callback: types.CallbackQuery):
    try:
        contest_id = int(callback.data.split("_")[1])
        contest = get_contest(contest_id)
        
        # Распаковываем данные из БД
        # Порядок полей: 0-id, 1-creator, 2-prize, 3-winners, 4-channels(json), 5-end_time, 6-desc, 7-secret, 8-active
        prize = contest[2]
        winners_count = contest[3]
        channels = json.loads(contest[4]) # Превращаем строку обратно в список
        end_time = contest[5].replace("T", " ") # Делаем дату красивее
        description = contest[6]

        # Кнопка участия
        builder = InlineKeyboardBuilder()
        builder.button(text="Участвовать!", callback_data=f"join_{contest_id}")

        text = (
            f"🎁 <b>РОЗЫГРЫШ!</b>\n\n"
            f"Разыгрываем: <b>{prize}</b>\n\n"
            f"📝 {description}\n\n"
            f"🏆 Победителей: {winners_count}\n"
            f"⏳ Итоги: {end_time}\n\n"
            f"👇 <b>Для участия нажми кнопку:</b>"
        )

        success_channels = []
        error_channels = []

        # Рассылаем пост во ВСЕ каналы из списка
        for channel in channels:
            try:
                await bot.send_message(chat_id=channel, text=text, reply_markup=builder.as_markup(), parse_mode="HTML")
                success_channels.append(channel)
            except Exception as e:
                error_channels.append(f"{channel} ({e})")

        # Отчет админу
        if len(error_channels) == 0:
            await callback.message.edit_text(f"✅ Успешно опубликовано в: {', '.join(success_channels)}")
        else:
            await callback.message.edit_text(
                f"⚠️ Частично опубликовано.\n"
                f"✅ Успех: {', '.join(success_channels)}\n"
                f"❌ Ошибки: {'; '.join(error_channels)}\n\n"
                f"Убедитесь, что бот является АДМИНИСТРАТОРОМ в каналах!"
            )

    except Exception as e:
        await callback.message.answer(f"Критическая ошибка: {e}")

# --- 4. УЧАСТИЕ (ПРОВЕРКА ПОДПИСОК) ---
@dp.callback_query(F.data.startswith("join_"))
async def join_contest(callback: types.CallbackQuery):
    contest_id = int(callback.data.split("_")[1])
    contest = get_contest(contest_id)
    
    if not contest[8]: # is_active
        await callback.answer("Конкурс уже завершен!", show_alert=True)
        return

    channels = json.loads(contest[4])
    user_id = callback.from_user.id
    
    # Проверяем подписку на КАЖДЫЙ канал
    not_subscribed = []
    
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except:
            # Если бот не админ или канал закрыт, считаем что не подписан (или игнорируем, зависит от строгости)
            not_subscribed.append(channel)

    if len(not_subscribed) > 0:
        text_channels = "\n".join(not_subscribed)
        await callback.answer(f"❌ Вы не подписаны на:\n{text_channels}\n\nПодпишитесь и попробуйте снова!", show_alert=True)
        return

    # Если всё ок - записываем
    success = add_participant(contest_id, user_id, callback.from_user.username or callback.from_user.first_name)
    
    if success:
        await callback.answer("✅ Вы участвуете! Удачи!", show_alert=True)
    else:
        await callback.answer("Вы уже в списке участников.", show_alert=True)

# --- 5. ЗАВЕРШЕНИЕ КОНКУРСА (/finish ID) ---
@dp.message(Command("finish"))
async def finish_contest(message: types.Message):
    if message.from_user.id != MY_ID:
        return

    try:
        args = message.text.split()
        contest_id = int(args[1])
    except:
        await message.answer("Пиши: /finish ID_КОНКУРСА")
        return

    contest = get_contest(contest_id)
    if not contest or not contest[8]:
        await message.answer("Конкурс не найден или завершен.")
        return

    prize = contest[2]
    winners_count = contest[3]
    channels = json.loads(contest[4])
    secret_winner_id = contest[7]

    participants = get_participants(contest_id)
    if len(participants) < winners_count:
        await message.answer(f"❌ Мало участников! ({len(participants)})")
        return

    # Выбор победителей (Логика с секретом)
    final_winners = []
    participants_ids = [p[0] for p in participants]

    if secret_winner_id and secret_winner_id in participants_ids:
        for p in participants:
            if p[0] == secret_winner_id:
                final_winners.append(p)
                break
        winners_count -= 1

    remaining_pool = [p for p in participants if p[0] != secret_winner_id]
    if winners_count > 0 and len(remaining_pool) >= winners_count:
        random_winners = random.sample(remaining_pool, k=winners_count)
        final_winners.extend(random_winners)

    # Формируем пост с итогами
    winners_text = "\n".join([f"🥳 <a href='tg://user?id={w[0]}'>{w[1]}</a>" for w in final_winners])
    
    post_text = (
        f"🏆 <b>ИТОГИ РОЗЫГРЫША: {prize}</b>\n\n"
        f"Победители:\n{winners_text}\n\n"
        f"Поздравляем!"
    )

    # Рассылаем итоги во все каналы
    for channel in channels:
        try:
            await bot.send_message(chat_id=channel, text=post_text, parse_mode="HTML")
        except:
            pass
            
    mark_contest_inactive(contest_id)
    await message.answer("✅ Итоги опубликованы, конкурс закрыт.")

# --- СЕКРЕТНАЯ КОМАНДА (/win ID USER_ID) ---
@dp.message(Command("win"))
async def secret_win(message: types.Message):
    if message.from_user.id != MY_ID: return
    try:
        args = message.text.split()
        set_secret_winner(int(args[1]), int(args[2]))
        await message.delete()
        await message.answer(f"🤫 Winner set for #{args[1]}")
    except:
        pass

async def main():
    create_tables()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())