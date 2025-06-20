from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
import time

def set_proxy_superproxy(appium_host, device_name, host, port, username, password):
    caps = {
        "platformName": "Android",
        "deviceName": device_name,
        "appPackage": "com.proxysuper.android",  # проверь package!
        "appActivity": "com.proxysuper.android.MainActivity",  # проверь activity!
        "autoGrantPermissions": True
    }
    driver = webdriver.Remote(appium_host, caps)
    time.sleep(7)

    try:
        # Клик "Añadir proxy"
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Añadir proxy")'
        ).click()
        time.sleep(1)
        # Host
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_host").send_keys(host)
        # Port
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_port").send_keys(port)
        # Username
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_username").send_keys(username)
        # Password
        driver.find_element(AppiumBy.ID, "com.proxysuper.android:id/proxy_password").send_keys(password)
        # Guardar
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Guardar")'
        ).click()
        time.sleep(2)
        # Активировать proxy
        driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().textContains("Activar")'
        ).click()
        time.sleep(2)
        driver.quit()
    except Exception as e:
        driver.quit()
        raise e
