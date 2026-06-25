import logging
from datetime import timedelta
from inspect import isawaitable
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from .api import create_charger, detect_api_version
from .const import (
    API_VERSION_AUTO,
    API_VERSION_OPTIONS,
    CONF_API_VERSION,
    CONF_CORRECTION_FACTOR,
    CONF_NAME,
    DEFAULT_API_VERSION,
    DOMAIN,
)
_LOGGER = logging.getLogger(__name__)


DEFAULT_UPDATE_INTERVAL = timedelta(seconds=20)
MIN_UPDATE_INTERVAL = timedelta(seconds=10)


def _validate_charger(host, api_version):
    create_charger(host, api_version).requestStatus()


async def _async_resolve_and_validate(hass, host, api_version):
    if api_version == API_VERSION_AUTO:
        api_version = await hass.async_add_executor_job(detect_api_version, host)
    await hass.async_add_executor_job(_validate_charger, host, api_version)
    return api_version


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for go-eCharger setup."""
    VERSION = 1

    @staticmethod
    @callback
    async def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, info=None):
        errors = {}
        if info is not None:
            _LOGGER.debug(info)
            data = dict(info)
            try:
                data[CONF_API_VERSION] = await _async_resolve_and_validate(
                    self.hass,
                    data[CONF_HOST],
                    data.get(CONF_API_VERSION, DEFAULT_API_VERSION),
                )
            except Exception:
                _LOGGER.debug("Cannot connect to go-eCharger", exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_NAME): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=20
                    ): int,
                    vol.Required(
                        CONF_CORRECTION_FACTOR, default="1.0"
                    ): str,
                    vol.Optional(
                        CONF_API_VERSION, default=API_VERSION_AUTO
                    ): vol.In(API_VERSION_OPTIONS),
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info):
        host = discovery_info.host
        name = discovery_info.name or "go-eCharger"
        entry_name = name.removesuffix("._http._tcp.local.").strip() or "go-eCharger"

        self.context["title_placeholders"] = {"name": name}
        await self.async_set_unique_id(name)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._discovered_data = {
            CONF_HOST: host,
            CONF_NAME: entry_name,
            CONF_SCAN_INTERVAL: 20,
            CONF_CORRECTION_FACTOR: "1.0",
            CONF_API_VERSION: DEFAULT_API_VERSION,
        }

        handle_discovery = getattr(self, "_async_handle_discovery_without_unique_id", None)
        if handle_discovery:
            result = handle_discovery()
            if isawaitable(result):
                await result

        return self.async_show_form(step_id="confirm")

    async def async_step_confirm(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="confirm")

        return self.async_create_entry(
            title=self._discovered_data[CONF_NAME],
            data=self._discovered_data,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            data = dict(user_input)
            try:
                data[CONF_API_VERSION] = await _async_resolve_and_validate(
                    self.hass,
                    self.config_entry.data[CONF_HOST],
                    data.get(CONF_API_VERSION, DEFAULT_API_VERSION),
                )
            except Exception:
                _LOGGER.debug("Cannot connect to go-eCharger", exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=data)

        api_version = (user_input or self.config_entry.options).get(
            CONF_API_VERSION,
            self.config_entry.data.get(CONF_API_VERSION, DEFAULT_API_VERSION),
        )
        scan_interval = (user_input or self.config_entry.options).get(
            CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, 20)
        )
        correction_factor = (user_input or self.config_entry.options).get(
            CONF_CORRECTION_FACTOR,
            self.config_entry.data.get(CONF_CORRECTION_FACTOR, "1.0"),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_API_VERSION, default=api_version): vol.In(API_VERSION_OPTIONS),
                    vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): int,
                    vol.Optional(CONF_CORRECTION_FACTOR, default=correction_factor): str,
                }
            ),
            errors=errors,
        )
