"""UI setup, optional legacy import, options, reconfigure and reauthentication."""

import json
from pathlib import Path

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CommaxClient
from .const import (
    CONF_FANS,
    CONF_LIGHTS,
    CONF_POLL_SECONDS,
    CONF_PROXY_PASSWORD,
    CONF_PROXY_URL,
    CONF_PROXY_USERNAME,
    CONF_TARGET_URL,
    DEFAULT_POLL_SECONDS,
    DOMAIN,
    LEGACY_CONNECTION_FILE,
)
from .models import ConnectionConfig, validate_channels
from .protocol import AuthenticationError, CommaxError


def connection_schema(defaults=None, *, credentials_only=False):
    defaults = defaults or {}
    fields = {}
    if not credentials_only:
        fields.update(
            {
                vol.Required(CONF_PROXY_URL, default=defaults.get(CONF_PROXY_URL, "")): str,
                vol.Required(CONF_TARGET_URL, default=defaults.get(CONF_TARGET_URL, "")): str,
            }
        )
    fields[vol.Required(CONF_PROXY_USERNAME, default=defaults.get(CONF_PROXY_USERNAME, ""))] = str
    fields[vol.Required(CONF_PROXY_PASSWORD)] = selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )
    return vol.Schema(fields)


def channel_schema(defaults=None):
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_LIGHTS, default=defaults.get(CONF_LIGHTS, "")): str,
            vol.Required(CONF_FANS, default=defaults.get(CONF_FANS, "")): str,
            vol.Required(
                CONF_POLL_SECONDS, default=defaults.get(CONF_POLL_SECONDS, DEFAULT_POLL_SECONDS)
            ): vol.All(vol.Coerce(int), vol.Range(min=15, max=300)),
        }
    )


class CommaxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._connection = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CommaxOptionsFlow()

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["manual", "legacy"])

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self._connection = ConnectionConfig.from_mapping(user_input)
            except (KeyError, ValueError, TypeError):
                errors["base"] = "invalid_connection"
            else:
                return await self.async_step_channels()
        return self.async_show_form(
            step_id="manual", data_schema=connection_schema(user_input), errors=errors
        )

    async def async_step_legacy(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = await self.hass.async_add_executor_job(
                    lambda: json.loads(
                        Path(self.hass.config.path(LEGACY_CONNECTION_FILE)).read_text()
                    )
                )
                self._connection = ConnectionConfig.from_mapping(data)
            except OSError:
                errors["base"] = "missing_connection"
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_connection"
            else:
                return await self.async_step_channels()
        return self.async_show_form(step_id="legacy", data_schema=vol.Schema({}), errors=errors)

    def _duplicate(self, connection, ignore_entry_id=None):
        for entry in self._async_current_entries():
            if entry.entry_id == ignore_entry_id:
                continue
            try:
                if ConnectionConfig.from_mapping(entry.data).identity == connection.identity:
                    return True
            except (ValueError, KeyError, TypeError):
                continue
        return False

    async def _check(self, connection, channel):
        await CommaxClient(async_get_clientsession(self.hass), connection).get_light(channel)

    async def async_step_channels(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                lights, fans = validate_channels(user_input[CONF_LIGHTS], user_input[CONF_FANS])
                await self._check(self._connection, (lights + fans)[0])
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_channels"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except CommaxError:
                errors["base"] = "cannot_connect"
            else:
                if self._duplicate(self._connection):
                    return self.async_abort(reason="already_configured")
                await self.async_set_unique_id(self._connection.identity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="COMMAX Wallpad", data={**self._connection.as_dict(), **user_input}
                )
        return self.async_show_form(
            step_id="channels", data_schema=channel_schema(user_input), errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                connection = ConnectionConfig.from_mapping(user_input)
                settings = {**entry.data, **entry.options}
                lights, fans = validate_channels(settings[CONF_LIGHTS], settings[CONF_FANS])
                await self._check(connection, (lights + fans)[0])
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_connection"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except CommaxError:
                errors["base"] = "cannot_connect"
            else:
                if self._duplicate(connection, entry.entry_id):
                    return self.async_abort(reason="already_configured")
                # Endpoint changes must not replace the established entity identities.
                return self.async_update_reload_and_abort(entry, data_updates=connection.as_dict())
        return self.async_show_form(
            step_id="reconfigure", data_schema=connection_schema(entry.data), errors=errors
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            try:
                connection = ConnectionConfig.from_mapping({**entry.data, **user_input})
                settings = {**entry.data, **entry.options}
                lights, fans = validate_channels(settings[CONF_LIGHTS], settings[CONF_FANS])
                await self._check(connection, (lights + fans)[0])
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_connection"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except CommaxError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(entry, data_updates=connection.as_dict())
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=connection_schema(entry.data, credentials_only=True),
            errors=errors,
        )


class CommaxOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_channels(user_input[CONF_LIGHTS], user_input[CONF_FANS])
            except (ValueError, KeyError, TypeError):
                errors["base"] = "invalid_channels"
            else:
                return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=channel_schema({**self.config_entry.data, **self.config_entry.options}),
            errors=errors,
        )
