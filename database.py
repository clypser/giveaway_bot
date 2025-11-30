import sqlite3

# Название файла базы данных
DB_NAME = 'bot_database.db'

# 1. Функция создания таблиц (запускается один раз при старте)
def create_tables():
    # Подключаемся к файлу (или создаем его)
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    # Создаем таблицу users, если её нет
    # У нас будут поля: id (номер в базе), telegram_id (ID в телеграме), username (имя пользователя)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        username TEXT,
        referrer_id INTEGER, 
        balance INTEGER DEFAULT 0
    )
    ''')
    
    connection.commit()
    connection.close()

# 2. Функция добавления пользователя
def add_user(telegram_id, username, referrer_id=None):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()
    
    try:
        # Пытаемся добавить пользователя
        cursor.execute("INSERT INTO users (telegram_id, username, referrer_id) VALUES (?, ?, ?)", 
                       (telegram_id, username, referrer_id))
        connection.commit()
        print(f"Пользователь {username} добавлен в базу!")
        return True # Успешно добавили
    except sqlite3.IntegrityError:
        # Если такой ID уже есть, ничего не делаем
        return False # Уже был в базе
    finally:
        connection.close()