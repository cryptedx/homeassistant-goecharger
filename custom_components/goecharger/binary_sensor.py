"""Binary sensor platform for go-eCharger."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHARGERS, CONF_NAME, DOMAIN, charger_entity_id

_LOGGER = logging.getLogger(__name__)

_BINARY_SENSORS = {
    "car_connected": "Car connected",
    "charging": "Charging",
    "error_present": "Error present",
    "wifi_connected": "WiFi connected",
}

_CONNECTED_CAR_STATUSES = {
    "charging",
    "Waiting for vehicle",
    "charging finished, vehicle still connected",
}

_SOURCE_ATTRIBUTES = {
    "car_connected": "car_status",
    "charging": "car_status",
    "error_present": "charger_err",
    "wifi_connected": "wifi",
}


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    config = config_entry.as_dict()["data"]
    chargerName = config[CONF_NAME]
    async_add_entities(_create_binary_sensors_for_charger(hass, chargerName))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up go-eCharger binary sensor platform."""
    if discovery_info is None:
        return

    entities = []
    for charger in discovery_info[CONF_CHARGERS]:
        chargerName = charger[0][CONF_NAME]
        entities.extend(_create_binary_sensors_for_charger(hass, chargerName))
    async_add_entities(entities)


def _create_binary_sensors_for_charger(hass, chargerName):
    return [
        GoeChargerBinarySensor(
            hass.data[DOMAIN]["coordinator"],
            charger_entity_id("binary_sensor", chargerName, attribute),
            chargerName,
            attribute,
        )
        for attribute in _BINARY_SENSORS
    ]


class GoeChargerBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entity_id, chargerName, attribute):
        """Initialize the go-eCharger binary sensor."""
        super().__init__(coordinator)
        self.entity_id = entity_id
        self._chargername = chargerName
        self._attribute = attribute
        self._attr_name = _BINARY_SENSORS[attribute]

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._chargername)},
            "name": self._chargername,
            "manufacturer": "go-e",
            "model": "HOME",
        }

    @property
    def unique_id(self):
        """Return the unique_id of the binary sensor."""
        return f"{self._chargername}_{self._attribute}"

    @property
    def available(self):
        """Return if entity is available."""
        return super().available and _SOURCE_ATTRIBUTES[self._attribute] in self._charger_data()

    def _charger_data(self):
        return (self.coordinator.data or {}).get(self._chargername, {})

    @property
    def is_on(self):
        """Return the state of the binary sensor."""
        data = self._charger_data()
        if self._attribute == "car_connected":
            return data.get("car_status") in _CONNECTED_CAR_STATUSES
        if self._attribute == "charging":
            return data.get("car_status") == "charging"
        if self._attribute == "error_present":
            return data.get("charger_err") not in (None, "OK")
        return data.get("wifi") == "connected"
