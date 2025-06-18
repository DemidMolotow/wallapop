import random

def load_lines(path):
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]

def random_user_agent(agents):
    return random.choice(agents)