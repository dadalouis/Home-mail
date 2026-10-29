"""Diagnostics download (Settings > Devices & services > Home-mail > Download diagnostics). Passwords and addresses are left out."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACT = {"password", "email", "signature", "sender_name"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    co = entry.runtime_data
    sent = hass.data.get(DOMAIN, {}).get("delivery", {})
    return {
        "data": async_redact_data(dict(entry.data), REDACT),
        "options": async_redact_data(dict(entry.options), REDACT),
        "inbox": co.data,
        "check_every_seconds": int(co.update_interval.total_seconds()) if co.update_interval else None,
        "last_update_success": co.last_update_success,
        "instant_new_mail": {"state": co.idle.state, "error": co.idle.error} if co.idle else {"state": "off"},
        "notified_messages_waiting_to_clear": len(co.notified),
        "cached_bodies": len(co.bodies),
        "notification_results": {k: {"ok": v["ok"], "error": v["error"]} for k, v in sent.items()},
    }
