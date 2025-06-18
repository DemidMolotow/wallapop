import json
import os

DB_STATS_FILE = "db/stats.json"

def load_stats():
    if not os.path.exists(DB_STATS_FILE):
        return {"registered": 0, "messages_sent": 0, "sms_requests": 0, "errors": 0}
    with open(DB_STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_stats(stats):
    with open(DB_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

def inc_stat(key, amount=1):
    stats = load_stats()
    stats[key] = stats.get(key, 0) + amount
    save_stats(stats)

def get_stat(key):
    stats = load_stats()
    return stats.get(key, 0)