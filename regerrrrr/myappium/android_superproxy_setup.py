from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.options.android import UiAutomator2Options
import time
from .appium_utils import is_appium_running, start_appium

def set_proxy_superproxy(appium_host, device_name, host, port, username, password):
    if not is_appium_running():
        start_appium()
        time.sleep(2)

    caps = {
        "platformName": "Android",
        "deviceName": device_name,
        "appPackage": "com.proxysuper.android",
        "appActivity": "com.proxysuper.android.MainActivity",
        "autoGrantPermissions": True
    }
    options = UiAutomator2Options()
    options.load_capabilities(caps)
    driver = webdriver.Remote(appium_host, options=options)
    time.sleep(7)

    try:
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Añadir proxy")'
        ).click()
        time.sleep(1)
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_host").send_keys(host)
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_port").send_keys(port)
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_username").send_keys(username)
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_password").send_keys(password)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Guardar")'
        ).click()
        time.sleep(2)
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Activar")'
        ).click()
        time.sleep(2)
        driver.quit()
    except Exception as e:
        driver.quit()
        raise e
