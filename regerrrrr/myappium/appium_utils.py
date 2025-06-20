import subprocess
import time
import requests

def is_appium_running(url="http://localhost:4723/status"):
    try:
        r = requests.get(url, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def start_appium():
    print("Запускаю Appium сервер...")
    subprocess.Popen(['npx', 'appium'], creationflags=subprocess.CREATE_NEW_CONSOLE)
    for i in range(15):
        if is_appium_running():
            print("Appium сервер запущен.")
            return True
        time.sleep(1)
    print("Appium сервер не стартовал :(")
    return False