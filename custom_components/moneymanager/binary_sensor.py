"""Binary sensor platform for MoneyManager integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_LAST_SYNC, CONF_HOST, CONF_PORT, CONF_USE_SSL, DOMAIN
from .coordinator import MoneyManagerDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MoneyManager binary sensor based on config_entry."""
    coordinator: MoneyManagerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([MoneyManagerServerBinarySensor(coordinator, entry)])


class MoneyManagerServerBinarySensor(
    CoordinatorEntity[MoneyManagerDataUpdateCoordinator], BinarySensorEntity
):
    """Representation of the MoneyManager PC Server connection binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "server_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: MoneyManagerDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the server connection sensor."""
        super().__init__(coordinator)
        self.entry = entry
        host = entry.data.get(CONF_HOST, "unknown")
        port = entry.data.get(CONF_PORT, 8888)
        use_ssl = entry.data.get(CONF_USE_SSL, False)
        proto = "https" if use_ssl else "http"
        config_url = f"{proto}://{host}:{port}/"

        self._attr_unique_id = f"{entry.entry_id}_server_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"MoneyManager ({host})",
            manufacturer="Realbyte",
            model="Money Manager PC Server",
            sw_version="v3.3.0 (PC Manager)",
            configuration_url=config_url,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the PC manager server is reachable."""
        return self.coordinator.server_available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device extra attributes."""
        return {
            ATTR_LAST_SYNC: self.coordinator.last_sync.isoformat()
            if self.coordinator.last_sync
            else None,
        }
