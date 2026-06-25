import logging
from datetime import timedelta
from inspect import isawaitable
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from .const import API_VERSIONS, CONF_API_VERSION, DEFAULT_API_VERSION, DOMAIN, CONF_NAME, CONF_CORRECTION_FACTOR
_LOGGER = logging.getLogger(__name__)


DEFAULT_UPDATE_INTERVAL = timedelta(seconds=20)
MIN_UPDATE_INTERVAL = timedelta(seconds=10)


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for go-eCharger setup."""
    VERSION = 1

    @staticmethod
    @callback
    async def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, info=None):
        if info is not None:
            _LOGGER.debug(info)
            return self.async_create_entry(title=info[CONF_NAME], data=info)

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
                        CONF_API_VERSION, default=DEFAULT_API_VERSION
                    ): vol.In(API_VERSIONS),
                }
            ),
        )

    async def async_step_zeroconf(self, discovery_info):
        host = discovery_info.host
        name = discovery_info.name or "go-eCharger"
        entry_name = name.removesuffix("._http._tcp.local.").strip() or "go-eCharger"

        self.context["title_placeholders"] = {"name": name}
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
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        api_version = self.config_entry.options.get(
            CONF_API_VERSION,
            self.config_entry.data.get(CONF_API_VERSION, DEFAULT_API_VERSION),
        )
        scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, 20)
        )
        correction_factor = self.config_entry.options.get(
            CONF_CORRECTION_FACTOR,
            self.config_entry.data.get(CONF_CORRECTION_FACTOR, "1.0"),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_API_VERSION, default=api_version): vol.In(API_VERSIONS),
                    vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): int,
                    vol.Optional(CONF_CORRECTION_FACTOR, default=correction_factor): str,
                }
            ),
        )
