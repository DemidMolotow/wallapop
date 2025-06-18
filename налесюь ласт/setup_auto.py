import subprocess
import sys
import os

def install_requirements():
    print("[*] Installing Python requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def install_playwright():
    print("[*] Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

def prepare_dirs():
    for d in [
        "autodetect_profiles", "proxy_manager", "mail_manager",
        "warming_scenarios", "messaging", "monitoring", "db"
    ]:
        os.makedirs(d, exist_ok=True)
    print("[*] Project directories prepared.")

def prepare_files():
    open("proxies.txt", "a").close()
    open("emails.txt", "a").close()
    open("pastes.txt", "a").close()
    print("[*] Placeholders created: proxies.txt, emails.txt, pastes.txt")

if __name__ == "__main__":
    install_requirements()
    install_playwright()
    prepare_dirs()
    prepare_files()
    print("[*] Setup complete! Fill in config.py and start the bot with python main.py")