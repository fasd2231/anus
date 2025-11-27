# database.py
import sqlite3

DB_NAME = "bot_database.db"

def init_db():
    """Создает таблицу пользователей, если её нет"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def add_user(user_id):
    """Добавляет юзера, если его еще нет (IGNORE игнорирует дубли)"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

def get_users_count():
    """Возвращает количество пользователей"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

def get_all_users():
    """Возвращает список ID всех пользователей для рассылки"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        # Возвращаем плоский список [123, 456, 789]
        return [row[0] for row in cursor.fetchall()]