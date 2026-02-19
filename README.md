# Telegram Userbot to RabbitMQ (Docker Compose)

This repository provides a minimal deployable pipeline:

- `Telethon` userbot listens to new messages in one or more target chats (numeric IDs)
- Events are published to RabbitMQ (topic exchange)
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
2. Generate a session string locally (requires `TG_API_ID` and `TG_API_HASH` in your environment):

```bash
uv sync
TG_API_ID=... TG_API_HASH=... uv run python tools/generate_session.py
```

Copy the printed value into `TG_SESSION_STRING`.

Note: `tools/generate_session.py` currently uses a hardcoded HTTP proxy at `127.0.0.1:7890`.
Edit the script if you do not want to use a proxy.

## 2. Configure environment

```bash
cp .env.example .env
```

Important values:

- `TG_TARGET_CHAT`: comma-separated numeric chat IDs (recommended, such as `-100...`)
- `TG_SESSION_STRING`: authorized user session

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

RabbitMQ management UI (not exposed by default in `docker-compose.yaml`):

- URL: `http://localhost:15672`
- Username: `RABBITMQ_USER`
- Password: `RABBITMQ_PASSWORD`

The compose file only exposes AMQP on `localhost:35672` (`5672` in the container).
If you want the management UI, add a port mapping for `15672`.

## RabbitMQ Publishing Details

The listener publishes to a topic exchange named by `MQ_EXCHANGE` (default: `telegram.messages`).
No queue is declared by the app, so consumers must create a queue and bind it to the exchange.

Routing key format for published messages: `chat:{chat_id}` (or `chat:unknown` if missing).
Use bindings like `chat:*` or `#` to receive all chat-specific routing keys.

## Event Schema

Published payload is JSON, for example:

```json
{
  "service": "telegram-userbot-listener",
  "event": "telegram.new_message",
  "chat_id": -1001234567890,
  "message_id": 42,
  "sender_id": 10001,
  "is_bot": false,
  "sender_username": "alice",
  "sender_fullname": "Alice Chen",
  "text": "hello",
  "date": "2026-02-16T06:00:00+00:00",
  "is_reply": true,
  "reply_to": {
    "message_id": 41,
    "sender_id": 9999,
    "sender_username": "bob",
    "sender_fullname": "Bob Li",
    "text": "previous message"
  },
  "has_media": true,
  "media": {
    "type": "photo",
    "class_name": "MessageMediaPhoto",
    "grouped_id": null,
    "file_id": 1234567890,
    "name": null,
    "ext": ".jpg",
    "mime_type": "image/jpeg",
    "size": 204800,
    "width": 1280,
    "height": 720,
    "duration": null
  },
  "out": false
}
```

The JSON Schema for payload validation is available at:

- `schemas/telegram_message.schema.json`

## Notes

- This uses a user account session; make sure usage complies with Telegram ToS.
- `TG_SESSION_STRING` is sensitive and should be treated like a credential.
- Current implementation handles only `NewMessage` events.
