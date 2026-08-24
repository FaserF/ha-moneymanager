"""DataUpdateCoordinator for the MoneyManager integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import MoneyManagerApiClient, MoneyManagerConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.storage"


class MoneyManagerDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching MoneyManager data with persistent cache fallback."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MoneyManagerApiClient,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # Only manual or config update
        )
        self.client = client
        self.entry_id = entry_id
        self._store = Store[dict[str, Any]](
            hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}"
        )
        self.server_available: bool = False
        self.last_sync: datetime | None = None
        self._cached_data: dict[str, Any] = {}

    async def async_load_cache(self) -> None:
        """Load cached data from persistent storage."""
        stored = await self._store.async_load()
        if stored:
            self._cached_data = stored.get("data", {})
            last_sync_str = stored.get("last_sync")
            if last_sync_str:
                try:
                    self.last_sync = datetime.fromisoformat(last_sync_str)
                except Exception:
                    self.last_sync = None
            if self._cached_data and not self.data:
                self.data = self._cached_data

    async def async_save_cache(self) -> None:
        """Save data to persistent storage."""
        if self._cached_data:
            payload = {
                "data": self._cached_data,
                "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            }
            await self._store.async_save(payload)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from MoneyManager or fallback to cache with warning."""
        try:
            data = await self.client.fetch_all_data()
            self.server_available = True
            self.last_sync = datetime.now(UTC)
            self._cached_data = data
            await self.async_save_cache()
            return data
        except MoneyManagerConnectionError as err:
            self.server_available = False
            _LOGGER.warning(
                "MoneyManager PC Manager server is not reachable (%s). "
                "Retaining last known cached financial data.",
                err,
            )
            if self._cached_data:
                return self._cached_data
            if self.data:
                return self.data
            # If no cached data exists at all
            return {}
        except Exception as err:
            self.server_available = False
            _LOGGER.warning(
                "Unexpected error fetching MoneyManager data: %s. Using cached data.",
                err,
            )
            if self._cached_data:
                return self._cached_data
            if self.data:
                return self.data
            return {}
