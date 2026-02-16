# Telegram Userbot to RabbitMQ (Docker Compose)

This repository provides a minimal deployable pipeline:

- `Telethon` userbot listens to all new messages in one target chat
- Events are published to RabbitMQ
- Full stack runs with `docker compose`

## Project Layout

```text
.
├── app/
│   ├── config.py
│   ├── main.py
│   └── mq.py
├── tools/
│   └── generate_session.py
├── docker-compose.yaml
├── Dockerfile
└── .env.example
```

## 1. Create Telegram API credentials

1. Open `https://my.telegram.org` and create an app to get `api_id` and `api_hash`.
2. Generate a session string locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/generate_session.py
```

Copy the printed value into `TG_SESSION_STRING`.

## 2. Configure environment

```bash
cp .env.example .env
```

Important values:

- `TG_TARGET_CHAT`: chat ID (recommended, such as `-100...`) or public username
- `TG_SESSION_STRING`: authorized user session

If session generation fails with `ModuleNotFoundError: No module named 'telethon'`,
install dependencies first:

```bash
pip install -r requirements.txt
```

## 3. Deploy

```bash
docker compose up -d --build
```

## 4. Verify

Check listener logs:

```bash
docker compose logs -f telegram-listener
```

When you see `Published message`, events are being pushed to RabbitMQ.

RabbitMQ management UI:

- URL: `http://localhost:15672`
- Username: `RABBITMQ_USER`
- Password: `RABBITMQ_PASSWORD`

Default queue: `telegram.messages.raw`

## Event Schema

Published payload is JSON, for example:

```json
{
  "service": "telegram-userbot-listener",
  "event": "telegram.new_message",
  "chat_id": -1001234567890,
  "message_id": 42,
  "sender_id": 10001,
  "text": "hello",
  "date": "2026-02-16T06:00:00+00:00",
  "is_reply": false,
  "reply_to_msg_id": null,
  "has_media": false,
  "out": false
}
```

## Notes

- This uses a user account session; make sure usage complies with Telegram ToS.
- `TG_SESSION_STRING` is sensitive and should be treated like a credential.
- Current implementation handles only `NewMessage` events.
