"""Home-mail: your own mail app inside Home Assistant.

Home Assistant fetches the mail (IMAP) and sends it (SMTP); the phone only shows it. Each config entry is
one mail account. The app talks to Home Assistant over the websocket API (websocket.py) and is served as a
sidebar panel, a Lovelace card (custom:homemail-card) and a stand-alone web app (/homemail-files/app.html).
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import actions, issues
from .const import DOMAIN, OPT_PUSH, PANEL_ELEMENT, PANEL_URL, URL_FILES, VERSION
from .coordinator import HomemailCoordinator
from .idle import IdleWatcher
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type HomemailConfigEntry = ConfigEntry[HomemailCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Static files, Lovelace card and websocket commands (once, for all accounts)."""
    hass.data.setdefault(DOMAIN, {"panel": False, "sent": []})
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_FILES, str(Path(__file__).parent / "frontend"), cache_headers=False)]
    )
    frontend.add_extra_js_url(hass, f"{URL_FILES}/homemail-card.js?v={VERSION}")
    async_register_websocket(hass)
    actions.async_setup(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HomemailConfigEntry) -> bool:
    coordinator = HomemailCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    if entry.options.get(OPT_PUSH, True):
        coordinator.idle = IdleWatcher(coordinator)
        coordinator.idle.start()
        entry.async_on_unload(coordinator.idle.stop)
    issues.check_access(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_options_changed))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.data[DOMAIN]["panel"]:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="Home-mail",
            sidebar_icon="mdi:email-outline",
            module_url=f"{URL_FILES}/homemail-card.js?v={VERSION}",
            require_admin=False,
        )
        hass.data[DOMAIN]["panel"] = True
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomemailConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    others = [e for e in hass.config_entries.async_entries(DOMAIN)
              if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED]
    if ok and not others and hass.data[DOMAIN]["panel"]:
        frontend.async_remove_panel(hass, PANEL_URL)
        hass.data[DOMAIN]["panel"] = False
    return ok


async def _options_changed(hass: HomeAssistant, entry: HomemailConfigEntry) -> None:
    """Options changed in the app (no reload needed): keep the repair notice about access up to date."""
    issues.check_access(hass, entry)


async def async_remove_entry(hass: HomeAssistant, entry: HomemailConfigEntry) -> None:
    issues.remove_all(hass, entry)
