import sqlite3
import os

DB_PATH = "db/data.sqlite3"

def get_connection():
    if not os.path.exists("db"):
        os.makedirs("db")
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        email TEXT PRIMARY KEY,
        password TEXT,
        proxy TEXT,
        status TEXT,
        last_try TIMESTAMP,
        last_success TIMESTAMP
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        ad_url TEXT,
        message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        error TEXT,
        occured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def save_account(email, password, proxy, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO accounts(email, password, proxy, status, last_try)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (email, password, proxy, status))
    conn.commit()
    conn.close()

def log_message(email, ad_url, message, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages(email, ad_url, message, status)
        VALUES (?, ?, ?, ?)
    """, (email, ad_url, message, status))
    conn.commit()
    conn.close()

def log_error(email, error):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO errors(email, error)
        VALUES (?, ?)
    """, (email, error))
    conn.commit()
    conn.close()

# В main.py или при запуске приложения не забудь:
# from db.database import init_db
# init_db()