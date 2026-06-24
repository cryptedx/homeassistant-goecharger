"""Select platform for go-eCharger API v2 controls."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GoeChargerV2, V2_SELECTS
from .const import CHARGER_API, CONF_CHARGERS, CONF_NAME, DOMAIN, charger_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = config_entry.as_dict()["data"]
    chargerName = config[CONF_NAME]
    async_add_entities(_create_selects_for_charger(hass, chargerName, hass.data[DOMAIN]["api"][chargerName]))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return
    entities = []
    for charger in discovery_info[CONF_CHARGERS]:
        chargerName = charger[0][CONF_NAME]
        entities.extend(_create_selects_for_charger(hass, chargerName, discovery_info[CHARGER_API][chargerName]))
    async_add_entities(entities)


def _create_selects_for_charger(hass, chargerName, chargerApi):
    if not isinstance(chargerApi, GoeChargerV2):
        return []
    return [
        GoeChargerSelect(
            hass.data[DOMAIN]["coordinator"],
            hass,
            chargerApi,
            chargerName,
            key,
            description,
        )
        for key, description in V2_SELECTS.items()
    ]


class GoeChargerSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, hass, chargerApi, chargerName, api_key, description):
        super().__init__(coordinator)
        self.hass = hass
        self._chargerApi = chargerApi
        self._chargername = chargerName
        self._api_key = api_key
        self._attribute = description.get("attribute", api_key)
        self._options = description["options"]
        self._reverse_options = {value: option for option, value in self._options.items()}
        self._attr_name = description["name"]
        self._attr_options = list(self._options)
        self.entity_id = charger_entity_id("select", chargerName, self._attribute)
        self._attr_unique_id = f"{chargerName}_{self._attribute}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._chargername)},
            "name": self._chargername,
            "manufacturer": "go-e",
            "model": "HOME",
        }

    @property
    def available(self):
        return super().available and self._attribute in (self.coordinator.data or {}).get(self._chargername, {})

    @property
    def current_option(self):
        value = (self.coordinator.data or {}).get(self._chargername, {}).get(self._attribute)
        return self._reverse_options.get(value)

    async def async_select_option(self, option):
        await self.hass.async_add_executor_job(self._chargerApi.setApiKey, self._api_key, self._options[option])
        await self.coordinator.async_request_refresh()
