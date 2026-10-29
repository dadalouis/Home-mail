"""Websocket API used by the app. Every command checks per account whether the HA user may use it:
the users chosen in the account's options, or (if none are chosen) every administrator."""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import re
import time
from typing import Any

import voluptuous as vol

from homeassistant.auth.models import User
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from . import mail, notify
from .const import (
    COLORS, DOMAIN, MAX_SENT_PER_HOUR, OPT_COLOR, OPT_NAME, OPT_SENDER, OPT_SENT_FOLDER, OPT_SIGNATURE, OPT_USERS,
    PROVIDERS, SIGNAL_UPDATE, URL_FILES,
)
from .coordinator import account_cfg

_LOGGER = logging.getLogger(__name__)
EMAIL = re.compile(r"[^@\s<>,]+@[^@\s<>,]+\.[^@\s<>,]+")
CHUNK = 384 * 1024  # bytes per websocket message when downloading or uploading a file
MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 25 * 1024 * 1024  # all attachments of one message (providers refuse more)
CTYPE = re.compile(r"^[\w.+-]+/[\w.+-]+$")
HTML5_REGISTRATIONS = "html5_push_registrations.conf"  # where the html5 integration keeps web push registrations
SINCE = vol.All(str, vol.Match(r"^(\d{4}-\d{2}-\d{2})?$"))  # a web app's period: only mail from this day on ("" = all)
USER_DEFAULTS = {"sender": "", "default": "", "bcc_me": False, "images": True}


class Unauthorized(Exception):
    """The HA user may not use this account."""


def async_register_websocket(hass: HomeAssistant) -> None:
    for handler in (ws_settings, ws_list, ws_mailboxes, ws_read, ws_action, ws_send, ws_contacts, ws_add_account, ws_subscribe,
                    ws_push_register, ws_push_check, ws_web_window, ws_push_remove, ws_notify_test, ws_attachment, ws_upload, ws_upload_remove):
        websocket_api.async_register_command(hass, handler)


# ---------- helpers ----------

def _may_use(entry: ConfigEntry, user: User | None) -> bool:
    if user is None or user.system_generated or not user.is_active:
        return False
    allowed = entry.options.get(OPT_USERS) or []
    return user.id in allowed if allowed else user.is_admin


def _accounts(hass: HomeAssistant, user: User | None) -> dict[str, ConfigEntry]:
    return {e.entry_id: e for e in hass.config_entries.async_entries(DOMAIN)
            if e.state is ConfigEntryState.LOADED and _may_use(e, user)}


def _account(hass: HomeAssistant, connection, account: str) -> ConfigEntry:
    entry = _accounts(hass, connection.user).get(account)
    if entry is None:
        raise Unauthorized("unauthorized")
    return entry


async def _store(hass: HomeAssistant) -> tuple[Store, dict]:
    data = hass.data[DOMAIN]
    if "store" not in data:
        data["store"] = Store(hass, 1, f"{DOMAIN}.settings")
        data["settings"] = await data["store"].async_load() or {}
    return data["store"], data["settings"]


def _app_urls(hass: HomeAssistant) -> dict[str, str]:
    """Addresses of the web app: the external (https when possible) one first, plus the one at home."""
    urls: dict[str, str] = {}
    for key, kwargs in (("external", {"allow_internal": False, "prefer_cloud": True}), ("internal", {"allow_external": False})):
        try:
            urls[key] = get_url(hass, **kwargs).rstrip("/") + f"{URL_FILES}/app.html"
        except NoURLAvailableError:
            pass
    return urls


async def _settings(hass: HomeAssistant, user: User) -> dict[str, Any]:
    """Settings as the app sees them: per-user options plus the accounts this user may use."""
    _, all_settings = await _store(hass)
    s = {**USER_DEFAULTS, **all_settings.get(user.id, {})}
    accounts = {}
    for i, (k, e) in enumerate(_accounts(hass, user).items()):
        o = e.options
        accounts[k] = {"name": o.get(OPT_NAME) or e.title, "sender": o.get(OPT_SENDER) or s["sender"],
                       "color": o.get(OPT_COLOR) or COLORS[i % len(COLORS)],
                       "signature": o.get(OPT_SIGNATURE, ""), "address": e.data["email"],
                       "unread": (e.runtime_data.data or {}).get("unread", 0),
                       "users": list(o.get(OPT_USERS) or []),  # empty = every administrator
                       "push": e.runtime_data.idle.state if e.runtime_data.idle else "off",
                       "interval": int(e.runtime_data.update_interval.total_seconds()) if e.runtime_data.update_interval else 0}
    if s["default"] not in accounts:
        s["default"] = next(iter(accounts), "")
    ncfg = notify.settings_of(all_settings, user.id)
    sent = notify.delivery(hass)
    out = {**s, "accounts": accounts, "is_admin": user.is_admin, "user_name": user.name or "", "user_id": user.id,
           "app_urls": _app_urls(hass), "notify": ncfg,
           # where notifications go, with the last result per device (memory only, since the last restart)
           "notify_devices": [{**d, "last": sent.get(f"app:{d['service']}")} for d in notify.app_devices(hass, user.id)],
           "notify_web_devices": [{**d, "last": sent.get(f"web:{d['entity_id']}")}
                                  for d in notify.web_devices(hass, s.get("push") or [])],
           "notify_web_names": list(s.get("push") or [])}
    out.pop("push", None)
    if user.is_admin:  # who may use which account is set by administrators
        out["ha_users"] = [{"id": u.id, "name": u.name or u.id} for u in await hass.auth.async_get_users()
                           if not u.system_generated and u.is_active]
    return out


def _err(err: Exception) -> str:
    if isinstance(err, mail.MailError):
        return err.code
    return f"{type(err).__name__}: {err}"[:160]


async def _run(hass, connection, msg, func, *args):
    try:
        return await hass.async_add_executor_job(func, *args)
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "mail_error", _err(err))
        return None


# ---------- commands ----------

@websocket_api.websocket_command({vol.Required("type"): "homemail/settings", vol.Optional("changes"): dict})
@websocket_api.async_response
async def ws_settings(hass, connection, msg) -> None:
    """Read or change settings. User options are per HA user; account options are shared (name, colour, signature)."""
    user = connection.user
    changes = msg.get("changes")
    if changes:
        store, all_settings = await _store(hass)
        mine = {**USER_DEFAULTS, **all_settings.get(user.id, {})}
        for k in ("sender", "default"):
            if isinstance(changes.get(k), str):
                mine[k] = changes[k][:200]
        for k in ("bcc_me", "images"):
            if k in changes:
                mine[k] = bool(changes[k])
        if isinstance(changes.get("notify"), dict):
            mine["notify"] = notify.clean(changes["notify"], mine.get("notify") or {})
        all_settings[user.id] = mine
        store.async_delay_save(lambda: all_settings, 1)
        for acc, w in (changes.get("accounts") or {}).items():
            entry = _accounts(hass, user).get(acc)
            if entry is None or not isinstance(w, dict):
                continue
            opts = dict(entry.options)
            for k, opt in (("name", OPT_NAME), ("sender", OPT_SENDER), ("color", OPT_COLOR), ("signature", OPT_SIGNATURE)):
                if isinstance(w.get(k), str):
                    opts[opt] = w[k][:2000]
            if user.is_admin and isinstance(w.get("users"), list):
                known = {u.id for u in await hass.auth.async_get_users()}
                opts[OPT_USERS] = [x for x in w["users"] if isinstance(x, str) and x in known]
            # options are applied live by the app; no reload needed
            hass.config_entries.async_update_entry(entry, options=opts)
    connection.send_result(msg["id"], await _settings(hass, user))


@websocket_api.websocket_command({vol.Required("type"): "homemail/push_register", vol.Required("name"): vol.All(str, vol.Length(min=1, max=100)),
                                   vol.Optional("endpoint"): vol.All(str, vol.Length(max=2000))})
@websocket_api.async_response
async def ws_push_register(hass, connection, msg) -> None:
    """The web app registered for web push (html5): remember the registration for this user.
    html5 files a subscription it already knows under its old name, so the name is looked up by endpoint.
    html5 only makes a notify entity for a new registration when it is (re)loaded, so that is done here."""
    regs = await hass.async_add_executor_job(_html5_registrations, hass)
    name = next((n for n, r in regs.items() if msg.get("endpoint") and (r.get("subscription") or {}).get("endpoint") == msg["endpoint"]),
                msg["name"])
    store, all_settings = await _store(hass)
    mine = {**USER_DEFAULTS, **all_settings.get(connection.user.id, {})}
    # registrations html5 no longer has (removed home-screen apps, expired subscriptions) go too
    mine["push"] = [*[n for n in (mine.get("push") or []) if n != name and (not regs or n in regs)], name][-10:]
    all_settings[connection.user.id] = mine
    store.async_delay_save(lambda: all_settings, 1)
    if not notify.web_devices(hass, [name]):
        for e in hass.config_entries.async_entries("html5"):
            await hass.config_entries.async_reload(e.entry_id)
    connection.send_result(msg["id"], {"ok": True, "name": name})


WINDOW = vol.Schema({vol.Optional("all"): bool, vol.Optional("n"): vol.All(int, vol.Range(min=0, max=36500)),
                     vol.Optional("unit"): vol.In(["d", "w", "m", "y"])})


@websocket_api.websocket_command({vol.Required("type"): "homemail/web_window", vol.Required("endpoint"): vol.All(str, vol.Length(max=2000)),
                                   vol.Required("window"): WINDOW})
@websocket_api.async_response
async def ws_web_window(hass, connection, msg) -> None:
    """The period of mail this web app shows: remembered per registration, so its red number counts the same."""
    regs = await hass.async_add_executor_job(_html5_registrations, hass)
    name = next((n for n, r in regs.items() if (r.get("subscription") or {}).get("endpoint") == msg["endpoint"]), None)
    if name:
        store, all_settings = await _store(hass)
        mine = {**USER_DEFAULTS, **all_settings.get(connection.user.id, {})}
        mine["windows"] = {k: v for k, v in (mine.get("windows") or {}).items() if k in regs} | {name: dict(msg["window"])}
        all_settings[connection.user.id] = mine
        store.async_delay_save(lambda: all_settings, 1)
    connection.send_result(msg["id"], {"ok": bool(name)})


@websocket_api.websocket_command({vol.Required("type"): "homemail/push_check", vol.Required("endpoint"): vol.All(str, vol.Length(max=2000))})
@websocket_api.async_response
async def ws_push_check(hass, connection, msg) -> None:
    """Does this device still get notifications for this user? (The app offers to turn them on when not.)"""
    regs = await hass.async_add_executor_job(_html5_registrations, hass)
    name = next((n for n, r in regs.items() if (r.get("subscription") or {}).get("endpoint") == msg["endpoint"]), None)
    _, all_settings = await _store(hass)
    mine = all_settings.get(connection.user.id, {}).get("push") or []
    connection.send_result(msg["id"], {"ok": bool(name and name in mine and notify.web_devices(hass, [name]))})


def _html5_registrations(hass: HomeAssistant) -> dict[str, dict]:
    """The web push registrations html5 keeps (name -> registration); empty when it cannot be read."""
    try:
        data = load_json(hass.config.path(HTML5_REGISTRATIONS))
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


@websocket_api.websocket_command({vol.Required("type"): "homemail/push_remove", vol.Required("name"): str})
@websocket_api.async_response
async def ws_push_remove(hass, connection, msg) -> None:
    """Stop sending web push to one of your web app registrations (an old phone, a removed home-screen app)."""
    store, all_settings = await _store(hass)
    mine = all_settings.get(connection.user.id, {})
    mine["push"] = [n for n in (mine.get("push") or []) if n != msg["name"]]
    all_settings[connection.user.id] = mine
    store.async_delay_save(lambda: all_settings, 1)
    connection.send_result(msg["id"], await _settings(hass, connection.user))


@websocket_api.websocket_command({vol.Required("type"): "homemail/notify_test", vol.Optional("notify"): dict})
@websocket_api.async_response
async def ws_notify_test(hass, connection, msg) -> None:
    """Send a test notification to the devices of the logged-in user."""
    _, all_settings = await _store(hass)
    try:
        sent = await notify.async_test(hass, connection.user, all_settings, msg.get("notify"))
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "notify_error", _err(err))
        return
    connection.send_result(msg["id"], sent)


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/list",
    vol.Optional("account", default="all"): str,
    vol.Optional("folder", default="INBOX"): str,
    vol.Optional("limit", default=50): vol.All(int, vol.Range(min=1, max=200)),
    vol.Optional("search"): str,
    vol.Optional("cached", default=False): bool,
    vol.Optional("since"): SINCE,
})
@websocket_api.async_response
async def ws_list(hass, connection, msg) -> None:
    """Newest messages of a folder of one account, or of all inboxes ('all').
    cached=True: answer straight from the preloaded inbox list (instant; the app then asks again live)."""
    if msg["account"] == "all":
        entries = list(_accounts(hass, connection.user).values())
        folder = "INBOX"
    else:
        try:
            entries = [_account(hass, connection, msg["account"])]
        except Unauthorized:
            connection.send_error(msg["id"], "unauthorized", "unauthorized")
            return
        folder = msg["folder"] or "INBOX"
    plain_inbox = folder == "INBOX" and not msg.get("search")
    since = msg.get("since") or None
    if msg["cached"]:
        if plain_inbox and entries and all(e.runtime_data.inbox is not None for e in entries):
            rows = [dict(r) for e in entries for r in e.runtime_data.inbox
                    if not since or (r.get("date") or "")[:10] >= since][-msg["limit"] * len(entries):]
            connection.send_result(msg["id"], {"messages": rows, "errors": [], "cached": True})
        else:
            connection.send_result(msg["id"], {"messages": None, "errors": [], "cached": True})
        return
    rows, errors = [], []
    # all accounts at the same time: opening All Inboxes waits for the slowest server, not for the sum
    parts = await asyncio.gather(*(hass.async_add_executor_job(
        mail.list_messages, e.entry_id, account_cfg(e), msg["limit"], msg.get("search"), e.runtime_data.cache, folder, since)
        for e in entries), return_exceptions=True)
    for e, part in zip(entries, parts):
        if isinstance(part, Exception):
            errors.append(f"{e.options.get(OPT_NAME) or e.title}: {_err(part)}"[:160])
            continue
        if plain_inbox and msg["limit"] >= 50 and not since:
            e.runtime_data.inbox = [dict(r) for r in part]
        rows += part
    connection.send_result(msg["id"], {"messages": rows, "errors": errors})


@websocket_api.websocket_command({vol.Required("type"): "homemail/mailboxes", vol.Optional("cached", default=False): bool,
                                   vol.Optional("since"): SINCE})
@websocket_api.async_response
async def ws_mailboxes(hass, connection, msg) -> None:
    """All folders with counters, per account (accounts in parallel).
    cached=True: the last known result at once (None if there is none yet); the app then asks again live."""
    entries = _accounts(hass, connection.user)
    if msg["cached"]:
        known = all(e.runtime_data.mailboxes is not None for e in entries.values())
        connection.send_result(msg["id"], {"accounts": [
            {"account": k, "name": e.options.get(OPT_NAME) or e.title, "folders": e.runtime_data.mailboxes}
            for k, e in entries.items()] if known and entries else None, "errors": [], "cached": True})
        return

    async def one(k: str, e: ConfigEntry) -> tuple[dict, str | None]:
        try:
            folders = await hass.async_add_executor_job(mail.mailboxes, account_cfg(e), msg.get("since") or None)
            if not msg.get("since"):
                e.runtime_data.mailboxes = folders
            error = None
        except Exception as err:  # noqa: BLE001
            folders, error = [], f"{e.options.get(OPT_NAME) or e.title}: {_err(err)}"[:160]
        return {"account": k, "name": e.options.get(OPT_NAME) or e.title, "folders": folders}, error

    results = await asyncio.gather(*(one(k, e) for k, e in entries.items()))
    connection.send_result(msg["id"], {"accounts": [r for r, _ in results], "errors": [x for _, x in results if x]})


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/read",
    vol.Required("account"): str,
    vol.Required("uid"): vol.Coerce(str),
    vol.Optional("folder", default="INBOX"): str,
    vol.Optional("mark", default=True): bool,
})
@websocket_api.async_response
async def ws_read(hass, connection, msg) -> None:
    try:
        e = _account(hass, connection, msg["account"])
    except Unauthorized:
        connection.send_error(msg["id"], "unauthorized", "unauthorized")
        return
    co = e.runtime_data
    hit = co.bodies.get((msg["folder"], msg["uid"]))
    if hit is not None:  # preloaded: answer at once, mark as read in the background
        connection.send_result(msg["id"], hit)
        if msg["mark"]:
            co.forget(msg["folder"], msg["uid"], seen=True)
            try:
                await hass.async_add_executor_job(mail.action, account_cfg(e), msg["uid"], "seen", msg["folder"])
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Marking as read failed: %s", err)
            await co.async_request_refresh()
        return
    r = await _run(hass, connection, msg, mail.read_message, account_cfg(e), msg["uid"], msg["mark"], msg["folder"])
    if r is not None:
        connection.send_result(msg["id"], r)
        co.put_body(msg["folder"], msg["uid"], r)
        if msg["mark"]:
            co.forget(msg["folder"], msg["uid"], seen=True)
            await co.async_request_refresh()


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/action",
    vol.Required("account"): str,
    vol.Required("uid"): vol.Coerce(str),
    vol.Required("action"): vol.In(mail.ACTIONS),
    vol.Optional("folder", default="INBOX"): str,
})
@websocket_api.async_response
async def ws_action(hass, connection, msg) -> None:
    try:
        e = _account(hass, connection, msg["account"])
    except Unauthorized:
        connection.send_error(msg["id"], "unauthorized", "unauthorized")
        return
    r = await _run(hass, connection, msg, mail.action, account_cfg(e), msg["uid"], msg["action"], msg["folder"])
    if r is not None:
        connection.send_result(msg["id"], r)
        act = msg["action"]
        if act in ("archive", "delete", "inbox"):
            e.runtime_data.forget(msg["folder"], msg["uid"], gone=True)
        else:
            e.runtime_data.forget(msg["folder"], msg["uid"], **({"seen": act == "seen"} if act in ("seen", "unseen") else {"flagged": act == "flag"}))
        await e.runtime_data.async_request_refresh()


def _addresses(x) -> list[str]:
    items = x if isinstance(x, list) else str(x or "").replace(";", ",").split(",")
    return [a.strip() for a in items if str(a).strip()]


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/send",
    vol.Required("account"): str,
    vol.Required("to"): vol.Any(list, str),
    vol.Optional("cc", default=[]): vol.Any(list, str),
    vol.Optional("subject", default=""): str,
    vol.Optional("body", default=""): str,
    vol.Optional("original_uid"): vol.Any(None, vol.Coerce(str)),
    vol.Optional("mode", default="new"): vol.In(["new", "reply", "reply_all", "forward"]),
    vol.Optional("folder", default="INBOX"): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("attachments", default=[]): [str],
})
@websocket_api.async_response
async def ws_send(hass, connection, msg) -> None:
    try:
        e = _account(hass, connection, msg["account"])
    except Unauthorized:
        connection.send_error(msg["id"], "unauthorized", "unauthorized")
        return
    to, cc = _addresses(msg["to"]), _addresses(msg["cc"])
    if not to:
        connection.send_error(msg["id"], "invalid", "no_recipient")
        return
    if [a for a in to + cc if not EMAIL.fullmatch(a)]:
        connection.send_error(msg["id"], "invalid", "invalid_address")
        return
    sent: list = hass.data[DOMAIN]["sent"]
    now = time.time()
    sent[:] = [t for t in sent if now - t < 3600]
    if len(sent) >= MAX_SENT_PER_HOUR:
        connection.send_error(msg["id"], "limit", "rate_limit")
        return
    settings = await _settings(hass, connection.user)
    cfg = account_cfg(e)
    sent_folder = e.options.get(OPT_SENT_FOLDER) or (None if mail.is_gmail(cfg) else "AUTO")
    bcc = [cfg["email"]] if settings["bcc_me"] else []
    sender = e.options.get(OPT_SENDER) or settings["sender"]  # per account; older per-user setting as fallback
    uploads = hass.data[DOMAIN].setdefault("uploads", {})
    atts = []
    for fid in msg["attachments"]:
        up = uploads.get((connection.user.id, fid))
        if not up or not up["done"]:
            connection.send_error(msg["id"], "invalid", "attachment_missing")
            return
        atts.append((up["name"], up["type"], bytes(up["data"])))
    r = await _run(hass, connection, msg, mail.send, cfg, sender, to, cc, msg["subject"], msg["body"],
                   msg.get("original_uid"), msg["mode"], sent_folder, bcc, msg["folder"], msg["language"], atts)
    if r is not None:
        for fid in msg["attachments"]:
            uploads.pop((connection.user.id, fid), None)
        sent.append(now)
        connection.send_result(msg["id"], r)


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/attachment",
    vol.Required("account"): str,
    vol.Optional("folder", default="INBOX"): str,
    vol.Required("uid"): vol.Coerce(str),
    vol.Required("index"): vol.All(int, vol.Range(min=0, max=500)),
    vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0)),
})
@websocket_api.async_response
async def ws_attachment(hass, connection, msg) -> None:
    """One piece (base64) of an attachment; the app asks for the pieces one after the other."""
    try:
        e = _account(hass, connection, msg["account"])
    except Unauthorized:
        connection.send_error(msg["id"], "unauthorized", "unauthorized")
        return
    cache = hass.data[DOMAIN].setdefault("downloads", {})
    now = time.time()
    for k in [k for k, v in cache.items() if now - v[0] > 300]:
        del cache[k]
    key = (connection.user.id, msg["account"], msg["folder"], msg["uid"], msg["index"])
    hit = cache.get(key)
    if hit is None:
        got = await _run(hass, connection, msg, mail.get_attachment, account_cfg(e), msg["uid"], msg["folder"], msg["index"])
        if got is None:
            return
        hit = cache[key] = (now, *got)
        for k in sorted(cache, key=lambda k: cache[k][0])[:-3]:  # keep the last three in memory
            del cache[k]
    _, name, ctype, data = hit
    piece = data[msg["offset"]:msg["offset"] + CHUNK]
    connection.send_result(msg["id"], {"name": name, "type": ctype, "size": len(data),
                                       "data": base64.b64encode(piece).decode(), "eof": msg["offset"] + len(piece) >= len(data)})


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/upload",
    vol.Required("file"): vol.All(str, vol.Length(min=1, max=64)),
    vol.Required("name"): vol.All(str, vol.Length(min=1, max=300)),
    vol.Optional("ctype", default="application/octet-stream"): str,
    vol.Required("data"): str,
    vol.Optional("last", default=False): bool,
})
@websocket_api.async_response
async def ws_upload(hass, connection, msg) -> None:
    """A file for a message being written, in pieces (base64). It waits in memory until the message is sent."""
    uploads = hass.data[DOMAIN].setdefault("uploads", {})
    now = time.time()
    for k in [k for k, v in uploads.items() if now - v["ts"] > 1800]:
        del uploads[k]
    try:
        piece = base64.b64decode(msg["data"], validate=True)
    except (binascii.Error, ValueError):
        connection.send_error(msg["id"], "invalid", "invalid_data")
        return
    key = (connection.user.id, msg["file"])
    up = uploads.setdefault(key, {"name": msg["name"].replace("\\", "/").rsplit("/", 1)[-1][:200] or "file",
                                  "type": msg["ctype"] if CTYPE.match(msg["ctype"]) else "application/octet-stream",
                                  "data": bytearray(), "ts": now, "done": False})
    up["data"] += piece
    mine = sum(len(v["data"]) for k, v in uploads.items() if k[0] == connection.user.id)
    if len(up["data"]) > MAX_FILE or mine > MAX_TOTAL:
        uploads.pop(key, None)
        connection.send_error(msg["id"], "too_big", "too_big")
        return
    up["done"] = bool(msg["last"])
    connection.send_result(msg["id"], {"size": len(up["data"])})


@websocket_api.websocket_command({vol.Required("type"): "homemail/upload_remove", vol.Required("file"): str})
@websocket_api.async_response
async def ws_upload_remove(hass, connection, msg) -> None:
    hass.data[DOMAIN].setdefault("uploads", {}).pop((connection.user.id, msg["file"]), None)
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): "homemail/contacts"})
@websocket_api.async_response
async def ws_contacts(hass, connection, msg) -> None:
    """Known addresses from all accounts of this user (cached for an hour, memory only)."""
    cache = hass.data[DOMAIN].setdefault("contacts", {})
    out: dict[str, str] = {}
    for k, e in _accounts(hass, connection.user).items():
        hit = cache.get(k)
        if not hit or time.time() - hit[0] > 3600:
            try:
                hit = (time.time(), await hass.async_add_executor_job(mail.contacts, account_cfg(e)))
                cache[k] = hit
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Contacts for %s failed: %s", k, err)
                continue
        for c in hit[1]:
            if c["address"] not in out or (c["name"] and not out[c["address"]]):
                out[c["address"]] = c["name"]
    connection.send_result(msg["id"], {"contacts": [{"address": a, "name": n} for a, n in out.items()]})


@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "homemail/add_account",
    vol.Required("provider"): vol.In(list(PROVIDERS)),
    vol.Optional("name", default=""): str,
    vol.Required("email"): str,
    vol.Required("password"): str,
    vol.Optional("imap_server"): str,
    vol.Optional("imap_port"): int,
    vol.Optional("smtp_server"): str,
    vol.Optional("smtp_port"): int,
})
@websocket_api.async_response
async def ws_add_account(hass, connection, msg) -> None:
    """Add an account from the app: runs the same config flow as Settings > Integrations (admins only)."""
    flow = hass.config_entries.flow
    step = await flow.async_init(DOMAIN, context={"source": "user"})
    step = await flow.async_configure(step["flow_id"], {"provider": msg["provider"]})
    fields = {k: msg[k] for k in ("name", "email", "password", "imap_server", "imap_port", "smtp_server", "smtp_port") if k in msg}
    try:
        step = await flow.async_configure(step["flow_id"], fields)
    except vol.Invalid as err:
        flow.async_abort(step["flow_id"])
        connection.send_error(msg["id"], "invalid", str(err))
        return
    if step["type"] == "create_entry":
        entry = step["result"]
        # whoever adds the account owns it: only they may use it until they share it
        hass.config_entries.async_update_entry(entry, options={**entry.options, OPT_USERS: [connection.user.id]})
        connection.send_result(msg["id"], {"ok": True, "account": entry.entry_id})
        return
    if step["type"] == "form":
        flow.async_abort(step["flow_id"])
    connection.send_error(msg["id"], "invalid", (step.get("errors") or {}).get("base") or step.get("reason") or "failed")


@websocket_api.websocket_command({vol.Required("type"): "homemail/subscribe", vol.Optional("since"): SINCE})
@callback
def ws_subscribe(hass, connection, msg) -> None:
    """Pushes {account, unread, total} whenever an inbox counter changes (and once right away).
    With `since` (a web app's period) the counters only count unread mail of that period."""
    user = connection.user
    since = msg.get("since") or None
    counts: dict[str, int] = {}

    async def send(account: str | None = None) -> None:
        entries = _accounts(hass, user)
        for k, e in entries.items():
            if since and (account in (None, k) or k not in counts):
                try:
                    counts[k] = await hass.async_add_executor_job(mail.unseen_since, account_cfg(e), since)
                except Exception:  # noqa: BLE001
                    counts.setdefault(k, (e.runtime_data.data or {}).get("unread", 0))
            elif not since:
                counts[k] = (e.runtime_data.data or {}).get("unread", 0)
        unread = {k: counts.get(k, 0) for k in entries}
        connection.send_message(websocket_api.event_message(msg["id"], {"account": account, "unread": unread, "total": sum(unread.values())}))

    @callback
    def forward(account: str, _unread: int) -> None:
        if account in _accounts(hass, user):
            hass.async_create_task(send(account))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, forward)
    connection.send_result(msg["id"])
    hass.async_create_task(send())
