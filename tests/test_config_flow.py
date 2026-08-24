"""Test config flow and options flow."""

from unittest.mock import AsyncMock, patch

import pytest

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
        client_instance.test_connection = AsyncMock(return_value=True)

        result = await flow.async_step_user(user_input)
        assert result["type"] == "CREATE_ENTRY"
        assert result["title"] == "MoneyManager (192.168.1.50)"
        assert result["data"] == user_input


@pytest.mark.asyncio
async def test_config_flow_cannot_connect(hass):
    """Test connection failure in config flow."""
    flow = MoneyManagerConfigFlow()
    flow.hass = hass

    user_input = {
        CONF_HOST: "192.168.1.50",
        CONF_PORT: 8888,
    }

    with patch(
        "custom_components.moneymanager.config_flow.MoneyManagerApiClient"
    ) as mock_client_cls:
        client_instance = mock_client_cls.return_value
        client_instance.test_connection = AsyncMock(return_value=False)

        result = await flow.async_step_user(user_input)
        assert result["type"] == "FORM"
        assert result["errors"] == {"base": "cannot_connect"}
