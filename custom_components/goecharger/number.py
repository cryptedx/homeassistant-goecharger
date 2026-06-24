"""Number platform for go-eCharger API v2 controls."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.number import NumberEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GoeChargerV2, V2_NUMBERS
from .const import CHARGER_API, CONF_CHARGERS, CONF_NAME, DOMAIN, charger_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = config_entry.as_dict()["data"]
    chargerName = config[CONF_NAME]
    async_add_entities(_create_numbers_for_charger(hass, chargerName, hass.data[DOMAIN]["api"][chargerName]))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return
    entities = []
    for charger in discovery_info[CONF_CHARGERS]:
        chargerName = charger[0][CONF_NAME]
        entities.extend(_create_numbers_for_charger(hass, chargerName, discovery_info[CHARGER_API][chargerName]))
    async_add_entities(entities)


def _create_numbers_for_charger(hass, chargerName, chargerApi):
    if not isinstance(chargerApi, GoeChargerV2):
        return []
    return [
        GoeChargerNumber(
            hass.data[DOMAIN]["coordinator"],
            hass,
            chargerApi,
            chargerName,
            key,
            description,
        )
        for key, description in V2_NUMBERS.items()
    ]


class GoeChargerNumber(CoordinatorEntity, NumberEntity):
    def __init__(self, coordinator, hass, chargerApi, chargerName, api_key, description):
        super().__init__(coordinator)
        self.hass = hass
        self._chargerApi = chargerApi
        self._chargername = chargerName
        self._api_key = api_key
        self._attribute = description.get("attribute", api_key)
        self._attr_name = description["name"]
        self.entity_id = charger_entity_id("number", chargerName, self._attribute)
        self._attr_unique_id = f"{chargerName}_{self._attribute}"
        self._attr_native_min_value = description["min"]
        self._attr_native_max_value = description["max"]
        self._attr_native_step = description["step"]
        self._attr_native_unit_of_measurement = description["unit"]

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
    def native_value(self):
        return (self.coordinator.data or {}).get(self._chargername, {}).get(self._attribute)

    async def async_set_native_value(self, value):
        if self._api_key == "dwo":
            value = None if value <= 0 else int(value * 1000)
        await self.hass.async_add_executor_job(self._chargerApi.setApiKey, self._api_key, value)
        await self.coordinator.async_request_refresh()
