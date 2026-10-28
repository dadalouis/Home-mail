"""Built-in notifications for new mail: Companion app and web app, per Home Assistant user."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util, slugify

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
    "app": True,  # Companion app
    "web": True,  # web app (html5 push)
    "devices_off": [],  # Companion devices (names) that do not notify
}
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def clean(raw: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    """Apply changes from the app on the stored notification settings (unknown or invalid values are ignored)."""
    out = {**NOTIFY_DEFAULTS, **old}
    for k in ("on", "quiet_on", "preview", "sound", "app", "web"):
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
    """Companion app devices of this user: [{name, service}]."""
    out = []
    for e in hass.config_entries.async_entries("mobile_app"):
        if e.data.get("user_id") != user_id:
            continue
        name = e.data.get("device_name") or e.title
        service = f"mobile_app_{slugify(name)}"
        if hass.services.has_service("notify", service):
            out.append({"name": name, "service": service})
    return out


def web_entities(hass: HomeAssistant, names: list[str]) -> list[str]:
    """notify entities (html5) for the registrations this user made in the web app."""
    if not names or not hass.services.has_service("html5", "send_message"):
        return []
    wanted_ids = {f"_{n}_device" for n in names}
    reg = er.async_get(hass)
    return [e.entity_id for e in reg.entities.values()
            if e.platform == "html5" and e.domain == "notify" and not e.disabled
            and any((e.unique_id or "").endswith(w) for w in wanted_ids)]


def targets(hass: HomeAssistant, user_id: str, cfg: dict[str, Any], web_names: list[str]) -> dict[str, Any]:
    app = [d for d in app_devices(hass, user_id) if d["name"] not in cfg["devices_off"]] if cfg["app"] else []
    web = web_entities(hass, web_names) if cfg["web"] else []
    return {"app": app, "web": web}


def tag_for(entry: ConfigEntry, uid: str) -> str:
    return f"homemail-{entry.entry_id}-{uid}"


# ---------- sending ----------

async def _send(hass: HomeAssistant, entry: ConfigEntry, m: dict[str, Any], unread: int, cfg: dict[str, Any],
                to: dict[str, Any], account_label: str | None) -> None:
    sender = m.get("name") or m.get("address") or "Home-mail"
    title = f"{sender} · {account_label}" if account_label else sender
    subject = m.get("subject") or "(no subject)"
    preview = (m.get("preview") or "").strip()
    message = f"{subject}\n{preview}" if cfg["preview"] and preview else subject
    tag = tag_for(entry, m["uid"])
    group = f"homemail-{entry.entry_id}"
    for d in to["app"]:
        data = {"group": group, "tag": tag, "url": f"/{PANEL_URL}", "clickAction": f"/{PANEL_URL}",
                "push": {"badge": unread, "thread-id": group, **({} if cfg["sound"] else {"sound": "none"})},
                "ttl": 0, "priority": "high"}
        await hass.services.async_call("notify", d["service"], {"title": title, "message": message, "data": data})
    if to["web"]:
        payload = {"title": title, "message": message, "tag": tag,
                   "data": {"message_id": m.get("message_id") or "", "unread": unread}}
        if not cfg["sound"]:
            payload["silent"] = True
        await hass.services.async_call("html5", "send_message", payload, target={"entity_id": to["web"]})


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
            await _send(hass, entry, m, unread, cfg, to, label)
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
        try:
            for d in to["app"]:
                await hass.services.async_call("notify", d["service"], {"message": "clear_notification", "data": {"tag": tag}})
            if to["web"] and hass.services.has_service("html5", "dismiss_message"):
                await hass.services.async_call("html5", "dismiss_message", {"tag": tag}, target={"entity_id": to["web"]})
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Clearing notification failed: %s", err)


async def async_test(hass: HomeAssistant, user, all_settings: dict) -> dict[str, int]:
    """Test notification to this user's own devices (ignores the filters). Returns how many devices it went to."""
    cfg = settings_of(all_settings, user.id)
    to = targets(hass, user.id, {**cfg, "devices_off": cfg["devices_off"]}, all_settings.get(user.id, {}).get("push") or [])
    for d in to["app"]:
        await hass.services.async_call("notify", d["service"], {
            "title": "Home-mail", "message": "Test notification",
            "data": {"tag": "homemail-test", "url": f"/{PANEL_URL}", "clickAction": f"/{PANEL_URL}"}})
    if to["web"]:
        await hass.services.async_call("html5", "send_message", {
            "title": "Home-mail", "message": "Test notification", "tag": "homemail-test", "data": {}},
            target={"entity_id": to["web"]})
    return {"app": len(to["app"]), "web": len(to["web"])}
