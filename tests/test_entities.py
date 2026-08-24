"""Test MoneyManager entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.moneymanager.binary_sensor import MoneyManagerServerBinarySensor
from custom_components.moneymanager.button import MoneyManagerUpdateDataButton
from custom_components.moneymanager.sensor import (
    MoneyManagerAccountSensor,
    MoneyManagerDebtSensor,
    MoneyManagerMonthlyExpenseSensor,
    MoneyManagerMonthlyIncomeSensor,
    MoneyManagerNetAssetSensor,
    MoneyManagerTotalAssetSensor,
)


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.server_available = True
    coord.last_sync = None
    coord.data = {
        "dashboard_data": {
            "assetSummary": {
                "totalAsset": "259195.11",
                "asset": "259381.61",
                "debt": "-186.5",
            },
            "assetRatio": [
                {"assetName": "Barzahlung", "assetMoney": "12356.95"},
                {"assetName": "Giro", "assetMoney": "245863.65"},
            ],
            "debtRatio": [
                {"assetName": "Kreditkarte", "assetMoney": "-4.0"},
            ],
        },
        "summary_data": {
            "summary": {
                "income": "651.99",
                "outcome": "285.26",
                "sum": "366.73",
            }
        },
    }
    return coord


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {"host": "192.168.1.50", "port": 8888}
    return entry


def test_sensors(mock_coordinator, mock_entry):
    """Test sensor state values."""
    total_sensor = MoneyManagerTotalAssetSensor(mock_coordinator, mock_entry)
    assert total_sensor.native_value == 259381.61

    net_sensor = MoneyManagerNetAssetSensor(mock_coordinator, mock_entry)
    assert net_sensor.native_value == 259195.11

    debt_sensor = MoneyManagerDebtSensor(mock_coordinator, mock_entry)
    assert debt_sensor.native_value == -186.5

    income_sensor = MoneyManagerMonthlyIncomeSensor(mock_coordinator, mock_entry)
    assert income_sensor.native_value == 651.99

    expense_sensor = MoneyManagerMonthlyExpenseSensor(mock_coordinator, mock_entry)
    assert expense_sensor.native_value == 285.26

    giro_sensor = MoneyManagerAccountSensor(
        mock_coordinator, mock_entry, "Giro", is_debt=False
    )
    assert giro_sensor.native_value == 245863.65

    card_sensor = MoneyManagerAccountSensor(
        mock_coordinator, mock_entry, "Kreditkarte", is_debt=True
    )
    assert card_sensor.native_value == -4.0


def test_binary_sensor(mock_coordinator, mock_entry):
    """Test binary sensor connection state."""
    bin_sensor = MoneyManagerServerBinarySensor(mock_coordinator, mock_entry)
    assert bin_sensor.is_on is True
    mock_coordinator.server_available = False
    assert bin_sensor.is_on is False


@pytest.mark.asyncio
async def test_button(mock_coordinator, mock_entry):
    """Test update data now button."""
    btn = MoneyManagerUpdateDataButton(mock_coordinator, mock_entry)
    await btn.async_press()
    mock_coordinator.async_request_refresh.assert_called_once()
