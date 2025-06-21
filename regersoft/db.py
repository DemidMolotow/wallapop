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
        android_id TEXT,
        imei TEXT,
        serial TEXT,
        model TEXT,
        brand TEXT,
        fingerprint TEXT,
        mac TEXT,
        gsf_id TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def save_account(google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent, spoof_info):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO wallapop_accounts 
        (google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent,
        android_id, imei, serial, model, brand, fingerprint, mac, gsf_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        google_email, google_pass, wallapop_login, wallapop_password, proxy, useragent,
        spoof_info.get("android_id"), spoof_info.get("imei"), spoof_info.get("serial"),
        spoof_info.get("model"), spoof_info.get("brand"), spoof_info.get("fingerprint"),
        spoof_info.get("mac"), spoof_info.get("gsf_id")
    ))
    conn.commit()
    conn.close()
