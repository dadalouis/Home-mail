"""Built-in notifications for new mail: Companion app and web app, per Home Assistant user."""
from __future__ import annotations

import logging
import re
import time
from typing import Any
from urllib.parse import quote

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util, slugify

from . import actions
from .const import DOMAIN, OPT_NAME, PANEL_URL

_LOGGER = logging.getLogger(__name__)

NOTIFY_DEFAULTS: dict[str, Any] = {
    "on": True,
    "accounts_off": [],  # entry ids of accounts that do not notify
    "days": [0, 1, 2, 3, 4, 5, 6],  # Monday = 0
    "quiet_on": False,
    "quiet_from": "22:00",
    "quiet_to": "07:00",
    "only": "all",  # all | vip
    "vip": "",  # one address or domain per line
    "mute": "",  # senders that never notify
    "preview": True,
    "sound": True,
    "buttons": True,  # Read / Archive / Delete / Reply on Companion app notifications
    "app": True,  # Companion app
    "web": True,  # web app (html5 push)
    "devices_off": [],  # Companion devices (names) that do not notify
}
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def clean(raw: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    """Apply changes from the app on the stored notification settings (unknown or invalid values are ignored)."""
    out = {**NOTIFY_DEFAULTS, **old}
    for k in ("on", "quiet_on", "preview", "sound", "buttons", "app", "web"):
        if k in raw:
            out[k] = bool(raw[k])
    for k in ("quiet_from", "quiet_to"):
        if isinstance(raw.get(k), str) and HHMM.match(raw[k]):
            out[k] = raw[k]
    if raw.get("only") in ("all", "vip"):
        out["only"] = raw["only"]
    for k in ("vip", "mute"):
        if isinstance(raw.get(k), str):
            out[k] = raw[k][:4000]
    if isinstance(raw.get("days"), list):
        out["days"] = sorted({int(d) for d in raw["days"] if isinstance(d, int) and 0 <= d <= 6})
    for k in ("accounts_off", "devices_off"):
        if isinstance(raw.get(k), list):
            out[k] = [str(x)[:100] for x in raw[k]][:100]
    return out


def settings_of(all_settings: dict, user_id: str) -> dict[str, Any]:
    return {**NOTIFY_DEFAULTS, **(all_settings.get(user_id, {}).get("notify") or {})}


def _patterns(text: str) -> list[str]:
    out = []
    for p in re.split(r"[\s,;]+", text or ""):
        p = p.strip().lower()
        if p:
            out.append(p if "@" in p.lstrip("@") else p.lstrip("@"))
    return out


def sender_in(text: str, address: str) -> bool:
    """True when the address matches a line of the list: a full address, or a domain (also its subdomains)."""
    address = (address or "").lower()
    domain = address.rpartition("@")[2]
    for p in _patterns(text):
        if "@" in p:
            if address == p:
                return True
        elif domain == p or domain.endswith("." + p):
            return True
    return False


def in_quiet_hours(cfg: dict[str, Any], now) -> bool:
    if not cfg["quiet_on"]:
        return False
    t = now.strftime("%H:%M")
    start, end = cfg["quiet_from"], cfg["quiet_to"]
    if start == end:
        return False
    return start <= t < end if start < end else (t >= start or t < end)


def wanted(cfg: dict[str, Any], account: str, m: dict[str, Any], now) -> bool:
    """Should this user get a notification for this message (settings, account, day, quiet hours, senders)?"""
    if not cfg["on"] or account in cfg["accounts_off"] or now.weekday() not in cfg["days"]:
        return False
    if in_quiet_hours(cfg, now):
        return False
    address = m.get("address") or ""
    if sender_in(cfg["mute"], address):
        return False
    if cfg["only"] == "vip" and not sender_in(cfg["vip"], address):
        return False
    return True


# ---------- where to send ----------

def app_devices(hass: HomeAssistant, user_id: str) -> list[dict[str, str]]:
    """Companion app devices of this user: [{name, service, os}]."""
    out = []
    for e in hass.config_entries.async_entries("mobile_app"):
        if e.data.get("user_id") != user_id:
            continue
        name = e.data.get("device_name") or e.title
        service = f"mobile_app_{slugify(name)}"
        if hass.services.has_service("notify", service):
            out.append({"name": name, "service": service, "os": e.data.get("os_name") or ""})
    return out


def web_devices(hass: HomeAssistant, names: list[str]) -> list[dict[str, str]]:
    """notify entities (html5) for the registrations this user made in the web app: [{name, entity_id}]."""
    if not names or not hass.services.has_service("html5", "send_message"):
        return []
    reg = er.async_get(hass)
    out = []
    for e in reg.entities.values():
        if e.platform != "html5" or e.domain != "notify" or e.disabled:
            continue
        name = next((n for n in names if (e.unique_id or "").endswith(f"_{n}_device")), None)
        if name:
            out.append({"name": name, "entity_id": e.entity_id})
    return out


def web_entities(hass: HomeAssistant, names: list[str]) -> list[str]:
    return [d["entity_id"] for d in web_devices(hass, names)]


def unread_total(hass: HomeAssistant, user, entry: ConfigEntry | None = None, unread: int | None = None) -> int:
    """Unread messages over all accounts this user may use (the red number on the app icon)."""
    from .websocket import _accounts

    total = 0
    for e in _accounts(hass, user).values():
        if entry is not None and e.entry_id == entry.entry_id and unread is not None:
            total += unread
        else:
            total += ((e.runtime_data.data if e.runtime_data else None) or {}).get("unread", 0)
    return total


def delivery(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Last result per device ("app:<service>" / "web:<entity_id>"), memory only: shown in the settings."""
    return hass.data[DOMAIN].setdefault("delivery", {})


def targets(hass: HomeAssistant, user_id: str, cfg: dict[str, Any], web_names: list[str]) -> dict[str, Any]:
    app = [d for d in app_devices(hass, user_id) if d["name"] not in cfg["devices_off"]] if cfg["app"] else []
    web = web_entities(hass, web_names) if cfg["web"] else []
    return {"app": app, "web": web}


URL = re.compile(r"(?:https?://|www\.)\S+", re.I)


def clean_preview(text: str, limit: int = 140) -> str:
    """Preview for a notification: no links, one line of text."""
    t = re.sub(r"\s+", " ", URL.sub("", text or "")).strip(" -–—·:()[]")
    return (t[:limit].rstrip() + "…") if len(t) > limit else t


async def _call(hass: HomeAssistant, domain: str, service: str, data: dict[str, Any], target: dict | None = None,
                keys: list[str] | None = None) -> bool:
    """Call a service and wait for it. A device that is offline must not disturb the others (or flood the log).
    keys: devices to remember the result for (shown in the settings)."""
    ok, error = True, ""
    try:
        await hass.services.async_call(domain, service, data, target=target, blocking=True)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("%s.%s failed: %s", domain, service, err)
        ok, error = False, str(err)[:200]
    for k in keys or []:
        delivery(hass)[k] = {"ts": time.time(), "ok": ok, "error": error}
    return ok


def tag_for(entry: ConfigEntry, uid: str) -> str:
    return f"homemail-{entry.entry_id}-{uid}"


# ---------- sending ----------

async def _send(hass: HomeAssistant, entry: ConfigEntry, m: dict[str, Any], badge: int, cfg: dict[str, Any],
                to: dict[str, Any], account_label: str | None) -> None:
    sender = m.get("name") or m.get("address") or "Home-mail"
    title = f"{sender} · {account_label}" if account_label else sender
    subject = m.get("subject") or "(no subject)"
    preview = clean_preview(m.get("preview") or "")
    message = f"{subject}\n{preview}" if cfg["preview"] and preview else subject
    tag = tag_for(entry, m["uid"])
    group = f"homemail-{entry.entry_id}"
    link = f"/{PANEL_URL}?mail={quote(m.get('message_id') or '', safe='')}" if m.get("message_id") else f"/{PANEL_URL}"
    for d in to["app"]:
        data = {"group": group, "tag": tag, "url": link, "clickAction": link,
                "push": {"badge": badge, "thread-id": group, **({} if cfg["sound"] else {"sound": "none"})},
                "ttl": 0, "priority": "high"}
        if cfg["buttons"]:
            data["actions"] = actions.buttons(hass, entry.entry_id, m["uid"], d["os"])
        await _call(hass, "notify", d["service"], {"title": title, "message": message, "data": data}, keys=[f"app:{d['service']}"])
    if to["web"]:
        payload = {"title": title, "message": message, "tag": tag,
                   "data": {"message_id": m.get("message_id") or "", "unread": badge}}
        if not cfg["sound"]:
            payload["silent"] = True
        await _call(hass, "html5", "send_message", payload, {"entity_id": to["web"]}, keys=[f"web:{x}" for x in to["web"]])


async def async_notify_new(hass: HomeAssistant, entry: ConfigEntry, m: dict[str, Any], unread: int) -> None:
    """One new message: tell every user who may read this account and wants to hear about it."""
    from .websocket import _accounts, _may_use, _store  # late import: websocket imports the coordinator

    _, all_settings = await _store(hass)
    now = dt_util.now()
    for user in await hass.auth.async_get_users():
        if not _may_use(entry, user):
            continue
        cfg = settings_of(all_settings, user.id)
        if not wanted(cfg, entry.entry_id, m, now):
            continue
        to = targets(hass, user.id, cfg, all_settings.get(user.id, {}).get("push") or [])
        if not to["app"] and not to["web"]:
            continue
        label = (entry.options.get(OPT_NAME) or entry.title) if len(_accounts(hass, user)) > 1 else None
        try:
            await _send(hass, entry, m, unread_total(hass, user, entry, unread), cfg, to, label)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Notification for %s failed: %s", user.name, err)


async def async_clear(hass: HomeAssistant, entry: ConfigEntry, uid: str) -> None:
    """The message was read or removed in the app: take its notification away again."""
    from .websocket import _may_use, _store

    _, all_settings = await _store(hass)
    tag = tag_for(entry, uid)
    for user in await hass.auth.async_get_users():
        if not _may_use(entry, user):
            continue
        cfg = settings_of(all_settings, user.id)
        to = targets(hass, user.id, cfg, all_settings.get(user.id, {}).get("push") or [])
        for d in to["app"]:
            await _call(hass, "notify", d["service"], {"message": "clear_notification", "data": {"tag": tag}})
        if to["web"] and hass.services.has_service("html5", "dismiss_message"):
            await _call(hass, "html5", "dismiss_message", {"tag": tag}, {"entity_id": to["web"]})


async def async_badge(hass: HomeAssistant, entry: ConfigEntry, unread: int) -> None:
    """Fewer unread messages (read here or in another app): set the red number on iPhone/iPad/Mac icons again.
    Android has no app badge for this, so it is skipped there."""
    from .websocket import _may_use, _store

    _, all_settings = await _store(hass)
    for user in await hass.auth.async_get_users():
        if not _may_use(entry, user):
            continue
        cfg = settings_of(all_settings, user.id)
        if not cfg["on"]:
            continue
        badge = unread_total(hass, user, entry, unread)
        for d in targets(hass, user.id, cfg, [])["app"]:
            if d["os"] in ("iOS", "iPadOS", "macOS"):
                await _call(hass, "notify", d["service"], {"message": "delete_alert", "data": {"push": {"badge": badge}}})


async def async_test(hass: HomeAssistant, user, all_settings: dict, draft: dict | None = None) -> dict[str, int]:
    """Test notification to this user's own devices (ignores the filters). `draft` = settings on screen, not saved yet.
    Returns how many devices it went to."""
    cfg = settings_of(all_settings, user.id)
    if isinstance(draft, dict):
        cfg = clean(draft, cfg)
    to = targets(hass, user.id, cfg, all_settings.get(user.id, {}).get("push") or [])
    app = 0
    for d in to["app"]:
        app += await _call(hass, "notify", d["service"], {
            "title": "Home-mail", "message": "Test notification",
            "data": {"tag": "homemail-test", "url": f"/{PANEL_URL}", "clickAction": f"/{PANEL_URL}"}}, keys=[f"app:{d['service']}"])
    web = 0
    if to["web"]:
        web = len(to["web"]) if await _call(hass, "html5", "send_message", {
            "title": "Home-mail", "message": "Test notification", "tag": "homemail-test", "data": {}},
            {"entity_id": to["web"]}, keys=[f"web:{x}" for x in to["web"]]) else 0
    return {"app": app, "web": web}
