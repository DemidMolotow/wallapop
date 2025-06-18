import httpx
import random
import os
import json

UA_LIST_URL = "https://user-agents.net/download"
FINGERPRINTS_URL = "https://raw.githubusercontent.com/fingerprintjs/fingerprintjs/main/fingerprints.json"
USER_AGENTS_PATH = "ua_updater/user_agents.json"
FINGERPRINTS_PATH = "ua_updater/fingerprints.json"

def update_user_agents():
    r = httpx.get(UA_LIST_URL)
    if r.status_code == 200:
        ua_list = r.text.splitlines()
        with open(USER_AGENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(ua_list, f)
        return True
    return False

def update_fingerprints():
    r = httpx.get(FINGERPRINTS_URL)
    if r.status_code == 200:
        with open(FINGERPRINTS_PATH, "w", encoding="utf-8") as f:
            f.write(r.text)
        return True
    return False

def get_random_user_agent():
    if not os.path.exists(USER_AGENTS_PATH):
        update_user_agents()
    with open(USER_AGENTS_PATH, "r", encoding="utf-8") as f:
        ua_list = json.load(f)
    return random.choice(ua_list)

def get_random_fingerprint():
    if not os.path.exists(FINGERPRINTS_PATH):
        update_fingerprints()
    with open(FINGERPRINTS_PATH, "r", encoding="utf-8") as f:
        fps = json.load(f)
    return random.choice(fps)