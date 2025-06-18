import random
from config import USER_AGENTS
from playwright.async_api import async_playwright

class ProfileManager:
    def __init__(self):
        self.used_ua = set()

    def get_new_user_agent(self):
        ua = random.choice([ua for ua in USER_AGENTS if ua not in self.used_ua] or USER_AGENTS)
        self.used_ua.add(ua)
        return ua

    async def open_browser(self, proxy=None, user_agent=None, headless=True):
        playwright = await async_playwright().start()
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]

        # Stealth/randomization: window size, lang, platform, etc.
        width, height = random.choice([(1280, 800), (1440, 900), (1920, 1080), (360, 640)])

        context_args = {
            "viewport": {"width": width, "height": height},
            "locale": random.choice(["es-ES", "en-US", "ru-RU"]),
            "user_agent": user_agent or self.get_new_user_agent(),
            "ignore_https_errors": True,
        }

        if proxy:
            context_args["proxy"] = {"server": proxy}

        browser = await playwright.chromium.launch(headless=headless, args=browser_args)
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        return playwright, browser, context, page
