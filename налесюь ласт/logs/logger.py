import logging
from logging.handlers import RotatingFileHandler
import os

LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "app.log")

def setup_logger(name="main", log_file=LOG_FILE, level=logging.INFO, max_bytes=5*1024*1024, backup_count=5):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

# Пример использования:
# logger = setup_logger()
# logger.info("Logger started")