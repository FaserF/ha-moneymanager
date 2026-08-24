"""Sensor platform for MoneyManager integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_SYNC,
    ATTR_SERVER_AVAILABLE,
    CONF_HOST,
    CONF_PORT,
    CONF_USE_SSL,
    DOMAIN,
)
from .coordinator import MoneyManagerDataUpdateCoordinator


def _safe_float(val: Any) -> float | None:
    """Safely convert string or numeric value to float."""
    if val is None:
        return None
    try:
        return round(float(str(val).replace(",", "").strip()), 2)
    except (ValueError, TypeError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MoneyManager sensors based on config entry."""
    coordinator: MoneyManagerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        MoneyManagerLastSyncSensor(coordinator, entry),
        MoneyManagerTotalAssetSensor(coordinator, entry),
        MoneyManagerNetAssetSensor(coordinator, entry),
        MoneyManagerDebtSensor(coordinator, entry),
        # Current Month
        MoneyManagerMonthlyIncomeSensor(coordinator, entry),
        MoneyManagerMonthlyExpenseSensor(coordinator, entry),
        MoneyManagerMonthlyBalanceSensor(coordinator, entry),
        MoneyManagerMonthlySavingsRateSensor(coordinator, entry),
        # Previous Month
        MoneyManagerPrevMonthIncomeSensor(coordinator, entry),
        MoneyManagerPrevMonthExpenseSensor(coordinator, entry),
        MoneyManagerPrevMonthBalanceSensor(coordinator, entry),
        MoneyManagerPrevMonthSavingsRateSensor(coordinator, entry),
        # Current Year
        MoneyManagerYearlyIncomeSensor(coordinator, entry),
        MoneyManagerYearlyExpenseSensor(coordinator, entry),
        MoneyManagerYearlyBalanceSensor(coordinator, entry),
        MoneyManagerYearlySavingsRateSensor(coordinator, entry),
        # Previous Year
        MoneyManagerPrevYearIncomeSensor(coordinator, entry),
        MoneyManagerPrevYearExpenseSensor(coordinator, entry),
        MoneyManagerPrevYearBalanceSensor(coordinator, entry),
        MoneyManagerPrevYearSavingsRateSensor(coordinator, entry),
        # Secondary / Breakdown sensors
        MoneyManagerCashExpenseSensor(coordinator, entry),
        MoneyManagerCardExpenseSensor(coordinator, entry),
        MoneyManagerTransactionsSensor(coordinator, entry),
        MoneyManagerBookInfoSensor(coordinator, entry),
    ]

    # Dynamically create account / asset breakdown sensors if available in data
    data = coordinator.data or {}
    dashboard = data.get("dashboard_data", {})

    asset_ratios = dashboard.get("assetRatio", [])
    for item in asset_ratios:
        name = item.get("assetName")
        if name:
            entities.append(
                MoneyManagerAccountSensor(coordinator, entry, name, is_debt=False)
            )

    debt_ratios = dashboard.get("debtRatio", [])
    for item in debt_ratios:
        name = item.get("assetName")
        if name:
            entities.append(
                MoneyManagerAccountSensor(coordinator, entry, name, is_debt=True)
            )

    async_add_entities(entities)


class MoneyManagerBaseSensor(
    CoordinatorEntity[MoneyManagerDataUpdateCoordinator], SensorEntity
):
    """Base sensor for MoneyManager."""

    _attr_has_entity_name = True
    _attr_device_class: SensorDeviceClass | None = SensorDeviceClass.MONETARY
    _attr_state_class: SensorStateClass | None = SensorStateClass.TOTAL

    def __init__(
        self,
        coordinator: MoneyManagerDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self.entry = entry
        host = entry.options.get(CONF_HOST, entry.data.get(CONF_HOST, "unknown"))
        port = entry.options.get(CONF_PORT, entry.data.get(CONF_PORT, 8888))
        use_ssl = entry.options.get(
            CONF_USE_SSL, entry.data.get(CONF_USE_SSL, False)
        )
        proto = "https" if use_ssl else "http"
        config_url = f"{proto}://{host}:{port}/"

        book_name = (
            coordinator.data.get("init_data", {})
            .get("initData", {})
            .get("mbName")
            if coordinator.data
            else None
        )
        device_name = f"MoneyManager ({book_name})" if book_name else f"MoneyManager ({host})"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            manufacturer="Realbyte",
            model="Money Manager PC Server",
            sw_version="v3.3.0 (PC Manager)",
            configuration_url=config_url,
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the default currency unit."""
        return "EUR"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor extra state attributes."""
        return {
            ATTR_LAST_SYNC: (
                self.coordinator.last_sync.isoformat()
                if self.coordinator.last_sync
                else None
            ),
            ATTR_SERVER_AVAILABLE: self.coordinator.server_available,
        }


class MoneyManagerLastSyncSensor(MoneyManagerBaseSensor):
    """Sensor representing the last data sync timestamp and connection status."""

    _attr_translation_key = "last_sync"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_state_class = None

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_sync"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return None

    @property
    def native_value(self) -> Any:
        """Return the last synchronization timestamp."""
        return self.coordinator.last_sync

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes including server connection status."""
        attrs = super().extra_state_attributes
        attrs["server_connected"] = self.coordinator.server_available
        attrs["is_connected"] = self.coordinator.server_available
        return attrs


class MoneyManagerTotalAssetSensor(MoneyManagerBaseSensor):
    """Sensor for Total Gross Assets."""

    _attr_translation_key = "total_assets"
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_assets"

    @property
    def native_value(self) -> float | None:
        """Return the total gross assets."""
        data = self.coordinator.data or {}
        summary = data.get("dashboard_data", {}).get("assetSummary", {})
        return _safe_float(summary.get("asset"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return history timeline and account breakdown."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        dashboard = data.get("dashboard_data", {})
        attrs["history_months"] = dashboard.get("assetLine", [])
        attrs["asset_ratio"] = dashboard.get("assetRatio", [])
        return attrs


class MoneyManagerNetAssetSensor(MoneyManagerBaseSensor):
    """Sensor for Net Worth (Total Assets minus Debt)."""

    _attr_translation_key = "net_assets"
    _attr_icon = "mdi:piggy-bank"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_net_assets"

    @property
    def native_value(self) -> float | None:
        """Return net total assets."""
        data = self.coordinator.data or {}
        summary = data.get("dashboard_data", {}).get("assetSummary", {})
        return _safe_float(summary.get("totalAsset"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return history timeline."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["history_months"] = data.get("asset_chart_data", {}).get(
            "assetChartData", []
        )
        return attrs


class MoneyManagerDebtSensor(MoneyManagerBaseSensor):
    """Sensor for Total Liabilities/Debt."""

    _attr_translation_key = "total_debt"
    _attr_icon = "mdi:credit-card-outline"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total_debt"

    @property
    def native_value(self) -> float | None:
        """Return total debt."""
        data = self.coordinator.data or {}
        summary = data.get("dashboard_data", {}).get("assetSummary", {})
        return _safe_float(summary.get("debt"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debt accounts breakdown."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["debt_ratio"] = data.get("dashboard_data", {}).get("debtRatio", [])
        return attrs


class MoneyManagerMonthlyIncomeSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Total Income."""

    _attr_translation_key = "monthly_income"
    _attr_icon = "mdi:arrow-down-bold-circle-outline"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_monthly_income"

    @property
    def native_value(self) -> float | None:
        """Return monthly income."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        return _safe_float(summary.get("income"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return income breakdown attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_data", {}).get("income", [])
        return attrs


class MoneyManagerMonthlyExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Total Expense."""

    _attr_translation_key = "monthly_expense"
    _attr_icon = "mdi:arrow-up-bold-circle-outline"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_monthly_expense"

    @property
    def native_value(self) -> float | None:
        """Return monthly expense."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        return _safe_float(summary.get("outcome"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return expense breakdown attributes."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_data", {}).get("outcome", [])
        return attrs


class MoneyManagerMonthlyBalanceSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Net Savings / Balance."""

    _attr_translation_key = "monthly_balance"
    _attr_icon = "mdi:scale-balance"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_monthly_balance"

    @property
    def native_value(self) -> float | None:
        """Return monthly net sum."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        return _safe_float(summary.get("sum"))


class MoneyManagerMonthlySavingsRateSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Savings Rate (%)."""

    _attr_translation_key = "monthly_savings_rate"
    _attr_icon = "mdi:percent"
    _attr_device_class = None
    _attr_state_class = None

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_monthly_savings_rate"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def native_value(self) -> float | None:
        """Calculate savings rate: (income - expense) / income * 100."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        income = _safe_float(summary.get("income"))
        outcome = _safe_float(summary.get("outcome"))
        if income and income > 0 and outcome is not None:
            return round(((income - outcome) / income) * 100, 2)
        return None


# -------------------------------------------------------------
# Previous Month Sensors (Disabled by default)
# -------------------------------------------------------------

class MoneyManagerPrevMonthIncomeSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Month Total Income."""

    _attr_translation_key = "prev_month_income"
    _attr_icon = "mdi:arrow-down-bold-circle-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_month_income"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        return _safe_float(summary.get("income"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_prev_month", {}).get("income", [])
        return attrs


class MoneyManagerPrevMonthExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Month Total Expense."""

    _attr_translation_key = "prev_month_expense"
    _attr_icon = "mdi:arrow-up-bold-circle-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_month_expense"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        return _safe_float(summary.get("outcome"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_prev_month", {}).get("outcome", [])
        return attrs


class MoneyManagerPrevMonthBalanceSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Month Balance."""

    _attr_translation_key = "prev_month_balance"
    _attr_icon = "mdi:scale-balance"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_month_balance"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        return _safe_float(summary.get("sum"))


class MoneyManagerPrevMonthSavingsRateSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Month Savings Rate (%)."""

    _attr_translation_key = "prev_month_savings_rate"
    _attr_icon = "mdi:percent"
    _attr_device_class = None
    _attr_state_class = None
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_month_savings_rate"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_month", {}).get("summary", {})
        income = _safe_float(summary.get("income"))
        outcome = _safe_float(summary.get("outcome"))
        if income and income > 0 and outcome is not None:
            return round(((income - outcome) / income) * 100, 2)
        return None


# -------------------------------------------------------------
# Current Year Sensors
# -------------------------------------------------------------

class MoneyManagerYearlyIncomeSensor(MoneyManagerBaseSensor):
    """Sensor for Current Year Total Income."""

    _attr_translation_key = "yearly_income"
    _attr_icon = "mdi:arrow-down-bold-circle-outline"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_yearly_income"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        return _safe_float(summary.get("income"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_current_year", {}).get("income", [])
        attrs["monthly_breakdown"] = data.get("summary_current_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerYearlyExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Current Year Total Expense."""

    _attr_translation_key = "yearly_expense"
    _attr_icon = "mdi:arrow-up-bold-circle-outline"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_yearly_expense"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        return _safe_float(summary.get("outcome"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_current_year", {}).get("outcome", [])
        attrs["monthly_breakdown"] = data.get("summary_current_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerYearlyBalanceSensor(MoneyManagerBaseSensor):
    """Sensor for Current Year Balance."""

    _attr_translation_key = "yearly_balance"
    _attr_icon = "mdi:scale-balance"

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_yearly_balance"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        return _safe_float(summary.get("sum"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["monthly_breakdown"] = data.get("summary_current_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerYearlySavingsRateSensor(MoneyManagerBaseSensor):
    """Sensor for Current Year Savings Rate (%)."""

    _attr_translation_key = "yearly_savings_rate"
    _attr_icon = "mdi:percent"
    _attr_device_class = None
    _attr_state_class = None

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_yearly_savings_rate"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_current_year", {}).get("summary", {})
        income = _safe_float(summary.get("income"))
        outcome = _safe_float(summary.get("outcome"))
        if income and income > 0 and outcome is not None:
            return round(((income - outcome) / income) * 100, 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["monthly_breakdown"] = data.get("summary_current_year", {}).get("monthly_breakdown", [])
        return attrs


# -------------------------------------------------------------
# Previous Year Sensors (Disabled by default)
# -------------------------------------------------------------

class MoneyManagerPrevYearIncomeSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Year Total Income."""

    _attr_translation_key = "prev_year_income"
    _attr_icon = "mdi:arrow-down-bold-circle-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_year_income"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        return _safe_float(summary.get("income"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_prev_year", {}).get("income", [])
        attrs["monthly_breakdown"] = data.get("summary_prev_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerPrevYearExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Year Total Expense."""

    _attr_translation_key = "prev_year_expense"
    _attr_icon = "mdi:arrow-up-bold-circle-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_year_expense"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        return _safe_float(summary.get("outcome"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        attrs["start_date"] = summary.get("startDate")
        attrs["end_date"] = summary.get("endDate")
        attrs["categories"] = data.get("summary_prev_year", {}).get("outcome", [])
        attrs["monthly_breakdown"] = data.get("summary_prev_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerPrevYearBalanceSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Year Balance."""

    _attr_translation_key = "prev_year_balance"
    _attr_icon = "mdi:scale-balance"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_year_balance"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        return _safe_float(summary.get("sum"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["monthly_breakdown"] = data.get("summary_prev_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerPrevYearSavingsRateSensor(MoneyManagerBaseSensor):
    """Sensor for Previous Year Savings Rate (%)."""

    _attr_translation_key = "prev_year_savings_rate"
    _attr_icon = "mdi:percent"
    _attr_device_class = None
    _attr_state_class = None
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_prev_year_savings_rate"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "%"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        summary = data.get("summary_prev_year", {}).get("summary", {})
        income = _safe_float(summary.get("income"))
        outcome = _safe_float(summary.get("outcome"))
        if income and income > 0 and outcome is not None:
            return round(((income - outcome) / income) * 100, 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["monthly_breakdown"] = data.get("summary_prev_year", {}).get("monthly_breakdown", [])
        return attrs


class MoneyManagerCashExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Cash Expenses."""

    _attr_translation_key = "cash_expense"
    _attr_icon = "mdi:cash"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cash_expense"

    @property
    def native_value(self) -> float | None:
        """Return monthly cash outcome."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        return _safe_float(summary.get("cash"))


class MoneyManagerCardExpenseSensor(MoneyManagerBaseSensor):
    """Sensor for Current Month Card/Electronic Expenses."""

    _attr_translation_key = "card_expense"
    _attr_icon = "mdi:credit-card"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_card_expense"

    @property
    def native_value(self) -> float | None:
        """Return monthly card outcome."""
        data = self.coordinator.data or {}
        summary = data.get("summary_data", {}).get("summary", {})
        return _safe_float(summary.get("card"))


class MoneyManagerTransactionsSensor(MoneyManagerBaseSensor):
    """Sensor for Monthly Transactions Count & Recent History."""

    _attr_translation_key = "recent_transactions"
    _attr_icon = "mdi:format-list-bulleted"
    _attr_device_class = None
    _attr_state_class = None
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_recent_transactions"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return "transactions"

    @property
    def native_value(self) -> int:
        """Return total count of fetched transactions."""
        data = self.coordinator.data or {}
        return len(data.get("transactions", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return full list of recent transactions."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        attrs["transactions"] = data.get("transactions", [])
        return attrs


class MoneyManagerBookInfoSensor(MoneyManagerBaseSensor):
    """Sensor for Account Book Name & Category Counts."""

    _attr_translation_key = "account_book"
    _attr_icon = "mdi:book-open-variant"
    _attr_device_class = None
    _attr_state_class = None
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: MoneyManagerDataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_account_book"

    @property
    def native_unit_of_measurement(self) -> str | None:
        return None

    @property
    def native_value(self) -> str | None:
        """Return book name."""
        data = self.coordinator.data or {}
        return (
            data.get("init_data", {}).get("initData", {}).get("mbName", "MoneyManager")
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return categories and payment types."""
        attrs = super().extra_state_attributes
        data = self.coordinator.data or {}
        init = data.get("init_data", {})
        attrs["income_categories"] = [
            c.get("mcname") for c in init.get("category_0", [])
        ]
        attrs["expense_categories"] = [
            c.get("mcname") for c in init.get("category_1", [])
        ]
        attrs["pay_types"] = [p.get("ptname") for p in init.get("payType", [])]
        attrs["asset_groups"] = [
            g.get("assetName") for g in init.get("assetGroups", [])
        ]
        return attrs


class MoneyManagerAccountSensor(MoneyManagerBaseSensor):
    """Sensor for specific accounts/assets (e.g. Giro, Bargeld, PayPal, etc.)."""

    def __init__(
        self,
        coordinator: MoneyManagerDataUpdateCoordinator,
        entry: ConfigEntry,
        account_name: str,
        is_debt: bool = False,
    ) -> None:
        super().__init__(coordinator, entry)
        self.account_name = account_name
        self.is_debt = is_debt
        slug = account_name.lower().replace(" ", "_").replace("/", "_")
        self._attr_unique_id = f"{entry.entry_id}_account_{slug}"
        self._attr_name = account_name
        self._attr_icon = "mdi:credit-card" if is_debt else "mdi:wallet"

    @property
    def native_value(self) -> float | None:
        """Return balance for this specific account."""
        data = self.coordinator.data or {}
        dashboard = data.get("dashboard_data", {})
        ratio_list = (
            dashboard.get("debtRatio", [])
            if self.is_debt
            else dashboard.get("assetRatio", [])
        )
        for item in ratio_list:
            if item.get("assetName") == self.account_name:
                return _safe_float(item.get("assetMoney"))
        return None
