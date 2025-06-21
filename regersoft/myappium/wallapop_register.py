from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
import time
import random
import string
from .appium_utils import is_appium_running, start_appium

def random_string(l):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=l))

def wallapop_register(appium_host, device_name):
    if not is_appium_running():
        start_appium()
        time.sleep(2)

    caps = {
        "platformName": "Android",
        "deviceName": device_name,
        "appPackage": "com.wallapop",
        "appActivity": "com.wallapop.ui.splash.SplashActivity",
        "autoGrantPermissions": True
    }
    options = UiAutomator2Options()
    options.load_capabilities(caps)
    driver = webdriver.Remote(appium_host, options=options)
    time.sleep(10)

    try:
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Registrarse")'
        ).click()
        time.sleep(2)
        email = f"{random_string(10)}@mail.com"
        driver.find_element(AppiumBy.ID, "com.wallapop:id/email_input").send_keys(email)
        username = f"usuario{random_string(6)}"
        driver.find_element(AppiumBy.ID, "com.wallapop:id/username_input").send_keys(username)
        password = random_string(12)
        driver.find_element(AppiumBy.ID, "com.wallapop:id/password_input").send_keys(password)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Crear cuenta")'
        ).click()
        time.sleep(7)
        driver.quit()
        return {'login': email, 'password': password}
    except Exception:
        driver.quit()
        return None
