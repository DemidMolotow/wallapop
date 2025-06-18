import imaplib
import email

def load_email_accounts(path):
    res = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                email_addr, password = line.strip().split(":", 1)
                res.append({"email": email_addr, "password": password})
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
    mail = imaplib.IMAP4_SSL(server)
    mail.login(email_addr, password)
    return mail

def find_verification_code(mail, subject_filter="Wallapop"):
    mail.select("inbox")
    typ, data = mail.search(None, f'(UNSEEN SUBJECT "{subject_filter}")')
    if typ != "OK" or not data or not data[0]:
        return None
    for num in data[0].split():
        typ, msg_data = mail.fetch(num, '(RFC822)')
        if typ != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                # Пример поиска кода в тексте
                import re
                m = re.search(r"\b(\d{4,6})\b", body)
                if m:
                    return m.group(1)
    return None