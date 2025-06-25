import os
from dataclasses import dataclass
from typing import List
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BotConfig:
    BOT_TOKEN: str
    ALLOWED_USERS: List[str]
    ADMIN_CHAT_ID: int
    MESSAGE_LIMIT: int = 20
    PROXY_URL: str = None
    HEADLESS: bool = True  # Режим браузера по умолчанию

def load_config():
    """Загружает конфигурацию из переменных окружения или использует значения по умолчанию"""
    
    # Основные параметры с значениями по умолчанию (используем те же, что были в исходном коде)
    bot_token = os.getenv("BOT_TOKEN", "7512529507:AAHga264aQDpBF9fsSHrvDVgInkjwfPJ96o")
    admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", "7541702112"))
    
    # Список разрешенных пользователей
    allowed_users_str = os.getenv("ALLOWED_USERS", "sIappytappy")
    allowed_users = [u.strip() for u in allowed_users_str.split(",") if u.strip()]
    
    # Дополнительные параметры
    message_limit = int(os.getenv("MESSAGE_LIMIT", "20"))
    proxy_url = os.getenv("PROXY_URL")
    headless = os.getenv("HEADLESS", "True").lower() in ("true", "1", "yes")
    
    return BotConfig(
        BOT_TOKEN=bot_token,
        ALLOWED_USERS=allowed_users,
        ADMIN_CHAT_ID=admin_chat_id,
        MESSAGE_LIMIT=message_limit,
        PROXY_URL=proxy_url,
        HEADLESS=headless
    )
