import imaplib
import email
import traceback

def load_email_accounts(path):
    res = []
    try:
        print(f"[load_email_accounts] Открываю файл: {path}")
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip().replace('\r', '').replace('\n', '')
                if not line:
                    continue
                # поддержка email:password и email;password и просто email (без пароля)
                if ":" in line:
                    email_addr, password = line.split(":", 1)
                elif ";" in line:
                    email_addr, password = line.split(";", 1)
                else:
                    email_addr, password = line, ""
                email_addr = email_addr.strip()
                password = password.strip()
                if email_addr:
                    res.append({"email": email_addr, "password": password})
        print(f"[load_email_accounts] Загружено аккаунтов: {len(res)} из {path}")
    except Exception as e:
        print(f"[load_email_accounts ERROR] Не удалось загрузить аккаунты из {path}: {e}")
        traceback.print_exc()
    return res

def get_imap_server(email_addr):
    domain = email_addr.split("@")[-1]
    if domain == "gmail.com":
        return "imap.gmail.com"
    if domain == "yandex.ru":
        return "imap.yandex.ru"
    if domain == "mail.ru":
        return "imap.mail.ru"
    if domain == "outlook.com":
        return "imap-mail.outlook.com"
    return "imap." + domain

def connect_imap(email_addr, password, server):
    try:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(email_addr, password)
        print(f"[connect_imap] Успешный IMAP логин: {email_addr}@{server}")
        return mail
    except Exception as e:
        print(f"[connect_imap ERROR] Не удалось войти на {server} как {email_addr}: {e}")
        traceback.print_exc()
        raise

def find_verification_code(mail, subject_filter="Wallapop"):
    try:
        mail.select("inbox")
        typ, data = mail.search(None, f'(UNSEEN SUBJECT "{subject_filter}")')
        if typ != "OK" or not data or not data[0]:
            print("[find_verification_code] Нет писем с темой:", subject_filter)
            return None
        for num in data[0].split():
            typ, msg_data = mail.fetch(num, '(RFC822)')
            if typ != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    import re
                    m = re.search(r"\b(\d{4,6})\b", body)
                    if m:
                        print(f"[find_verification_code] Найден код: {m.group(1)}")
                        return m.group(1)
        print("[find_verification_code] Код не найден в письме.")
        return None
    except Exception as e:
        print(f"[find_verification_code ERROR]: {e}")
        traceback.print_exc()
        return None
