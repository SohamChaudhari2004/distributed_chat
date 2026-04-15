import sqlite3
import os

# Use /data directory for persistence in Docker, or current directory locally
DB_PATH = os.environ.get('DB_PATH', '/data/store.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Store DB initialized at {DB_PATH}")

def get_connection():
    return sqlite3.connect(DB_PATH)