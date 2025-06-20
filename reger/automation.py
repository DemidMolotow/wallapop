import subprocess
import random
import string
import time
from config import *
from db import save_account
from myappium.android_google_login import google_login
from myappium.android_superproxy_setup import set_proxy_superproxy
from myappium.wallapop_register import wallapop_register

def rand_hex(length):
    return ''.join(random.choices('0123456789abcdef', k=length))

def clone_vm():
    new_name = f"{TEMPLATE_VM_NAME}_clone_{rand_hex(6)}"
    subprocess.run([VBOX_PATH, "clonevm", TEMPLATE_VM_NAME, "--name", new_name, "--register", "--options", "link"], check=True)
    return new_name

def start_vm(vm_name):
    subprocess.run([VBOX_PATH, "startvm", vm_name, "--type", "headless"], check=True)

def wait_adb(ip, port=ADB_PORT, timeout=180):
    for _ in range(timeout // 5):
        try:
            subprocess.run(["adb", "connect", f"{ip}:{port}"], check=True, timeout=5)
            return
        except Exception:
            time.sleep(5)
    raise Exception("ADB connect timeout")

def unique_device():
    android_id = rand_hex(16)
    imei = ''.join(random.choices(string.digits, k=15))
    ua = f"Dalvik/2.1.0 (Linux; Android 8.1.0; Custom_{rand_hex(5)})"
    subprocess.run(["adb", "shell", "su", "-c", f"settings put secure android_id {android_id}"])
    subprocess.run(["adb", "shell", "su", "-c", f"echo {imei} > /data/property/persist.radio.imei"])
    return ua

async def run_full_registration(proxy, google_data):
    try:
        # 1. Клонируем и запускаем ВМ
        vm_name = clone_vm()
        start_vm(vm_name)
        time.sleep(70)
        wait_adb(ADB_HOST)
        useragent = unique_device()

        # 2. Настраиваем прокси через Super Proxy (UI автоматизация)
        host, port, login, password = proxy.split(":")
        set_proxy_superproxy(APPIUM_HOST, DEVICE_NAME, host, port, login, password)

        # 3. Вход в Google через Appium
        google_email, google_pass = google_data.split(":")
        google_login_success = google_login(APPIUM_HOST, DEVICE_NAME, google_email, google_pass)
        if not google_login_success:
            return {"success": False, "error": "Ошибка входа в Google"}

        # 4. Регистрация Wallapop через Appium
        walla = wallapop_register(APPIUM_HOST, DEVICE_NAME)
        if not walla:
            return {"success": False, "error": "Ошибка регистрации Wallapop"}

        save_account(google_email, google_pass, walla['login'], walla['password'], proxy, useragent)

        return {
            "success": True,
            "wallapop_login": walla['login'],
            "wallapop_password": walla['password'],
            "proxy": proxy,
            "useragent": useragent
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
