"""Diagnostics support for go-eCharger."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

from .const import CONF_NAME, DOMAIN


TO_REDACT = {CONF_HOST}
SENSITIVE_STATUS_KEYS = {"unlocked_by_card", "wifi_ssid"}


async def async_get_config_entry_diagnostics(hass, config_entry):
    """Return diagnostics for a config entry."""
    charger_name = config_entry.data[CONF_NAME]
    coordinator = hass.data[DOMAIN]["coordinator"]
    charger_status = (coordinator.data or {}).get(charger_name, {})
    if not isinstance(charger_status, dict):
        charger_status = {}

    return {
        "config_entry": async_redact_data(config_entry.data, TO_REDACT),
        "options": dict(config_entry.options),
        "charger_status": {
            key: value
            for key, value in charger_status.items()
            if key not in SENSITIVE_STATUS_KEYS
        },
        "available_status_keys": sorted(charger_status),
    }
