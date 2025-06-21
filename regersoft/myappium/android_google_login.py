from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
import time
from .appium_utils import is_appium_running, start_appium

def google_login(appium_host, device_name, email, password):
    if not is_appium_running():
        start_appium()
        time.sleep(2)

    caps = {
        "platformName": "Android",
        "deviceName": device_name,
        "appPackage": "com.android.settings",
        "appActivity": ".Settings",
        "autoGrantPermissions": True
    }
    options = UiAutomator2Options()
    options.load_capabilities(caps)
    driver = webdriver.Remote(appium_host, options=options)
    time.sleep(8)

    try:
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR, 
            'new UiSelector().textContains("Cuentas")'
        ).click()
        time.sleep(1)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR, 
            'new UiSelector().textContains("Añadir cuenta")'
        ).click()
        time.sleep(1)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Google")'
        ).click()
        time.sleep(7)
        email_field = driver.find_element(AppiumBy.CLASS_NAME, "android.widget.EditText")
        email_field.send_keys(email)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Siguiente")'
        ).click()
        time.sleep(4)
        pw_field = driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")[1]
        pw_field.send_keys(password)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Siguiente")'
        ).click()
        time.sleep(7)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Aceptar")'
        ).click()
        time.sleep(5)
        driver.quit()
        return True
    except Exception:
        driver.quit()
        return False
