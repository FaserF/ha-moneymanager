"""Test the MoneyManager API Client and JSON/JS parser."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.moneymanager.api import (
    MoneyManagerApiClient,
    MoneyManagerAuthError,
    parse_js_object,
)


def test_parse_js_object_standard_json():
    """Test standard JSON parsing."""
    res = parse_js_object('{"key": "value", "number": 123}')
    assert res == {"key": "value", "number": 123}


def test_parse_js_object_loose_js():
    """Test loose JavaScript object parsing."""
    raw = "{initData: {initStartDate:'2026-08-01',initEndDate:'2026-08-31',mbid:'1'}, multiBooks: [{mbid:'1', mbname:'MoneyManager'}]}"
    res = parse_js_object(raw)
    assert res["initData"]["initStartDate"] == "2026-08-01"
    assert res["multiBooks"][0]["mbname"] == "MoneyManager"


def test_parse_js_object_summary():
    """Test dashboard and summary JSON."""
    raw = "{summary:{startDate:'2026-08-01',endDate:'2026-08-31',income:'651.99',outcome:'285.26',cash:'74.8',card:'186.5',etcExpenseOpt:false, etcExpense:'0',sum:'366.73'},income:[{mcname:'VHS',mcSum:'600.0',budget:'0'}]}"
    res = parse_js_object(raw)
    assert res["summary"]["income"] == "651.99"
    assert res["income"][0]["mcname"] == "VHS"


@pytest.mark.asyncio
async def test_api_client_request():
    """Test API client request method."""
    client = MoneyManagerApiClient(host="192.168.1.50", port=8888)
    assert client.base_url == "http://192.168.1.50:8888"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value="{initData: {mbid:'1'}}")

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request = MagicMock(return_value=mock_cm)
    mock_session.closed = False

    with patch.object(client, "_get_session", AsyncMock(return_value=mock_session)):
        data = await client.request("moneyBook/getInitData")
        assert data["initData"]["mbid"] == "1"


@pytest.mark.asyncio
async def test_api_client_auth_error():
    """Test authentication error handling."""
    client = MoneyManagerApiClient(host="192.168.1.50", port=8888)

    mock_resp = MagicMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="")

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.request = MagicMock(return_value=mock_cm)
    mock_session.closed = False

    with patch.object(client, "_get_session", AsyncMock(return_value=mock_session)):
        with pytest.raises(MoneyManagerAuthError):
            await client.request("moneyBook/getInitData")

