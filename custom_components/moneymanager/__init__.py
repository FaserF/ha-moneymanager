"""Home Assistant integration for MoneyManager (PC Manager)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MoneyManagerApiClient
from .const import (
    CONF_HOST,
    CONF_PASSCODE,
    CONF_PORT,
    CONF_USE_SSL,
    DEFAULT_PORT,
    DEFAULT_USE_SSL,
    DOMAIN,
    SERVICE_CREATE_ENTRY,
    SERVICE_DELETE_ENTRY,
    SERVICE_UPDATE_DATA,
)
from .coordinator import MoneyManagerDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MoneyManager from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST))
    port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, DEFAULT_PORT))
    passcode = entry.options.get(CONF_PASSCODE, entry.data.get(CONF_PASSCODE, ""))
    use_ssl = entry.options.get(
        CONF_USE_SSL, entry.data.get(CONF_USE_SSL, DEFAULT_USE_SSL)
    )

    session = async_get_clientsession(hass)
    client = MoneyManagerApiClient(
        host=host,
        port=port,
        passcode=passcode if passcode else None,
        use_ssl=use_ssl,
        session=session,
    )

    coordinator = MoneyManagerDataUpdateCoordinator(hass, client, entry.entry_id)
    await coordinator.async_load_cache()

    # Initial fetch
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    async def async_handle_update_data(call: ServiceCall) -> None:
        """Handle manual update data service call."""
        _LOGGER.debug("Triggering manual MoneyManager coordinator update via service")
        await coordinator.async_request_refresh()

    async def async_handle_create_entry(call: ServiceCall) -> None:
        """Handle create entry service call."""
        data = call.data
        amount = float(data.get("amount", 0))
        entry_type = str(data.get("entry_type", "Expense"))
        category = str(data.get("category", ""))
        account = str(data.get("account", ""))
        date_str = str(data.get("date") or datetime.now(UTC).strftime("%Y-%m-%d"))
        note = str(data.get("note", ""))
        detail = str(data.get("detail", ""))
        to_account = data.get("to_account")

        _LOGGER.info("Creating MoneyManager entry: %s %.2f in %s (%s)", entry_type, amount, category, account)
        success = await coordinator.client.create_entry(
            date=date_str,
            amount=amount,
            category=category,
            account=account,
            entry_type=entry_type,
            note=note,
            detail=detail,
            to_account=to_account,
        )
        if success:
            # Refresh coordinator cache immediately
            await coordinator.async_request_refresh()

    async def async_handle_delete_entry(call: ServiceCall) -> None:
        """Handle delete entry service call."""
        entry_id_to_del = str(call.data.get("entry_id", "")).strip()
        if not entry_id_to_del:
            return
        _LOGGER.info("Deleting MoneyManager entry ID: %s", entry_id_to_del)
        success = await coordinator.client.delete_entry(entry_id_to_del)
        if success:
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_DATA,
        async_handle_update_data,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_ENTRY,
        async_handle_create_entry,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ENTRY,
        async_handle_delete_entry,
    )

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: MoneyManagerDataUpdateCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        await coordinator.client.close()

    return unload_ok
