from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
import time
import random
import string

def random_string(l):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=l))

def wallapop_register(appium_host, device_name):
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
        # Клик "Registrarse"
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Registrarse")'
        ).click()
        time.sleep(2)
        # Email
        email = f"{random_string(10)}@mail.com"
        driver.find_element(AppiumBy.ID, "com.wallapop:id/email_input").send_keys(email)
        # Имя пользователя
        username = f"usuario{random_string(6)}"
        driver.find_element(AppiumBy.ID, "com.wallapop:id/username_input").send_keys(username)
        # Пароль
        password = random_string(12)
        driver.find_element(AppiumBy.ID, "com.wallapop:id/password_input").send_keys(password)
        # Кнопка "Crear cuenta"
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Crear cuenta")'
        ).click()
        time.sleep(7)
        driver.quit()
        return {'login': email, 'password': password}
    except Exception as e:
        driver.quit()
        return None
