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
    snapshot_name = "clean"  # Имя твоего снимка (snapshot)
    cmd = [
        VBOX_PATH, "clonevm", TEMPLATE_VM_NAME,
        "--name", new_name,
        "--register",
        "--snapshot", snapshot_name,
        "--options", "link"
    ]
    print("Запускаю команду:", cmd)
    subprocess.run(cmd, check=True)
    return new_name

def start_vm(vm_name):
    cmd = [VBOX_PATH, "startvm", vm_name, "--type", "headless"]
    print("Запускаю команду:", cmd)
    subprocess.run(cmd, check=True)

def adb_devices():
    cmd = ["adb", "devices"]
    print("Запускаю команду:", cmd)
    out = subprocess.run(cmd, capture_output=True, text=True)
    print(out.stdout)
    return out.stdout

def wait_adb(ip, port=ADB_PORT, timeout=180):
    for _ in range(timeout // 5):
        try:
            cmd = ["adb", "connect", f"{ip}:{port}"]
            print("Запускаю команду:", cmd)
            subprocess.run(cmd, check=True, timeout=5)
            devices = adb_devices()
            # Проверяем, что устройство реально подключено
            if f"{ip}:{port}" in devices:
                return
        except Exception as ex:
            print("Ошибка подключения adb:", ex)
            time.sleep(5)
    raise Exception("ADB connect timeout")

def unique_device():
    android_id = rand_hex(16)
    imei = ''.join(random.choices(string.digits, k=15))
    ua = f"Dalvik/2.1.0 (Linux; Android 8.1.0; Custom_{rand_hex(5)})"
    cmd1 = ["adb", "shell", "su", "-c", f"settings put secure android_id {android_id}"]
    print("Запускаю команду:", cmd1)
    subprocess.run(cmd1)
    cmd2 = ["adb", "shell", "su", "-c", f"echo {imei} > /data/property/persist.radio.imei"]
    print("Запускаю команду:", cmd2)
    subprocess.run(cmd2)
    return ua

def parse_proxy(proxy):
    # Поддержка формата host:port или host:port:login:pass
    parts = proxy.strip().split(':')
    if len(parts) == 2:
        host, port = parts
        login = password = ""
    elif len(parts) == 4:
        host, port, login, password = parts
    else:
        raise Exception("Прокси должен быть в формате host:port или host:port:логин:пароль")
    return host, port, login, password

async def run_full_registration(proxy, google_data):
    try:
        vm_name = clone_vm()
        start_vm(vm_name)
        time.sleep(90)  # Дольше ждём загрузки VM!
        wait_adb(ADB_HOST)
        useragent = unique_device()

        # Поддерживаем оба формата прокси
        host, port, login, password = parse_proxy(proxy)
        set_proxy_superproxy(APPIUM_HOST, DEVICE_NAME, host, port, login, password)

        google_email, google_pass = google_data.split(":")
        google_login_success = google_login(APPIUM_HOST, DEVICE_NAME, google_email, google_pass)
        if not google_login_success:
            return {"success": False, "error": "Ошибка входа в Google"}

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

