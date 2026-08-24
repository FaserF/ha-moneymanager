"""Test coordinator offline caching behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.moneymanager.api import MoneyManagerConnectionError
from custom_components.moneymanager.coordinator import MoneyManagerDataUpdateCoordinator


@pytest.mark.asyncio
async def test_coordinator_caching_on_failure(hass):
    """Test that coordinator returns cached data and sets server_available=False on connection error."""
    mock_client = MagicMock()
    mock_client.fetch_all_data = AsyncMock(
        side_effect=MoneyManagerConnectionError("Connection refused")
    )

    coordinator = MoneyManagerDataUpdateCoordinator(hass, mock_client, "test_entry_id")
    coordinator._cached_data = {"cached": "data"}

    data = await coordinator._async_update_data()
    assert data == {"cached": "data"}
    assert coordinator.server_available is False
