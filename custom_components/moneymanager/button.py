"""Button platform for MoneyManager integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_PORT, CONF_USE_SSL, DOMAIN
from .coordinator import MoneyManagerDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MoneyManager button based on config_entry."""
    coordinator: MoneyManagerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([MoneyManagerUpdateDataButton(coordinator, entry)])


class MoneyManagerUpdateDataButton(
    CoordinatorEntity[MoneyManagerDataUpdateCoordinator], ButtonEntity
):
    """Representation of the MoneyManager manual update data button."""

    _attr_has_entity_name = True
    _attr_translation_key = "update_data_now"
    _attr_icon = "mdi:sync"

    def __init__(
        self,
        coordinator: MoneyManagerDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entry = entry
        host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, "unknown"))
        port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, 8888))
        use_ssl = entry.options.get(CONF_USE_SSL, entry.data.get(CONF_USE_SSL, False))
        proto = "https" if use_ssl else "http"
        config_url = f"{proto}://{host}:{port}/"

        book_name = (
            coordinator.data.get("init_data", {}).get("initData", {}).get("mbName")
            if coordinator.data
            else None
        )
        device_name = (
            f"MoneyManager ({book_name})" if book_name else f"MoneyManager ({host})"
        )

        self._attr_unique_id = f"{entry.entry_id}_update_data_now"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Realbyte",
            model="Money Manager PC Server",
            sw_version="v3.3.0 (PC Manager)",
            configuration_url=config_url,
        )

    async def async_press(self) -> None:
        """Handle the button press to fetch latest data."""
        await self.coordinator.async_request_refresh()
