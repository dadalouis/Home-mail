"""Buttons on Companion app notifications: mark as read, archive, delete and reply, right from the notification."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback

from . import mail
from .const import DOMAIN, MAX_SENT_PER_HOUR, OPT_SENDER, OPT_SENT_FOLDER, OPT_SIGNATURE

_LOGGER = logging.getLogger(__name__)
PREFIX = "HOMEMAIL"
EVENT = "mobile_app_notification_action"

WORDS = {
    "en": {"read": "Mark as read", "archive": "Archive", "delete": "Delete", "reply": "Reply", "send": "Send",
           "placeholder": "Your answer", "failed": "Reply not sent", "sent": "Reply sent"},
    "nl": {"read": "Gelezen", "archive": "Archiveer", "delete": "Verwijder", "reply": "Beantwoord", "send": "Verstuur",
           "placeholder": "Je antwoord", "failed": "Antwoord niet verstuurd", "sent": "Antwoord verstuurd"},
}


def words(hass: HomeAssistant) -> dict[str, str]:
    return WORDS.get((hass.config.language or "en")[:2], WORDS["en"])


def action_id(kind: str, entry_id: str, uid: str) -> str:
    return f"{PREFIX}|{kind}|{entry_id}|{uid}"


def parse(action: str) -> tuple[str, str, str] | None:
    """'HOMEMAIL|read|<entry>|<uid>' -> ('read', entry, uid)."""
    parts = (action or "").split("|")
    if len(parts) != 4 or parts[0] != PREFIX or parts[1] not in ("read", "archive", "delete", "reply"):
        return None
    return parts[1], parts[2], parts[3]


def buttons(hass: HomeAssistant, entry_id: str, uid: str, os_name: str) -> list[dict[str, Any]]:
    """The buttons for one message. Android shows at most three, so Delete is left out there."""
    w = words(hass)
    reply = {"action": action_id("reply", entry_id, uid), "title": w["reply"], "behavior": "textInput"}
    read = {"action": action_id("read", entry_id, uid), "title": w["read"]}
    archive = {"action": action_id("archive", entry_id, uid), "title": w["archive"]}
    if os_name == "Android":
        return [read, archive, reply]
    reply.update(textInputButtonTitle=w["send"], textInputPlaceholder=w["placeholder"])
    delete = {"action": action_id("delete", entry_id, uid), "title": w["delete"], "destructive": True}
    return [read, archive, delete, reply]


def reply_subject(subject: str) -> str:
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


async def handle(hass: HomeAssistant, event: Event) -> None:
    from . import notify
    from .coordinator import account_cfg
    from .websocket import _may_use, _store

    got = parse(event.data.get("action", ""))
    if got is None:
        return
    kind, entry_id, uid = got
    entry = hass.config_entries.async_get_entry(entry_id)
    user = await hass.auth.async_get_user(event.context.user_id) if event.context.user_id else None
    if entry is None or entry.domain != DOMAIN or not _may_use(entry, user):
        _LOGGER.warning("Notification button ignored: this device's user may not use that account")
        return
    co = entry.runtime_data
    cfg = account_cfg(entry)
    try:
        if kind == "reply":
            text = (event.data.get("reply_text") or "").strip()
            if not text:
                return
            await _reply(hass, entry, user, uid, text)
            kind = "read"
        act = {"read": "seen", "archive": "archive", "delete": "delete"}[kind]
        await hass.async_add_executor_job(mail.action, cfg, uid, act, "INBOX")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Notification button %s for %s failed: %s", kind, cfg["email"], err)
        _, all_settings = await _store(hass)
        to = notify.targets(hass, user.id, notify.settings_of(all_settings, user.id), [])
        for d in to["app"]:
            await notify._call(hass, "notify", d["service"], {"title": "Home-mail", "message": f"{words(hass)['failed']}: {err}"})
        return
    if kind == "read":
        co.forget("INBOX", uid, seen=True)
    else:
        co.forget("INBOX", uid, gone=True)
    await co.async_request_refresh()


async def _reply(hass: HomeAssistant, entry, user, uid: str, text: str) -> None:
    from .coordinator import account_cfg
    from .websocket import USER_DEFAULTS, _store

    sent: list = hass.data[DOMAIN]["sent"]
    now = time.time()
    sent[:] = [t for t in sent if now - t < 3600]
    if len(sent) >= MAX_SENT_PER_HOUR:
        raise mail.MailError("rate_limit")
    co = entry.runtime_data
    cfg = account_cfg(entry)
    m = co.cache.get((entry.entry_id, "INBOX", uid))
    if m is None:  # not in memory any more (restart): read the headers again
        m = await hass.async_add_executor_job(mail.read_message, cfg, uid, False, "INBOX")
        m["address"] = m.get("reply_to") or m.get("address")
    _, all_settings = await _store(hass)
    mine = {**USER_DEFAULTS, **all_settings.get(user.id, {})}
    signature = entry.options.get(OPT_SIGNATURE) or ""
    body = f"{text}\n\n{signature}".rstrip() if signature else text
    sent_folder = entry.options.get(OPT_SENT_FOLDER) or (None if mail.is_gmail(cfg) else "AUTO")
    bcc = [cfg["email"]] if mine["bcc_me"] else []
    sender = entry.options.get(OPT_SENDER) or mine["sender"]
    await hass.async_add_executor_job(
        mail.send, cfg, sender, [m["address"]], [], reply_subject(m.get("subject") or ""), body,
        uid, "reply", sent_folder, bcc, "INBOX", (hass.config.language or "en")[:2])
    sent.append(now)


@callback
def async_setup(hass: HomeAssistant) -> None:
    async def _on_event(event: Event) -> None:
        if str(event.data.get("action", "")).startswith(PREFIX + "|"):
            await handle(hass, event)

    hass.bus.async_listen(EVENT, _on_event)
