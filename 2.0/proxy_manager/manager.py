import random
from utils import load_lines, save_lines
from config import PROXY_LIST_PATH

def get_all_proxies():
    return load_lines(PROXY_LIST_PATH)

def get_random_proxy():
    proxies = get_all_proxies()
    return random.choice(proxies) if proxies else None

def add_proxy(proxy):
    proxies = get_all_proxies()
    if proxy not in proxies:
        proxies.append(proxy)
        save_lines(PROXY_LIST_PATH, proxies)

def remove_proxy(proxy):
    proxies = get_all_proxies()
    proxies = [p for p in proxies if p != proxy]
    save_lines(PROXY_LIST_PATH, proxies)