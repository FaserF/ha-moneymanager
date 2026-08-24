"""Constants for the MoneyManager integration."""

from typing import Final

DOMAIN: Final = "moneymanager"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_PASSCODE: Final = "passcode"
CONF_USE_SSL: Final = "use_ssl"

DEFAULT_PORT: Final = 8888
DEFAULT_USE_SSL: Final = False

# Extra Attributes
ATTR_LAST_SYNC: Final = "last_sync"
ATTR_SERVER_AVAILABLE: Final = "server_available"
ATTR_CURRENCY: Final = "currency"

SERVICE_UPDATE_DATA: Final = "update_data"
SERVICE_CREATE_ENTRY: Final = "create_entry"
SERVICE_DELETE_ENTRY: Final = "delete_entry"
