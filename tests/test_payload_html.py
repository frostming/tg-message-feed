from __future__ import annotations

import sys
from datetime import UTC, datetime
from types import ModuleType
from types import SimpleNamespace
from unittest import TestCase

telethon_module = ModuleType("telethon")
telethon_module.TelegramClient = object
telethon_module.events = SimpleNamespace(NewMessage=SimpleNamespace(Event=object))
telethon_sessions_module = ModuleType("telethon.sessions")
telethon_sessions_module.StringSession = object
sys.modules.setdefault("telethon", telethon_module)
sys.modules.setdefault("telethon.sessions", telethon_sessions_module)

from app.main import _build_payload, _extract_reply_payload


class PayloadHtmlTests(TestCase):
    def test_build_payload_preserves_html_mentions(self) -> None:
        sender = SimpleNamespace(bot=False, username="alice", first_name="Alice")
        message = SimpleNamespace(
            chat_id=-100123,
            id=42,
            message="Alice",
            text_html='<a href="tg://user?id=123456">Alice</a>',
            date=datetime(2026, 3, 13, tzinfo=UTC),
            is_reply=False,
            media=None,
            out=False,
        )
        event = SimpleNamespace(message=message, sender=sender, sender_id=123456)

        payload = _build_payload(event, service_name="test-service", reply_to=None)

        self.assertEqual(payload["text"], "Alice")
        self.assertEqual(
            payload["text_html"], '<a href="tg://user?id=123456">Alice</a>'
        )

    def test_extract_reply_payload_preserves_html_mentions(self) -> None:
        reply_sender = SimpleNamespace(username="bob", first_name="Bob")
        reply_message = SimpleNamespace(
            id=41,
            sender_id=654321,
            sender=reply_sender,
            message="Bob",
            text_html='<a href="tg://user?id=654321">Bob</a>',
        )

        payload = _extract_reply_payload(reply_message)

        self.assertEqual(payload["text"], "Bob")
        self.assertEqual(
            payload["text_html"], '<a href="tg://user?id=654321">Bob</a>'
        )

    def test_falls_back_to_plain_text_when_html_is_unavailable(self) -> None:
        sender = SimpleNamespace(bot=False, username=None, first_name="Carol")
        message = SimpleNamespace(
            chat_id=-100123,
            id=43,
            message="plain text",
            date=datetime(2026, 3, 13, tzinfo=UTC),
            is_reply=False,
            media=None,
            out=False,
        )
        event = SimpleNamespace(message=message, sender=sender, sender_id=777)

        payload = _build_payload(event, service_name="test-service", reply_to=None)

        self.assertEqual(payload["text"], "plain text")
        self.assertEqual(payload["text_html"], "plain text")
