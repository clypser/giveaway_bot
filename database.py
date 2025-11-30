import sqlite3
import json

DB_NAME = 'bot_database.db'

def create_tables():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT
    )
    ''')

    # Таблица конкурсов (Базовая структура)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        prize TEXT,
        winners_count INTEGER,
        channels TEXT, 
        end_time TEXT,
        description TEXT,
        secret_winner_id INTEGER DEFAULT NULL,
        is_active BOOLEAN DEFAULT 1
    )
    ''')

    # Таблица участников
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contest_id INTEGER,
        user_id INTEGER,
        user_name TEXT,
        UNIQUE(contest_id, user_id)
    )
    ''')
    
    # --- АВТОМАТИЧЕСКОЕ ОБНОВЛЕНИЕ БАЗЫ (Миграция) ---
    # Если база была создана старым кодом, в ней нет колонки 'channels'.
    # Мы проверяем это и добавляем колонки, если нужно.
    try:
        cursor.execute("SELECT channels FROM contests LIMIT 1")
    except sqlite3.OperationalError:
        print("⚠️ Обнаружена старая структура базы. Обновляем...")
        try:
            cursor.execute("ALTER TABLE contests ADD COLUMN channels TEXT")
            cursor.execute("ALTER TABLE contests ADD COLUMN end_time TEXT")
            cursor.execute("ALTER TABLE contests ADD COLUMN description TEXT")
            cursor.execute("ALTER TABLE contests ADD COLUMN secret_winner_id INTEGER DEFAULT NULL")
            print("✅ База данных успешно обновлена!")
        except Exception as e:
            print(f"❌ Ошибка обновления базы: {e}")

    connection.commit()
    connection.close()

# --- ФУНКЦИИ ---

def add_user(telegram_id, username):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (telegram_id, username))
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()

# Создание конкурса с новыми полями
def create_contest(creator_id, prize, winners_count, channels_list, end_time, description):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    try:
        # Превращаем список каналов ["@a", "@b"] в строку '["@a", "@b"]' для сохранения в БД
        channels_json = json.dumps(channels_list)
        
        cursor.execute("""
            INSERT INTO contests (creator_id, prize, winners_count, channels, end_time, description) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (creator_id, prize, winners_count, channels_json, end_time, description))
        
        contest_id = cursor.lastrowid
        connection.commit()
        print(f"✅ Конкурс #{contest_id} успешно сохранен в БД.")
        return contest_id
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА записи конкурса в БД: {e}")
        raise e # Пробрасываем ошибку дальше, чтобы бот знал о ней
    finally:
        connection.close()

def get_contest(contest_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM contests WHERE id = ?", (contest_id,))
    data = cursor.fetchone()
    connection.close()
    return data

def add_participant(contest_id, user_id, user_name):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO participants (contest_id, user_id, user_name) VALUES (?, ?, ?)", 
                       (contest_id, user_id, user_name))
        connection.commit()
        connection.close()
        return True
    except sqlite3.IntegrityError:
        connection.close()
        return False

def set_secret_winner(contest_id, winner_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("UPDATE contests SET secret_winner_id = ? WHERE id = ?", (winner_id, contest_id))
    connection.commit()
    connection.close()

def mark_contest_inactive(contest_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("UPDATE contests SET is_active = 0 WHERE id = ?", (contest_id,))
    connection.commit()
    connection.close()

def get_participants(contest_id):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    cursor.execute("SELECT user_id, user_name FROM participants WHERE contest_id = ?", (contest_id,))
    participants = cursor.fetchall()
    connection.close()
    return participants