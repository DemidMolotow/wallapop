import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7512529507:AAHga264aQDpBF9fsSHrvDVgInkjwfPJ96o)"
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7541702112").split(",")]

PROXY_LIST_PATH = os.getenv("PROXY_LIST_PATH", "proxies.txt")
EMAIL_LIST_PATH = os.getenv("EMAIL_LIST_PATH", "emails.txt")
PASTES_PATH = os.getenv("PASTES_PATH", "pastes.txt")
DB_PATH = os.getenv("DB_PATH", "db/data.sqlite3")

TARGET_PLATFORMS = ["wallapop"]
WALLAPOP_URL = "https://es.wallapop.com"

IMAP_PORT = int(os.getenv("IMAP_PORT", 993))

# Тонкая настройка
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 3))
REGISTRATION_URL = "https://es.wallapop.com/register"

# User-agents pool (можешь расширить)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]
