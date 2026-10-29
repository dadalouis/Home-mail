"""Repair notices in Home Assistant (Settings > Repairs) for things the owner should know about."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, OPT_NAME, OPT_USERS


def _name(entry: ConfigEntry) -> str:
    return entry.options.get(OPT_NAME) or entry.title


def check_access(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Nobody chosen for an account means every administrator can read it: say so until someone is chosen."""
    issue_id = f"shared_with_admins_{entry.entry_id}"
    if entry.options.get(OPT_USERS):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(hass, DOMAIN, issue_id, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                          translation_key="shared_with_admins", translation_placeholders={"account": _name(entry)})


def idle_failing(hass: HomeAssistant, entry: ConfigEntry, failing: bool, error: str = "") -> None:
    """Instant new mail (IMAP IDLE) keeps failing: Home-mail falls back to checking, but the owner may want to know."""
    issue_id = f"idle_failing_{entry.entry_id}"
    if not failing:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(hass, DOMAIN, issue_id, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                          translation_key="idle_failing", translation_placeholders={"account": _name(entry), "error": error or "?"})


def remove_all(hass: HomeAssistant, entry: ConfigEntry) -> None:
    for issue_id in (f"shared_with_admins_{entry.entry_id}", f"idle_failing_{entry.entry_id}"):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
