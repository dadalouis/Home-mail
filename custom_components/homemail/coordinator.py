"""Polls the inbox of one account: unread counter and new-mail events."""

from __future__ import annotations

import imaplib
import logging
from collections import OrderedDict
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import mail, notify
from .const import (
    CONF_IMAP_PORT, CONF_IMAP_SERVER, CONF_SMTP_PORT, CONF_SMTP_SERVER, DEFAULT_SCAN_INTERVAL, DOMAIN,
    EVENT_NEW_MAIL, OPT_NAME, OPT_SCAN_INTERVAL, SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)
PREFETCH_BODIES = 10  # newest unread messages kept ready per account
MAX_BODIES = 40
MAX_BODY = 2_000_000  # characters; bigger messages are fetched when opened


def account_cfg(entry: ConfigEntry) -> dict[str, Any]:
    d = entry.data
    return {
        "email": d["email"], "password": d["password"],
        "imap_server": d[CONF_IMAP_SERVER], "imap_port": d[CONF_IMAP_PORT],
        "smtp_server": d[CONF_SMTP_SERVER], "smtp_port": d[CONF_SMTP_PORT],
    }


class HomemailCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """data = {"unread": n, "uidnext": n, "uidvalidity": n}."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN} {entry.data['email']}", config_entry=entry,
            update_interval=timedelta(seconds=entry.options.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.entry = entry
        self.cfg = account_cfg(entry)
        self.cache: dict = {}  # (account, folder, uid) -> list row (headers + preview), memory only
        # Preloaded so the app opens instantly; memory only, refreshed when the inbox changes.
        self.inbox: list[dict] | None = None  # latest inbox list (with flags)
        self.mailboxes: list[dict] | None = None  # latest folder list with counters
        self.bodies: OrderedDict[tuple[str, str], dict] = OrderedDict()  # (folder, uid) -> read_message result
        self._prefetching = False

    def put_body(self, folder: str, uid: str, body: dict) -> None:
        if len(body.get("html", "")) > MAX_BODY:
            return
        self.bodies[(folder, uid)] = body
        self.bodies.move_to_end((folder, uid))
        while len(self.bodies) > MAX_BODIES:
            self.bodies.popitem(last=False)

    def forget(self, folder: str, uid: str, gone: bool = False, **flags) -> None:
        """Keep the preloaded data in line with an action done in the app."""
        if folder == "INBOX" and (gone or flags.get("seen")):
            self.hass.async_create_task(notify.async_clear(self.hass, self.entry, uid))
        if gone:
            self.bodies.pop((folder, uid), None)
        if folder == "INBOX" and self.inbox is not None:
            if gone:
                self.inbox = [r for r in self.inbox if r["uid"] != uid]
            else:
                for r in self.inbox:
                    if r["uid"] == uid:
                        r.update(flags)

    async def _prefetch(self) -> None:
        """Load the inbox list and the newest unread messages in the background."""
        if self._prefetching:
            return
        self._prefetching = True
        try:
            rows = await self.hass.async_add_executor_job(
                mail.list_messages, self.entry.entry_id, self.cfg, 50, None, self.cache, "INBOX")
            self.inbox = rows
            self.mailboxes = await self.hass.async_add_executor_job(mail.mailboxes, self.cfg)
            rows = sorted(rows, key=lambda r: r.get("date") or "", reverse=True)
            todo = [r["uid"] for r in rows if not r["seen"] and ("INBOX", r["uid"]) not in self.bodies][:PREFETCH_BODIES]
            for uid in todo:
                body = await self.hass.async_add_executor_job(mail.read_message, self.cfg, uid, False, "INBOX")
                self.put_body("INBOX", uid, body)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Prefetch for %s failed: %s", self.cfg["email"], err)
        finally:
            self._prefetching = False

    async def _async_update_data(self) -> dict[str, int]:
        try:
            st = await self.hass.async_add_executor_job(mail.inbox_status, self.cfg)
        except imaplib.IMAP4.error as err:
            if "auth" in str(err).lower() or "login" in str(err).lower() or "credentials" in str(err).lower():
                raise ConfigEntryAuthFailed(str(err)) from err
            raise UpdateFailed(f"IMAP: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"{type(err).__name__}: {err}") from err
        old = self.data
        if old and st["uidvalidity"] == old["uidvalidity"] and st["uidnext"] > old["uidnext"]:
            await self._fire_new(old["uidnext"], st["unread"])
        if old != st:
            async_dispatcher_send(self.hass, SIGNAL_UPDATE, self.entry.entry_id, st["unread"])
        if old is None or old.get("uidnext") != st["uidnext"] or old.get("unread") != st["unread"]:
            self.entry.async_create_background_task(self.hass, self._prefetch(), f"{DOMAIN} prefetch")
        return st

    async def _fire_new(self, first_uid: int, unread: int) -> None:
        try:
            new = await self.hass.async_add_executor_job(mail.new_since, self.entry.entry_id, self.cfg, first_uid)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("New mail fetch failed: %s", err)
            return
        for m in new:
            self.cache[(self.entry.entry_id, "INBOX", m["uid"])] = m
            self.hass.bus.async_fire(EVENT_NEW_MAIL, {
                "account": self.entry.entry_id,
                "account_name": self.entry.options.get(OPT_NAME) or self.entry.title,
                "account_email": self.cfg["email"],
                "uid": m["uid"], "from_name": m["name"], "from_address": m["address"],
                "subject": m["subject"], "preview": m["preview"], "message_id": m["message_id"],
                "date": m["date"], "unread": unread,
            })
            try:
                await notify.async_notify_new(self.hass, self.entry, m, unread)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Notifications for new mail failed: %s", err)
