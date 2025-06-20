from appium import webdriver
from appium.webdriver.common.mobileby import MobileBy
import time

def google_login(appium_host, device_name, email, password):
    caps = {
        "platformName": "Android",
        "deviceName": device_name,
        "appPackage": "com.android.settings",
        "appActivity": ".Settings",
        "autoGrantPermissions": True
    }
    driver = webdriver.Remote(appium_host, caps)
    time.sleep(8)

    try:
        # Открыть "Cuentas" (Аккаунты)
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR, 
            'new UiSelector().textContains("Cuentas")'
        ).click()
        time.sleep(1)
        # Добавить аккаунт
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR, 
            'new UiSelector().textContains("Añadir cuenta")'
        ).click()
        time.sleep(1)
        # Google
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Google")'
        ).click()
        time.sleep(7)
        # Вводим email
        email_field = driver.find_element(MobileBy.CLASS_NAME, "android.widget.EditText")
        email_field.send_keys(email)
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Siguiente")'
        ).click()
        time.sleep(4)
        # Вводим пароль
        pw_field = driver.find_elements(MobileBy.CLASS_NAME, "android.widget.EditText")[1]
        pw_field.send_keys(password)
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Siguiente")'
        ).click()
        time.sleep(7)
        # Принять условия
        driver.find_element(
            MobileBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Aceptar")'
        ).click()
        time.sleep(5)
        driver.quit()
        return True
    except Exception as e:
        driver.quit()
        return False
