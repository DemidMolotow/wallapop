import imaplib
import email
import time

def connect_imap(email_addr, password, imap_server, imap_port=993):
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    mail.login(email_addr, password)
    return mail

def find_verification_code(mail, sender_filter=None, subject_filter=None, timeout=120):
    # mail: IMAP4_SSL connection (already logged in and selected inbox)
    # Looks for code in the most recent emails.
    start = time.time()
    while time.time() - start < timeout:
        mail.select("inbox")
        typ, data = mail.search(None, "ALL")
        mail_ids = data[0].split()
        for num in reversed(mail_ids[-10:]):  # Check last 10 messages
            typ, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            if sender_filter and sender_filter not in msg.get("From", ""):
                continue
            if subject_filter and subject_filter not in msg.get("Subject", ""):
                continue
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        code = extract_code(body)
                        if code:
                            return code
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                code = extract_code(body)
                if code:
                    return code
        time.sleep(5)
    return None

import re
def extract_code(text):
    # Поиск 4-8-значного кода (можно адаптировать под нужный шаблон)
    match = re.search(r'(\d{4,8})', text)
    return match.group(1) if match else None

def get_imap_server(email_addr):
    # Примитивный autodetect
    if email_addr.endswith("@gmail.com"):
        return "imap.gmail.com"
    elif email_addr.endswith("@yandex.ru") or email_addr.endswith("@yandex.com"):
        return "imap.yandex.com"
    elif email_addr.endswith("@mail.ru"):
        return "imap.mail.ru"
    elif email_addr.endswith("@outlook.com") or email_addr.endswith("@hotmail.com"):
        return "imap-mail.outlook.com"
    else:
        # Пробуем стандартный вариант
        domain = email_addr.split("@")[-1]
        return f"imap.{domain}"

def load_email_accounts(path):
    accounts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                email_addr, password = line.strip().split(":", 1)
                accounts.append({"email": email_addr, "password": password})
    return accounts