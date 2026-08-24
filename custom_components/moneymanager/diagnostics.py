"""Diagnostics support for MoneyManager integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_PASSCODE, DOMAIN
from .coordinator import MoneyManagerDataUpdateCoordinator

REDACT_KEYS = {
    CONF_PASSCODE,
    "passcode",
    "sessionid",
    "password",
}


def _to_json_safe(obj: Any) -> Any:
    """Convert arbitrary objects to JSON-safe data."""
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_to_json_safe(i) for i in obj]
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return _to_json_safe(obj.__dict__)
    return str(obj)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: MoneyManagerDataUpdateCoordinator = hass.data[DOMAIN].get(
        entry.entry_id
    )

    diag: dict[str, Any] = {
        "config_entry": async_redact_data(dict(entry.data), REDACT_KEYS),
        "options": async_redact_data(dict(entry.options), REDACT_KEYS),
    }

    if coordinator:
        diag["server_available"] = coordinator.server_available
        diag["last_sync"] = (
            coordinator.last_sync.isoformat() if coordinator.last_sync else None
        )
        diag["data"] = coordinator.data or {}

    reg_devices = []
    reg_entities = []

    try:
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)

        for dev in dev_reg.devices.values():
            if entry.entry_id not in dev.config_entries:
                continue

            reg_devices.append(
                {
                    "id": str(dev.id),
                    "name": str(dev.name or ""),
                    "model": str(dev.model or ""),
                    "manufacturer": str(dev.manufacturer or ""),
                    "configuration_url": str(dev.configuration_url or ""),
                    "identifiers": [list(i) for i in dev.identifiers],
                }
            )

        for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            reg_entities.append(
                {
                    "entity_id": str(ent.entity_id),
                    "unique_id": str(ent.unique_id),
                    "domain": str(ent.domain),
                    "disabled": ent.disabled_by is not None,
                    "device_id": str(ent.device_id),
                    "original_name": str(ent.original_name or ""),
                }
            )
    except Exception as err:
        diag["registry_debug_error"] = str(err)

    diag["registry_debug"] = {
        "devices": reg_devices,
        "entities": reg_entities,
        "config_entry_id": entry.entry_id,
    }

    return _to_json_safe(diag)
