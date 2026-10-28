"""Config flow: one entry per mail account. Login is tested (IMAP + SMTP) before saving."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import mail
from .const import (
    COLORS, CONF_IMAP_PORT, CONF_IMAP_SERVER, CONF_PROVIDER, CONF_SMTP_PORT, CONF_SMTP_SERVER,
    DEFAULT_SCAN_INTERVAL, DOMAIN, OPT_COLOR, OPT_NAME, OPT_SCAN_INTERVAL, OPT_SENDER, OPT_SENT_FOLDER,
    OPT_SIGNATURE, OPT_USERS, PROVIDERS,
)

try:  # HA 2025.8+
    from homeassistant.config_entries import OptionsFlowWithReload as _OptionsBase
except ImportError:  # pragma: no cover
    _OptionsBase = OptionsFlow


def _clean_password(provider: str, password: str) -> str:
    # Google shows app passwords as 'abcd efgh ijkl mnop'; the spaces are not part of it.
    return password.replace(" ", "") if provider == "gmail" else password.strip()


APP_PASSWORD_HELP = {
    "gmail": ("https://myaccount.google.com/signinoptions/twosv", "https://myaccount.google.com/apppasswords"),
    "icloud": ("https://account.apple.com/account/manage", "https://account.apple.com/account/manage"),
}


def _needs_app_password(provider: str, password: str) -> bool:
    """Gmail app passwords are 16 letters, iCloud ones xxxx-xxxx-xxxx-xxxx. Anything else was the normal password."""
    if provider == "gmail":
        return not (len(password) == 16 and password.isalpha())
    if provider == "icloud":
        return len(password.replace("-", "")) != 16
    return False


class HomepostConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._provider = "gmail"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HomepostOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            return await self.async_step_account()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_PROVIDER, default="gmail"): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=list(PROVIDERS), translation_key="provider",
                                                  mode=selector.SelectSelectorMode.LIST)
                ),
            }),
        )

    async def async_step_account(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        other = self._provider == "other"
        imap, imap_port, smtp, smtp_port = PROVIDERS[self._provider]
        if user_input is not None:
            address = user_input["email"].strip().lower()
            data = {
                CONF_PROVIDER: self._provider,
                "email": address,
                "password": _clean_password(self._provider, user_input["password"]),
                CONF_IMAP_SERVER: user_input.get(CONF_IMAP_SERVER, imap).strip().lower(),
                CONF_IMAP_PORT: int(user_input.get(CONF_IMAP_PORT, imap_port)),
                CONF_SMTP_SERVER: user_input.get(CONF_SMTP_SERVER, smtp).strip().lower(),
                CONF_SMTP_PORT: int(user_input.get(CONF_SMTP_PORT, smtp_port)),
            }
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            error = await self.hass.async_add_executor_job(mail.test_account, data)
            if error == "invalid_auth_imap" and _needs_app_password(self._provider, data["password"]):
                error = "app_password_required"
            if error:
                errors["base"] = error
            else:
                name = (user_input.get(OPT_NAME) or "").strip() or address
                used = len(self._async_current_entries())
                return self.async_create_entry(title=name, data=data, options={
                    OPT_NAME: name, OPT_SENDER: "", OPT_COLOR: COLORS[used % len(COLORS)], OPT_SIGNATURE: "",
                    OPT_SENT_FOLDER: "", OPT_USERS: [], OPT_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                })
        schema: dict = {
            vol.Optional(OPT_NAME): str,
            vol.Required("email"): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)),
            vol.Required("password"): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        }
        if other:
            schema.update({
                vol.Required(CONF_IMAP_SERVER): str,
                vol.Required(CONF_IMAP_PORT, default=993): int,
                vol.Required(CONF_SMTP_SERVER): str,
                vol.Required(CONF_SMTP_PORT, default=465): int,
            })
        return self.async_show_form(
            step_id="account_app" if self._provider in APP_PASSWORD_HELP else "account", data_schema=self.add_suggested_values_to_schema(vol.Schema(schema), user_input or {}),
            errors=errors, description_placeholders={
                "provider": self._provider,
                "step1": APP_PASSWORD_HELP.get(self._provider, ("", ""))[0],
                "step2": APP_PASSWORD_HELP.get(self._provider, ("", ""))[1],
            },
        )

    async def async_step_account_app(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Same as account, with the step-by-step app password help (Gmail, iCloud)."""
        return await self.async_step_account(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, "password": _clean_password(entry.data.get(CONF_PROVIDER, ""), user_input["password"])}
            error = await self.hass.async_add_executor_job(mail.test_account, data)
            if error == "invalid_auth_imap" and _needs_app_password(data.get(CONF_PROVIDER, ""), data["password"]):
                error = "app_password_required"
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))}),
            errors=errors, description_placeholders={"email": entry.data["email"]},
        )


class HomepostOptionsFlow(_OptionsBase):
    """Display name, colour, signature, sent folder, who may use this account, poll interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        users = [u for u in await self.hass.auth.async_get_users() if not u.system_generated and u.is_active]
        o = self.config_entry.options
        schema = vol.Schema({
            vol.Required(OPT_NAME, default=o.get(OPT_NAME, self.config_entry.title)): str,
            vol.Optional(OPT_SENDER, default=o.get(OPT_SENDER, "")): str,
            vol.Required(OPT_COLOR, default=o.get(OPT_COLOR, COLORS[0])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=COLORS, custom_value=True)),
            vol.Optional(OPT_SIGNATURE, default=o.get(OPT_SIGNATURE, "")): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)),
            vol.Optional(OPT_SENT_FOLDER, default=o.get(OPT_SENT_FOLDER, "")): str,
            vol.Optional(OPT_USERS, default=o.get(OPT_USERS, [])): selector.SelectSelector(
                selector.SelectSelectorConfig(options=[selector.SelectOptionDict(value=u.id, label=u.name or u.id) for u in users],
                                              multiple=True)),
            vol.Required(OPT_SCAN_INTERVAL, default=o.get(OPT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=30, max=3600, step=10, unit_of_measurement="s",
                                              mode=selector.NumberSelectorMode.BOX)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
