"""Config flow and options flow for MoneyManager integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    MoneyManagerApiClient,
    MoneyManagerAuthError,
    MoneyManagerConnectionError,
)
from .const import (
    CONF_HOST,
    CONF_PASSCODE,
    CONF_PORT,
    CONF_USE_SSL,
    DEFAULT_PORT,
    DEFAULT_USE_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_PASSCODE, default=""): str,
        vol.Optional(CONF_USE_SSL, default=DEFAULT_USE_SSL): bool,
    }
)


class MoneyManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MoneyManager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            passcode = user_input.get(CONF_PASSCODE, "").strip()
            use_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)

            session = async_get_clientsession(self.hass)
            client = MoneyManagerApiClient(
                host=host,
                port=port,
                passcode=passcode if passcode else None,
                use_ssl=use_ssl,
                session=session,
            )

            try:
                # Test connection and fetch initData
                init_data = await client.request("moneyBook/getInitData", timeout=5)
                mb_name = init_data.get("initData", {}).get("mbName") or "MoneyManager"

                # Generate a globally unique fingerprint from internal database UUIDs (categories & accounts)
                # MoneyManager generates persistent UUIDs for custom categories & accounts (e.g. '9CA5B6E1-7111-4203-8C7D-921D058A3672')
                raw_ids: list[str] = []
                for cat in init_data.get("category_0", []) + init_data.get(
                    "category_1", []
                ):
                    if mcid := cat.get("mcid"):
                        raw_ids.append(str(mcid))
                for asset in init_data.get("assetNames", []):
                    if aid := asset.get("assetId"):
                        raw_ids.append(str(aid))

                if raw_ids:
                    import hashlib

                    fingerprint = hashlib.sha256(
                        "_".join(sorted(raw_ids)).encode("utf-8")
                    ).hexdigest()[:12]
                    unique_id = f"moneymanager_{fingerprint}"
                else:
                    unique_id = f"moneymanager_{host}_{port}"

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                entry_title = (
                    f"MoneyManager ({mb_name})"
                    if mb_name != "MoneyManager"
                    else f"MoneyManager ({host})"
                )

                return self.async_create_entry(
                    title=entry_title,
                    data=user_input,
                )
            except MoneyManagerAuthError:
                errors["base"] = "invalid_auth"
            except MoneyManagerConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected exception in config flow: %s", err)
                errors["base"] = "unknown"

        current_host = user_input.get(CONF_HOST, "") if user_input else ""
        current_port = (
            user_input.get(CONF_PORT, DEFAULT_PORT) if user_input else DEFAULT_PORT
        )
        current_passcode = user_input.get(CONF_PASSCODE, "") if user_input else ""
        current_ssl = (
            user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)
            if user_input
            else DEFAULT_USE_SSL
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_PORT, default=current_port): int,
                vol.Optional(CONF_PASSCODE, default=current_passcode): str,
                vol.Optional(CONF_USE_SSL, default=current_ssl): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return MoneyManagerOptionsFlowHandler(config_entry)


class MoneyManagerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle MoneyManager options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST, "").strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            passcode = user_input.get(CONF_PASSCODE, "").strip()
            use_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)

            session = async_get_clientsession(self.hass)
            client = MoneyManagerApiClient(
                host=host,
                port=port,
                passcode=passcode if passcode else None,
                use_ssl=use_ssl,
                session=session,
            )

            try:
                success = await client.test_connection()
                if not success:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title="", data=user_input)
            except MoneyManagerAuthError:
                errors["base"] = "invalid_auth"
            except MoneyManagerConnectionError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected exception in options flow: %s", err)
                errors["base"] = "unknown"

        if user_input is not None:
            current_host = user_input.get(CONF_HOST, "")
            current_port = user_input.get(CONF_PORT, DEFAULT_PORT)
            current_passcode = user_input.get(CONF_PASSCODE, "")
            current_ssl = user_input.get(CONF_USE_SSL, DEFAULT_USE_SSL)
        else:
            current_host = self._config_entry.data.get(CONF_HOST, "")
            current_port = self._config_entry.data.get(CONF_PORT, DEFAULT_PORT)
            current_passcode = self._config_entry.data.get(CONF_PASSCODE, "")
            current_ssl = self._config_entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL)

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_PORT, default=current_port): int,
                vol.Optional(CONF_PASSCODE, default=current_passcode): str,
                vol.Optional(CONF_USE_SSL, default=current_ssl): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )
