"""Platform for go-eCharger switch integration."""
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant import core, config_entries

from .const import DOMAIN, CONF_CHARGERS, CONF_NAME, CHARGER_API, charger_entity_id
from .api import GoeChargerV2, V2_SWITCHES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    _LOGGER.debug("setup switch...")
    _LOGGER.debug(repr(config_entry.as_dict()))
    config = config_entry.as_dict()["data"]

    chargerName = config[CONF_NAME]
    chargerApi = hass.data[DOMAIN]["api"][chargerName]

    async_add_entities(_create_switches_for_charger(hass, chargerName, chargerApi))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up go-eCharger Switch platform."""
    if discovery_info is None:
        return
    _LOGGER.debug("setup_platform")

    chargers = discovery_info[CONF_CHARGERS]
    chargerApi = discovery_info[CHARGER_API]

    entities = []

    for charger in chargers:
        chargerName = charger[0][CONF_NAME]

        entities.extend(_create_switches_for_charger(hass, chargerName, chargerApi[chargerName]))
    async_add_entities(entities)


def _create_switches_for_charger(hass, chargerName, chargerApi):
    switches = [
        GoeChargerSwitch(
            hass.data[DOMAIN]["coordinator"],
            hass,
            chargerApi,
            charger_entity_id("switch", chargerName, "allow_charging"),
            chargerName,
            "Charging allowed",
            "allow_charging",
        )
    ]
    if isinstance(chargerApi, GoeChargerV2):
        for key, description in V2_SWITCHES.items():
            attribute = description["attribute"]
            switches.append(
                GoeChargerSwitch(
                    hass.data[DOMAIN]["coordinator"],
                    hass,
                    chargerApi,
                    charger_entity_id("switch", chargerName, attribute),
                    chargerName,
                    description["name"],
                    attribute,
                    key,
                )
            )
    return switches


class GoeChargerSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, hass, goeCharger, entity_id, chargerName, name, attribute, api_key=None):
        """Initialize the go-eCharger switch."""
        super().__init__(coordinator)
        self.entity_id = entity_id
        self._chargername = chargerName
        self._name = name
        self._attribute = attribute
        self._api_key = api_key
        self.hass = hass
        self._goeCharger = goeCharger
        self._state = None

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._chargername)
            },
            "name": self.name,
            "manufacturer": "go-e",
            "model": "HOME",
        }

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if self._api_key:
            await self.hass.async_add_executor_job(self._goeCharger.setApiKey, self._api_key, True)
        else:
            await self.hass.async_add_executor_job(self._goeCharger.setAllowCharging, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        if self._api_key:
            await self.hass.async_add_executor_job(self._goeCharger.setApiKey, self._api_key, False)
        else:
            await self.hass.async_add_executor_job(self._goeCharger.setAllowCharging, False)
        await self.coordinator.async_request_refresh()

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique_id of the switch."""
        return f"{self._chargername}_{self._attribute}"

    @property
    def available(self):
        """Return if entity is available."""
        return super().available and self._attribute in (self.coordinator.data or {}).get(self._chargername, {})

    @property
    def is_on(self):
        """Return the state of the switch."""
        state = (self.coordinator.data or {}).get(self._chargername, {}).get(self._attribute)
        return None if state is None else state == "on"
