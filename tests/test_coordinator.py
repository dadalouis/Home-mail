import asyncio
import types

from conftest import coordinator, notify


class Hass:
    def __init__(self):
        self.tasks, self.events = [], []
        self.bus = types.SimpleNamespace(async_fire=lambda name, data: self.events.append(data))

    def async_create_task(self, coro):
        self.tasks.append(coro)
        coro.close()

    async def async_add_executor_job(self, func, *args):
        return func(*args)


def make(hass):
    entry = types.SimpleNamespace(entry_id="E1", title="Gmail", options={}, data={
        "email": "anna@example.com", "password": "x", "imap_server": "imap.example.com", "imap_port": 993,
        "smtp_server": "smtp.example.com", "smtp_port": 465})
    return coordinator.HomemailCoordinator(hass, entry)


def test_reading_a_message_without_notification_sends_nothing():
    hass = Hass()
    co = make(hass)
    co.forget("INBOX", "7", seen=True)
    assert hass.tasks == []  # no "take the notification away" push for a message that never had one
    co.notified = ["8"]
    co.forget("INBOX", "8", gone=True)
    assert len(hass.tasks) == 1 and co.notified == []


def test_only_sent_notifications_are_remembered(monkeypatch):
    hass = Hass()
    co = make(hass)
    msgs = [{"uid": u, "name": "Anna", "address": "anna@example.com", "subject": "s", "preview": "", "message_id": "", "date": ""}
            for u in ("5", "6")]
    monkeypatch.setattr(coordinator.mail, "new_since", lambda *a: msgs)

    async def notify_new(hass_, entry, m, unread):
        return m["uid"] == "6"  # "5" filtered out (quiet hours, muted sender, ...)
    monkeypatch.setattr(notify, "async_notify_new", notify_new)
    asyncio.run(co._fire_new(5, 2))
    assert co.notified == ["6"] and len(hass.events) == 2
