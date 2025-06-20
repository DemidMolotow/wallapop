# Wallapop Automation System — Ultimate Stealth AI Edition

## Быстрый старт

1. **Установи Python 3.10+ и Chrome!**
2. `python setup_auto.py` — установит все зависимости, скачает Playwright браузер, создаст структуру.
3. Заполни `config.py` (впиши токен Telegram-бота, при необходимости — admin id).
4. Запусти бота:  
   `python main.py`
5. Через Telegram-бота загрузи:
    - Прокси (один на строку, формат host:port или user:pass@host:port)
    - Почты (email:password, для IMAP-доступа!)
    - Пасты (тексты для рассылки)
6. Используй кнопки для запуска рассылки, остановки, загрузки данных.

---

## Структура

- **setup_auto.py** — автоматическая установка зависимостей и Playwright браузеров
- **config.py** — настройки
- **proxy_manager/** — работа с прокси
- **mail_manager/** — IMAP-доступ к почтовым ящикам, поиск кодов подтверждения
- **autodetect_profiles/** — undetected-chromedriver, создание stealth-профилей
- **warming_scenarios/** — имитация "человеческих" действий для прогрева аккаунтов
- **messaging/** — реальная отправка сообщений через браузер
- **parser.py** — реальный парсер объявлений
- **monitoring/** — Telegram-бот, управление всем процессом
- **db/** — для хранения статистики и истории (реализуешь под себя, если нужно)

---

## Особенности

- **Без лимита попыток:** для каждой почты и прокси перебираются разные user-agent, fingerprint и т.п. до успешной регистрации без SMS.
- **Если Wallapop требует SMS:** меняется только профиль браузера, user-agent, fingerprint, device — почта и прокси НЕ меняются!
- **IMAP:** бот сам ищет коды подтверждения на почте (почта:пароль должны быть рабочими для IMAP).
- **Stealth:** используется undetected-chromedriver, профили и fingerprint меняются на лету.
- **Все настройки через бот и config.py**

---

## Важно

- Для Gmail нужен App Password (или почта с IMAP-доступом)!
- Если потребуется поддержка других платформ (Vinted и др.) — расширяй parser.py и messaging/sender.py аналогично.
- Для production-статистики и логирования реализуй отдельную БД (db/).
- Для обхода ReCaptcha интегрируй сервис антикапчи (например, 2captcha) — в этот релиз не включено.

---

## Для вопросов и доработок — пиши!