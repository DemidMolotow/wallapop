import random
import asyncio

async def human_actions(driver):
    actions = ["scroll", "search", "random_click", "wait"]
    for _ in range(random.randint(4, 8)):
        act = random.choice(actions)
        if act == "scroll":
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        elif act == "wait":
            await asyncio.sleep(random.uniform(1.5, 3.5))
        elif act == "random_click":
            # Попытка кликнуть по случайному элементу (например, случайная кнопка/ссылка)
            try:
                elems = driver.find_elements("xpath", "//a | //button")
                if elems:
                    random.choice(elems).click()
            except:
                pass
        elif act == "search":
            # Попробовать имитировать поиск
            try:
                search_box = driver.find_element("xpath", "//input[@type='search' or @placeholder]")
                search_box.send_keys(random.choice(["iPhone", "Xiaomi", "Nike", "Coche"]))
                await asyncio.sleep(random.uniform(1, 2))
                search_box.submit()
            except:
                pass
        await asyncio.sleep(random.uniform(1.0, 2.5))