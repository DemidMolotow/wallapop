## Wallabot — Автоматическая регистрация Wallapop через Android x86, Super Proxy, Telegram и HTTP Root-сервер

## Как это работает

- Клонируется Android x86, запускается, уникализируется (device fingerprint spoof через HTTP root-сервер)
- Прокси настраивается через приложение Super Proxy (Appium UI)
- Выполняется автоматизированный вход в Google (Appium UI)
- Регистрируется аккаунт в Wallapop (Appium UI)
- Вся логика управления и spoof через HTTP root-сервер, никакого прямого adb!
- Управление через Telegram-бота, всё логируется в БД

---

## Установка

1. Установи зависимости:
    ```
    pip install -r requirements.txt
    ```
2. Разверни FastAPI root HTTP-сервер на Android (см. ниже)
3. Убедись, что VBoxManage, Appium и всё необходимое доступно на хосте
4. В Android x86 включи root и USB Debugging
5. В config.py пропиши актуальные параметры подключения (IP root-сервера, токены и прочее)
6. Запусти Appium сервер (можно через root HTTP API)
7. Запусти Telegram-бота:
    ```
    python bot.py
    ```

---

## HTTP root-сервер (на Android)

**Пример FastAPI сервера:**  
(см. device_spoof_http.py для структуры запросов)

- /spoof/android_id, /spoof/imei, /spoof/mac, /spoof/build_prop, /spoof/gsf_id, /spoof/device_profile
- /clear_gsf, /reboot, /start_appium
- /device_info — получить все spoofed параметры
- /exec — любой shell

---

## Использование

- Пиши `/start` в Telegram-боте
- Жми "+ Новая регистрация"
- Вводи прокси (host:port:логин:пароль) и Google-аккаунт (email:пароль)
- Получай готовый результат (логин/пароль Wallapop, прокси, useragent, spoofed параметры)

---

## Кастомизация spoof

- Все spoof операции идут через HTTP root API (см. device_spoof_http.py)
- База реалистичных фингерпринтов в device_spoof_http.py (можно расширять)

---

## Внимание

**Проект для ознакомительных целей. Использование на свой страх и риск.**