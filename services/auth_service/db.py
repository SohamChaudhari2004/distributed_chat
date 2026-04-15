import sqlite3
import os

# Use /data directory for persistence in Docker, or current directory locally
DB_PATH = os.environ.get('DB_PATH', '/data/auth.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            token TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Auth DB initialized at {DB_PATH}")

def get_connection():
    return sqlite3.connect(DB_PATH)
