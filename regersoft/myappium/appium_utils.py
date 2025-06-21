import requests
import time

def is_appium_running(url="http://localhost:4723/status"):
    try:
        r = requests.get(url, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def start_appium():
    # Опционально: можно запускать Appium через HTTP root API
    # Или оставить заглушку, если сервер стартует отдельно
    for i in range(15):
        if is_appium_running():
            print("Appium сервер запущен.")
            return True
        time.sleep(1)
    print("Appium сервер не стартовал :(")
    return False
