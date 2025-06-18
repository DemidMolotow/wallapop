import undetected_chromedriver as uc
import random
from config import USER_AGENTS

class ProfileManager:
    def __init__(self):
        self.used_ua = set()

    def get_new_user_agent(self):
        ua = random.choice([ua for ua in USER_AGENTS if ua not in self.used_ua] or USER_AGENTS)
        self.used_ua.add(ua)
        return ua

    def open_browser(self, proxy=None, user_agent=None, headless=True):
        options = uc.ChromeOptions()
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
        # Stealth: рандомизация window size, lang, platform и др.
        width, height = random.choice([(1280, 800), (1440, 900), (1920, 1080), (360, 640)])
        options.add_argument(f'--window-size={width},{height}')
        options.add_argument('--lang=' + random.choice(["es-ES", "en-US", "ru-RU"]))
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        driver = uc.Chrome(options=options, headless=headless)
        return driver