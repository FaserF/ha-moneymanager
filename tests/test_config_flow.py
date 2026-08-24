"""Test config flow and options flow."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.moneymanager.api import MoneyManagerConnectionError
from custom_components.moneymanager.config_flow import MoneyManagerConfigFlow
from custom_components.moneymanager.const import CONF_HOST, CONF_PORT


@pytest.mark.asyncio
async def test_config_flow_success(hass):
    """Test successful config flow."""
    flow = MoneyManagerConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.50",
        CONF_PORT: 8888,
        "passcode": "",
        "use_ssl": False,
    }

    with patch(
        "custom_components.moneymanager.config_flow.MoneyManagerApiClient"
    ) as mock_client_cls:
        client_instance = mock_client_cls.return_value
        client_instance.request = AsyncMock(
            return_value={
                "initData": {"mbName": "Privat"},
                "category_0": [{"mcid": "1"}],
                "category_1": [{"mcid": "2"}],
                "assetNames": [{"assetId": "1"}],
            }
        )

        result = await flow.async_step_user(user_input)
        assert result["type"] == "CREATE_ENTRY"
        assert result["title"] == "MoneyManager (Privat)"
        assert result["data"] == user_input


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(hass):
    """Test connection failure in config flow."""
    flow = MoneyManagerConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.50",
        CONF_PORT: 8888,
        "passcode": "",
        "use_ssl": False,
    }

    with patch(
        "custom_components.moneymanager.config_flow.MoneyManagerApiClient"
    ) as mock_client_cls:
        client_instance = mock_client_cls.return_value
        client_instance.request = AsyncMock(
            side_effect=MoneyManagerConnectionError("Connection refused")
        )

        result = await flow.async_step_user(user_input)
        assert result["type"] == "FORM"
        assert result["errors"] == {"base": "cannot_connect"}

