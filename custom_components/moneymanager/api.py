"""API client for MoneyManager PC Manager."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import re
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class MoneyManagerAuthError(Exception):
    """Exception to indicate an authentication error."""


class MoneyManagerConnectionError(Exception):
    """Exception to indicate a connection error."""


class MoneyManagerResponseError(Exception):
    """Exception to indicate invalid response payload."""


def _safe_float(val: Any) -> float | None:
    """Safely convert string or numeric value to float."""
    if val is None:
        return None
    try:
        return round(float(str(val).replace(",", "").strip()), 2)
    except (ValueError, TypeError):
        return None


def parse_js_object(js_text: str) -> dict[str, Any]:
    """Parse JavaScript object notation / loose JSON returned by MoneyManager."""
    cleaned = js_text.strip()
    if not cleaned:
        return {}

    # Try standard JSON first
    try:
        val = json.loads(cleaned)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    # Normalize single quotes to double quotes, wrap unquoted keys in quotes
    try:
        # Quote unquoted keys (e.g. {key: or ,key: or  key:)
        normalized = re.sub(r"([{\[,]\s*)([a-zA-Z_0-9]+)\s*:", r'\1"\2":', cleaned)
        # Replace single quotes with double quotes for string values
        normalized = re.sub(r"'([^']*)'", r'"\1"', normalized)
        # Replace 'null' as string or bare null
        normalized = normalized.replace("':null'", ":null").replace('":null"', ":null")
        val = json.loads(normalized)
        if isinstance(val, dict):
            return val
    except Exception as err:
        _LOGGER.debug(
            "Regex normalization failed (%s), attempting Python literal evaluation",
            err,
        )

    # Fallback to ast.literal_eval if safe
    try:
        import ast

        # Python dictionary syntax requires true/false/null -> True/False/None
        py_repr = re.sub(r"([{\[,]\s*)([a-zA-Z_0-9]+)\s*:", r'\1"\2":', cleaned)
        py_repr = (
            py_repr.replace(":true", ":True")
            .replace(":false", ":False")
            .replace(":null", ":None")
        )
        result = ast.literal_eval(py_repr)
        if isinstance(result, dict):
            return result
    except Exception as err:
        raise MoneyManagerResponseError(
            f"Failed to parse MoneyManager response: {err}"
        ) from err

    raise MoneyManagerResponseError("Response was not a valid dictionary structure")


class MoneyManagerApiClient:
    """Client for MoneyManager PC Manager API."""

    def __init__(
        self,
        host: str,
        port: int = 8888,
        passcode: str | None = None,
        use_ssl: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host.strip().rstrip("/")
        if self._host.startswith("http://"):
            self._host = self._host[7:]
        elif self._host.startswith("https://"):
            self._host = self._host[8:]

        self._port = port
        self._passcode = passcode.strip() if passcode else None
        self._use_ssl = use_ssl
        self._session = session
        self._session_id: str | None = None

    @property
    def base_url(self) -> str:
        """Return base URL."""
        proto = "https" if self._use_ssl else "http"
        return f"{proto}://{self._host}:{self._port}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return or create ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def async_login(self, timeout: int = 5) -> bool:
        """Authenticate with the server using the configured passcode."""
        if not self._passcode:
            return True

        session = await self._get_session()
        url = f"{self.base_url}/moneyBook/login"
        headers = {
            "User-Agent": "HomeAssistant-MoneyManager/1.0",
            "Accept": "text/javascript, application/json, text/html, */*",
        }

        try:
            async with asyncio.timeout(timeout):
                async with session.post(
                    url=url,
                    data={"pwd": self._passcode},
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        raise MoneyManagerConnectionError(
                            f"HTTP error {resp.status} during login"
                        )
                    text = await resp.text(encoding="utf-8", errors="replace")

                    # Parse {success:true, conid:'...'}
                    match = re.search(r"conid:\s*['\"]([^'\"]*)['\"]", text)
                    is_success = "success:true" in text.lower() or "success: true" in text.lower()
                    if is_success and match and match.group(1):
                        self._session_id = match.group(1)
                        return True

                    # If the server has no passcode set, /moneyBook/login returns empty body or 200 without login failure
                    # In that case, check if the server is accessible directly without authentication
                    try:
                        async with session.get(
                            f"{self.base_url}/moneyBook/getInitData",
                            headers=headers,
                        ) as test_resp:
                            test_text = await test_resp.text(
                                encoding="utf-8", errors="replace"
                            )
                            if (
                                "initData" in test_text
                                or "multiBooks" in test_text
                                or "assetNames" in test_text
                            ):
                                _LOGGER.debug(
                                    "Server does not enforce passcode; proceeding unauthenticated"
                                )
                                self._session_id = None
                                return True
                    except Exception:
                        pass

                    self._session_id = None
                    raise MoneyManagerAuthError(
                        "Authentication failed: invalid passcode"
                    )
        except TimeoutError as err:
            raise MoneyManagerConnectionError("Login request timed out") from err
        except aiohttp.ClientError as err:
            raise MoneyManagerConnectionError(f"Login connection error: {err}") from err

    async def request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        timeout: int = 5,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Perform request to MoneyManager PC Manager."""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "User-Agent": "HomeAssistant-MoneyManager/1.0",
            "Accept": "text/javascript, application/json, text/html, */*",
        }

        cookies: dict[str, str] = {}
        if self._session_id:
            cookies["sessionid"] = self._session_id

        try:
            async with asyncio.timeout(timeout):
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                ) as resp:
                    if resp.status in (401, 403):
                        if retry_auth and self._passcode:
                            await self.async_login(timeout=timeout)
                            return await self.request(
                                endpoint, params, method, timeout, retry_auth=False
                            )
                        raise MoneyManagerAuthError(
                            "Authentication failed: invalid passcode"
                        )
                    if resp.status != 200:
                        raise MoneyManagerConnectionError(
                            f"HTTP error {resp.status} on {url}"
                        )

                    text = await resp.text(encoding="utf-8", errors="replace")

                    # Check if MoneyManager returned a login redirect/form or login.js
                    if "login.js" in text or (
                        "password" in text.lower()
                        and "initdata" not in text.lower()
                        and "summary" not in text.lower()
                    ):
                        if retry_auth and self._passcode:
                            await self.async_login(timeout=timeout)
                            return await self.request(
                                endpoint, params, method, timeout, retry_auth=False
                            )
                        raise MoneyManagerAuthError(
                            "Authentication required or invalid passcode"
                        )

                    return parse_js_object(text)

        except TimeoutError as err:
            raise MoneyManagerConnectionError("Connection timed out") from err
        except aiohttp.ClientError as err:
            raise MoneyManagerConnectionError(
                f"Client connection error: {err}"
            ) from err

    async def test_connection(self) -> bool:
        """Test if server is reachable and responds correctly."""
        # Try direct request first; if authentication is required, log in
        try:
            data = await self.request("moneyBook/getInitData", timeout=5, retry_auth=False)
            if "initData" in data or "multiBooks" in data or "assetNames" in data:
                return True
        except MoneyManagerAuthError:
            if self._passcode:
                await self.async_login(timeout=5)
                data = await self.request("moneyBook/getInitData", timeout=5, retry_auth=False)
                if "initData" in data or "multiBooks" in data or "assetNames" in data:
                    return True
            raise

        return False

    async def fetch_all_data(self) -> dict[str, Any]:
        """Fetch all relevant financial and category data."""
        # 1. Fetch initData
        init_data = await self.request("moneyBook/getInitData")

        # Extract date range for summary
        start_date = None
        end_date = None
        mbid = "1"
        if "initData" in init_data:
            start_date = init_data["initData"].get("initStartDate")
            end_date = init_data["initData"].get("initEndDate")
            mbid = str(init_data["initData"].get("mbid", "1"))

        # 2. Fetch dashboard data
        dashboard_data = {}
        try:
            dashboard_data = await self.request("moneyBook/getDashBoardData")
        except Exception as err:
            _LOGGER.debug("Error fetching dashboard data: %s", err)

        # 3. Fetch summary data by period (Current Month, Previous Month, Current Year, Previous Year)
        summary_data: dict[str, Any] = {}
        summary_prev_month: dict[str, Any] = {}
        summary_current_year: dict[str, Any] = {}
        summary_prev_year: dict[str, Any] = {}

        if start_date and end_date:
            try:
                # Parse year and month
                # start_date format is YYYY-MM-DD
                dt_start = datetime.date.fromisoformat(start_date)

                # Previous month calculation
                first_of_cur = dt_start.replace(day=1)
                last_of_prev = first_of_cur - datetime.timedelta(days=1)
                first_of_prev = last_of_prev.replace(day=1)
                prev_m_start = first_of_prev.isoformat()
                prev_m_end = last_of_prev.isoformat()

                # Current Year
                cur_y_start = f"{dt_start.year}-01-01"
                cur_y_end = f"{dt_start.year}-12-31"

                # Previous Year
                prev_y_start = f"{dt_start.year - 1}-01-01"
                prev_y_end = f"{dt_start.year - 1}-12-31"

                # Fetch all period summaries concurrently
                async def _get_summary(s: str, e: str) -> dict[str, Any]:
                    try:
                        return await self.request(
                            "moneyBook/getSummaryDataByPeriod",
                            params={"startDate": s, "endDate": e, "mbid": mbid},
                        )
                    except Exception as err:
                        _LOGGER.debug("Error fetching summary for %s to %s: %s", s, e, err)
                        return {}

                (
                    summary_data,
                    summary_prev_month,
                    summary_current_year,
                    summary_prev_year,
                ) = await asyncio.gather(
                    _get_summary(start_date, end_date),
                    _get_summary(prev_m_start, prev_m_end),
                    _get_summary(cur_y_start, cur_y_end),
                    _get_summary(prev_y_start, prev_y_end),
                )

                # Fetch individual months breakdown for current year (months 1..current_month)
                import calendar

                sem = asyncio.Semaphore(4)

                async def _get_summary_limited(s: str, e: str) -> dict[str, Any]:
                    async with sem:
                        return await _get_summary(s, e)

                cur_year_months_tasks = []
                for m in range(1, dt_start.month + 1):
                    s_m = f"{dt_start.year}-{m:02d}-01"
                    last_d = calendar.monthrange(dt_start.year, m)[1]
                    e_m = f"{dt_start.year}-{m:02d}-{last_d:02d}"
                    cur_year_months_tasks.append(_get_summary_limited(s_m, e_m))

                # Fetch all 12 months for previous year
                prev_year_months_tasks = []
                for m in range(1, 13):
                    s_m = f"{dt_start.year - 1}-{m:02d}-01"
                    last_d = calendar.monthrange(dt_start.year - 1, m)[1]
                    e_m = f"{dt_start.year - 1}-{m:02d}-{last_d:02d}"
                    prev_year_months_tasks.append(_get_summary_limited(s_m, e_m))

                cur_year_res = await asyncio.gather(*cur_year_months_tasks)
                prev_year_res = await asyncio.gather(*prev_year_months_tasks)

                def _build_month_list(results: list[dict[str, Any]], year_val: int) -> list[dict[str, Any]]:
                    mlist = []
                    for idx, res in enumerate(results, start=1):
                        sd = res.get("summary", {})
                        inc = _safe_float(sd.get("income")) or 0.0
                        out = _safe_float(sd.get("outcome")) or 0.0
                        net = _safe_float(sd.get("sum")) if sd.get("sum") is not None else round(inc - out, 2)
                        rate = round(((inc - out) / inc) * 100, 2) if inc > 0 else 0.0
                        mlist.append(
                            {
                                "month": f"{year_val}-{idx:02d}",
                                "month_name": datetime.date(year_val, idx, 1).strftime("%B"),
                                "start_date": sd.get("startDate"),
                                "end_date": sd.get("endDate"),
                                "income": inc,
                                "outcome": out,
                                "balance": net,
                                "savings_rate": rate,
                                "categories_income": res.get("income", []),
                                "categories_outcome": res.get("outcome", []),
                            }
                        )
                    return mlist

                if summary_current_year:
                    summary_current_year["monthly_breakdown"] = _build_month_list(
                        list(cur_year_res), dt_start.year
                    )
                if summary_prev_year:
                    summary_prev_year["monthly_breakdown"] = _build_month_list(
                        list(prev_year_res), dt_start.year - 1
                    )
            except Exception as err:
                _LOGGER.debug("Error preparing period summaries: %s", err)

        # 4. Fetch asset chart data
        asset_chart_data = {}
        try:
            asset_chart_data = await self.request("moneyBook/getEachAssetChartData")
        except Exception as err:
            _LOGGER.debug("Error fetching asset chart data: %s", err)

        # 5. Fetch transactions for current period
        transactions: list[dict[str, Any]] = []
        if start_date and end_date:
            try:
                session = await self._get_session()
                url = f"{self.base_url}/moneyBook/getDataByPeriod"
                params = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "mbid": mbid,
                    "start": "0",
                    "limit": "100",
                }
                cookies: dict[str, str] = {}
                if self._session_id:
                    cookies["sessionid"] = self._session_id

                async with asyncio.timeout(6):
                    async with session.get(
                        url,
                        params=params,
                        headers={"User-Agent": "HomeAssistant-MoneyManager/1.0"},
                        cookies=cookies,
                    ) as resp:
                        if resp.status == 200:
                            xml_text = await resp.text(
                                encoding="utf-8", errors="replace"
                            )
                            import xml.etree.ElementTree as ET

                            root = ET.fromstring(xml_text)
                            for row in root.findall("row"):
                                item: dict[str, Any] = {}
                                for child in row:
                                    item[child.tag] = child.text
                                transactions.append(item)
            except Exception as err:
                _LOGGER.debug("Error fetching transactions: %s", err)

        return {
            "init_data": init_data,
            "dashboard_data": dashboard_data,
            "summary_data": summary_data,
            "summary_prev_month": summary_prev_month,
            "summary_current_year": summary_current_year,
            "summary_prev_year": summary_prev_year,
            "asset_chart_data": asset_chart_data,
            "transactions": transactions,
        }

    async def create_entry(
        self,
        date: str,
        amount: float,
        category: str,
        account: str,
        entry_type: str = "Expense",  # "Expense", "Income", "Transfer"
        note: str = "",
        detail: str = "",
        to_account: str | None = None,
        mbid: str = "1",
    ) -> bool:
        """Create a new income/expense/transfer transaction entry."""
        # 1. Fetch initData to map names to internal IDs
        init_data = await self.request("moneyBook/getInitData")

        in_out_code = "1"
        if entry_type.lower() in ("income", "einnahme", "einnahmen", "0"):
            in_out_code = "0"
            entry_type_str = "Income"
            cat_list = init_data.get("category_0", [])
        elif entry_type.lower() in ("transfer", "umbuchung", "2"):
            in_out_code = "2"
            entry_type_str = "Transfer"
            cat_list = []
        else:
            in_out_code = "1"
            entry_type_str = "Expense"
            cat_list = init_data.get("category_1", [])

        # Find mcid
        mcid = ""
        mb_category = category
        for c in cat_list:
            if c.get("mcname", "").lower() == category.lower() or c.get("mcid") == category:
                mcid = str(c.get("mcid", ""))
                mb_category = str(c.get("mcname", category))
                break
        if not mcid and cat_list:
            mcid = str(cat_list[0].get("mcid", ""))
            mb_category = str(cat_list[0].get("mcname", ""))

        # Find assetId
        asset_list = init_data.get("assetNames", [])
        asset_id = ""
        pay_type = account
        for a in asset_list:
            if a.get("assetName", "").lower() == account.lower() or a.get("assetId") == account:
                asset_id = str(a.get("assetId", ""))
                pay_type = str(a.get("assetName", account))
                break
        if not asset_id and asset_list:
            asset_id = str(asset_list[0].get("assetId", ""))
            pay_type = str(asset_list[0].get("assetName", ""))

        # Find toAssetId if transfer
        to_asset_id = ""
        if to_account:
            for a in asset_list:
                if a.get("assetName", "").lower() == to_account.lower() or a.get("assetId") == to_account:
                    to_asset_id = str(a.get("assetId", ""))
                    break

        post_params: dict[str, Any] = {
            "mbDate": date,
            "assetId": asset_id,
            "payType": pay_type,
            "mcid": mcid,
            "mbCategory": mb_category,
            "mbContent": note,
            "mbCash": str(amount),
            "inOutCode": in_out_code,
            "inOutType": entry_type_str,
            "mbDetailContent": detail,
            "mbid": mbid,
        }
        if to_asset_id:
            post_params["toAssetId"] = to_asset_id

        session = await self._get_session()
        headers = {
            "User-Agent": "HomeAssistant-MoneyManager/1.0",
            "Accept": "text/javascript, application/json, text/html, */*",
        }
        cookies: dict[str, str] = {}
        if self._session_id:
            cookies["sessionid"] = self._session_id

        async with asyncio.timeout(6):
            async with session.post(
                f"{self.base_url}/moneyBook/create",
                data=post_params,
                headers=headers,
                cookies=cookies,
            ) as resp:
                if resp.status != 200:
                    raise MoneyManagerConnectionError(f"HTTP error {resp.status} creating transaction")
                text = await resp.text(encoding="utf-8", errors="replace")
                return "success:true" in text.lower() or "success: true" in text.lower()

    async def delete_entry(self, entry_ids: str | list[str]) -> bool:
        """Delete one or more transaction entries by ID."""
        ids_str = ",".join(entry_ids) if isinstance(entry_ids, list) else entry_ids
        session = await self._get_session()
        headers = {
            "User-Agent": "HomeAssistant-MoneyManager/1.0",
            "Accept": "text/javascript, application/json, text/html, */*",
        }
        cookies: dict[str, str] = {}
        if self._session_id:
            cookies["sessionid"] = self._session_id

        async with asyncio.timeout(6):
            async with session.post(
                f"{self.base_url}/moneyBook/delete",
                data={"ids": ids_str},
                headers=headers,
                cookies=cookies,
            ) as resp:
                if resp.status != 200:
                    raise MoneyManagerConnectionError(f"HTTP error {resp.status} deleting transaction")
                text = await resp.text(encoding="utf-8", errors="replace")
                return "success:true" in text.lower() or "success: true" in text.lower()

    async def close(self) -> None:
        """Close the underlying session if managed internally."""
        if self._session and not self._session.closed:
            await self._session.close()
