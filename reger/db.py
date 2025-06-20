import sqlite3
from config import DB_FILE

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS wallapop_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        google_email TEXT,
        google_pass TEXT,
        wallapop_login TEXT,
        wallapop_password TEXT,
        proxy TEXT,
        useragent TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def save_account(google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO wallapop_accounts 
        (google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent))
    conn.commit()
    conn.close()