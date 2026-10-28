"""Websocket API used by the app. Every command checks per account whether the HA user may use it:
the users chosen in the account's options, or (if none are chosen) every administrator."""

from __future__ import annotations

import asyncio
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
from homeassistant.helpers.storage import Store

from . import mail
from .const import (
    COLORS, DOMAIN, MAX_SENT_PER_HOUR, OPT_COLOR, OPT_NAME, OPT_SENDER, OPT_SENT_FOLDER, OPT_SIGNATURE, OPT_USERS,
    PROVIDERS, SIGNAL_UPDATE,
)
from .coordinator import account_cfg

_LOGGER = logging.getLogger(__name__)
EMAIL = re.compile(r"[^@\s<>,]+@[^@\s<>,]+\.[^@\s<>,]+")
USER_DEFAULTS = {"sender": "", "default": "", "bcc_me": False, "images": True}


class Unauthorized(Exception):
    """The HA user may not use this account."""


def async_register_websocket(hass: HomeAssistant) -> None:
    for handler in (ws_settings, ws_list, ws_mailboxes, ws_read, ws_action, ws_send, ws_contacts, ws_add_account, ws_subscribe):
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
                       "unread": (e.runtime_data.data or {}).get("unread", 0)}
    if s["default"] not in accounts:
        s["default"] = next(iter(accounts), "")
    return {**s, "accounts": accounts, "is_admin": user.is_admin, "user_name": user.name or ""}


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
            # options are applied live by the app; no reload needed
            hass.config_entries.async_update_entry(entry, options=opts)
    connection.send_result(msg["id"], await _settings(hass, user))


@websocket_api.websocket_command({
    vol.Required("type"): "homemail/list",
    vol.Optional("account", default="all"): str,
    vol.Optional("folder", default="INBOX"): str,
    vol.Optional("limit", default=50): vol.All(int, vol.Range(min=1, max=200)),
    vol.Optional("search"): str,
    vol.Optional("cached", default=False): bool,
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
    if msg["cached"]:
        if plain_inbox and entries and all(e.runtime_data.inbox is not None for e in entries):
            rows = [dict(r) for e in entries for r in e.runtime_data.inbox][-msg["limit"] * len(entries):]
            connection.send_result(msg["id"], {"messages": rows, "errors": [], "cached": True})
        else:
            connection.send_result(msg["id"], {"messages": None, "errors": [], "cached": True})
        return
    rows, errors = [], []
    for e in entries:
        try:
            part = await hass.async_add_executor_job(
                mail.list_messages, e.entry_id, account_cfg(e), msg["limit"], msg.get("search"), e.runtime_data.cache, folder)
        except Exception as err:  # noqa: BLE001
            errors.append(f"{e.options.get(OPT_NAME) or e.title}: {_err(err)}"[:160])
            continue
        if plain_inbox and msg["limit"] >= 50:
            e.runtime_data.inbox = [dict(r) for r in part]
        rows += part
    connection.send_result(msg["id"], {"messages": rows, "errors": errors})


@websocket_api.websocket_command({vol.Required("type"): "homemail/mailboxes", vol.Optional("cached", default=False): bool})
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
            folders = await hass.async_add_executor_job(mail.mailboxes, account_cfg(e))
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
    r = await _run(hass, connection, msg, mail.send, cfg, sender, to, cc, msg["subject"], msg["body"],
                   msg.get("original_uid"), msg["mode"], sent_folder, bcc, msg["folder"], msg["language"])
    if r is not None:
        sent.append(now)
        connection.send_result(msg["id"], r)


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
        connection.send_result(msg["id"], {"ok": True, "account": step["result"].entry_id})
        return
    if step["type"] == "form":
        flow.async_abort(step["flow_id"])
    connection.send_error(msg["id"], "invalid", (step.get("errors") or {}).get("base") or step.get("reason") or "failed")


@websocket_api.websocket_command({vol.Required("type"): "homemail/subscribe"})
@callback
def ws_subscribe(hass, connection, msg) -> None:
    """Pushes {account, unread, total} whenever an inbox counter changes (and once right away)."""
    user = connection.user

    def payload(account: str | None = None) -> dict:
        unread = {k: (e.runtime_data.data or {}).get("unread", 0) for k, e in _accounts(hass, user).items()}
        return {"account": account, "unread": unread, "total": sum(unread.values())}

    @callback
    def forward(account: str, _unread: int) -> None:
        if account in _accounts(hass, user):
            connection.send_message(websocket_api.event_message(msg["id"], payload(account)))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, forward)
    connection.send_result(msg["id"])
    connection.send_message(websocket_api.event_message(msg["id"], payload()))
