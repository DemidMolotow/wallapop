import asyncio

async def send_message(driver, ad_url, message_text):
    driver.get(ad_url)
    await asyncio.sleep(2.0)
    try:
        # Найти и нажать кнопку "Contactar" или аналогичную
        contact_btn = driver.find_element("xpath", "//button[contains(., 'Contactar') or contains(., 'Chat')]")
        contact_btn.click()
        await asyncio.sleep(2.0)
        # Найти textarea для сообщения
        textarea = driver.find_element("xpath", "//textarea")
        textarea.clear()
        textarea.send_keys(message_text)
        await asyncio.sleep(1.5)
        # Найти и нажать кнопку отправки
        send_btn = driver.find_element("xpath", "//button[contains(., 'Enviar') or contains(., 'Send')]")
        send_btn.click()
        await asyncio.sleep(2.0)
        return True
    except Exception as ex:
        print(f"Ошибка при отправке сообщения: {ex}")
        return False