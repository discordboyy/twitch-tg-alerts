# Twitch Telegram Notifier

Минимальный сервис: Twitch EventSub → FastAPI → Telegram Bot.

Когда Twitch сообщает через EventSub, что стрим начался (`stream.online`), сервис отправляет сообщение в Telegram-канал.

## Структура

```text
twitch-telegram-notifier/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 1. Twitch

Создай приложение в Twitch Developer Console и получи:

- `TWITCH_CLIENT_ID`
- `TWITCH_CLIENT_SECRET`

Также нужен ID аккаунта, который стримит:

- `TWITCH_BROADCASTER_ID`

Сгенерируй отдельный секрет для EventSub:

```bash
openssl rand -hex 32
```

Сохрани результат как `TWITCH_EVENTSUB_SECRET`.

## 2. Telegram

Создай бота через BotFather и получи:

```text
TELEGRAM_BOT_TOKEN
```

Добавь бота администратором в Telegram-канал и укажи ID канала в:

```text
TELEGRAM_CHAT_ID
```

Для публичного канала это обычно `@channel_username`.

## 3. Установка на Ubuntu

```bash
git clone https://github.com/YOUR_USERNAME/twitch-telegram-notifier.git
cd twitch-telegram-notifier

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
nano .env
```

Запуск:

```bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://127.0.0.1:8000/health
```

Должно вернуть:

```json
{"status":"ok"}
```

## 4. HTTPS

Twitch должен иметь возможность обратиться к публичному HTTPS URL:

```text
https://your-domain.example/webhook
```

Этот URL должен проксироваться на:

```text
http://127.0.0.1:8000/webhook
```

Например, через Nginx или Caddy.

## 5. Twitch EventSub

Нужно создать EventSub subscription:

```text
type:
stream.online

version:
1

condition:
broadcaster_user_id = TWITCH_BROADCASTER_ID

transport:
Webhook
```

В качестве callback URL используется:

```text
https://your-domain.example/webhook
```

Для EventSub Webhook Twitch использует challenge-запрос при создании подписки. `main.py` автоматически отвечает на этот challenge.

После подтверждения Twitch будет отправлять уведомления на `/webhook`.

## События

Обрабатываются:

```text
stream.online
stream.offline
```

При `stream.online` отправляется сообщение:

```text
🔴 Стрим начался!

📺 username
👉 https://twitch.tv/username
```

При `stream.offline` сейчас ничего в Telegram не отправляется.

## Важно

Секреты не должны попадать в Git:

```text
.env
```

уже добавлен в `.gitignore`.

`TWITCH_CLIENT_SECRET` пока хранится в `.env` для дальнейшего создания/управления EventSub-подпиской. Сам webhook проверяет подпись Twitch с помощью `TWITCH_EVENTSUB_SECRET`.
