import subprocess
import time
from config import *
from db import save_account
from myappium.android_google_login import google_login
from myappium.android_superproxy_setup import set_proxy_superproxy
from myappium.wallapop_register import wallapop_register
from device_spoof_http import spoof_device_profile, set_proxy, clear_gsf, start_appium, get_device_info

def clone_vm():
    new_name = f"{TEMPLATE_VM_NAME}_clone_{int(time.time())}"
    snapshot_name = "clean"
    cmd = [
        VBOX_PATH, "clonevm", TEMPLATE_VM_NAME,
        "--name", new_name,
        "--register",
        "--snapshot", snapshot_name,
        "--options", "link"
    ]
    subprocess.run(cmd, check=True)
    return new_name

def start_vm(vm_name):
    cmd = [VBOX_PATH, "startvm", vm_name, "--type", "headless"]
    subprocess.run(cmd, check=True)

async def run_full_registration(proxy, google_data):
    try:
        vm_name = clone_vm()
        start_vm(vm_name)
        time.sleep(90)  # Ждём загрузки VM

        # SPOOF device profile через HTTP root API
        spoof_info = spoof_device_profile()
        clear_gsf()  # Чистим GSF перед логином Google

        # Настраиваем прокси на Android через HTTP root API
        set_proxy(proxy)
        start_appium()  # Стартуем Appium через root API

        google_email, google_pass = google_data.split(":")
        google_login_success = google_login(APPIUM_HOST, DEVICE_NAME, google_email, google_pass)
        if not google_login_success:
            return {"success": False, "error": "Ошибка входа в Google"}

        walla = wallapop_register(APPIUM_HOST, DEVICE_NAME)
        if not walla:
            return {"success": False, "error": "Ошибка регистрации Wallapop"}

        useragent = spoof_info.get("useragent", "Dalvik/2.1.0 (Linux; Android 8.1.0)")
        save_account(google_email, google_pass, walla['login'], walla['password'], proxy, useragent, spoof_info)

        return {
            "success": True,
            "wallapop_login": walla['login'],
            "wallapop_password": walla['password'],
            "proxy": proxy,
            "useragent": useragent,
            "spoof_info": spoof_info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
