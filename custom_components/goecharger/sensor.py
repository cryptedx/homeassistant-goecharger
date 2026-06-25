"""Platform for go-eCharger sensor integration."""
import logging
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfEnergy,
    UnitOfPower,
)

from homeassistant import core, config_entries
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorStateClass,
    SensorDeviceClass,
    SensorEntity
)


from .const import CHARGER_API, CONF_CHARGERS, DOMAIN, CONF_NAME, CONF_CORRECTION_FACTOR, charger_entity_id
from .api import GoeChargerV2

CARD_ID = 'Card ID'
PERCENT = '%'

_LOGGER = logging.getLogger(__name__)

_POWER_SENSORS = ('p_l1', 'p_l2', 'p_l3', 'p_n', 'p_all', 'p_grid', 'p_pv', 'p_akku')
_VOLTAGE_SENSORS = ('u_l1', 'u_l2', 'u_l3', 'u_n')
_CURRENT_SENSORS = (
    'i_l1',
    'i_l2',
    'i_l3',
    'charger_max_current',
    'charger_absolute_max_current',
    'cable_max_current',
    'allowed_current',
)
_TEMPERATURE_SENSORS = ('charger_temp', 'charger_temp0', 'charger_temp1', 'charger_temp2', 'charger_temp3')

_sensorUnits = {
    'charger_temp': {'unit': UnitOfTemperature.CELSIUS, 'name': 'Charger Temp'},
    'charger_temp0': {'unit': UnitOfTemperature.CELSIUS, 'name': 'Charger Temp 0'},
    'charger_temp1': {'unit': UnitOfTemperature.CELSIUS, 'name': 'Charger Temp 1'},
    'charger_temp2': {'unit': UnitOfTemperature.CELSIUS, 'name': 'Charger Temp 2'},
    'charger_temp3': {'unit': UnitOfTemperature.CELSIUS, 'name': 'Charger Temp 3'},
    'p_l1': {'unit': UnitOfPower.KILO_WATT, 'name': 'Power L1'},
    'p_l2': {'unit': UnitOfPower.KILO_WATT, 'name': 'Power L2'},
    'p_l3': {'unit': UnitOfPower.KILO_WATT, 'name': 'Power L3'},
    'p_n': {'unit': UnitOfPower.KILO_WATT, 'name': 'Power N'},
    'p_all': {'unit': UnitOfPower.KILO_WATT, 'name': 'Power All'},
    'current_session_charged_energy': {'unit': UnitOfEnergy.KILO_WATT_HOUR, 'name': 'Current Session charged'},
    'current_session_charged_energy_corrected': {'unit': UnitOfEnergy.KILO_WATT_HOUR, 'name': 'Current Session charged corrected'},
    'energy_total': {'unit': UnitOfEnergy.KILO_WATT_HOUR, 'name': 'Total Charged'},
    'energy_total_corrected': {'unit': UnitOfEnergy.KILO_WATT_HOUR, 'name': 'Total Charged corrected'},
    'charge_limit': {'unit': UnitOfEnergy.KILO_WATT_HOUR, 'name': 'Charge limit'},
    'u_l1': {'unit': UnitOfElectricPotential.VOLT, 'name': 'Voltage L1'},
    'u_l2': {'unit': UnitOfElectricPotential.VOLT, 'name': 'Voltage L2'},
    'u_l3': {'unit': UnitOfElectricPotential.VOLT, 'name': 'Voltage L3'},
    'u_n': {'unit': UnitOfElectricPotential.VOLT, 'name': 'Voltage N'},
    'i_l1': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Current L1'},
    'i_l2': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Current L2'},
    'i_l3': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Current L3'},
    'charger_max_current': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Charger max current setting'},
    'charger_absolute_max_current': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Charger absolute max current setting'},
    'cable_lock_mode': {'unit': '', 'name': 'Cable lock mode'},
    'cable_max_current': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Cable max current'},
    'unlocked_by_card': {'unit': CARD_ID, 'name': 'Card used'},
    'lf_l1': {'unit': PERCENT, 'name': 'Power factor L1'},
    'lf_l2': {'unit': PERCENT, 'name': 'Power factor L2'},
    'lf_l3': {'unit': PERCENT, 'name': 'Power factor L3'},
    'lf_n': {'unit': PERCENT, 'name': 'Loadfactor N'},
    'car_status': {'unit': '', 'name': 'Status'}
}
_v2SensorUnits = {
    'model_status': {'unit': '', 'name': 'Model status'},
    'allowed_current': {'unit': UnitOfElectricCurrent.AMPERE, 'name': 'Allowed current'},
    'force_single_phase': {'unit': '', 'name': 'Force single phase'},
    'p_grid': {'unit': UnitOfPower.KILO_WATT, 'name': 'Grid power'},
    'p_pv': {'unit': UnitOfPower.KILO_WATT, 'name': 'PV power'},
    'p_akku': {'unit': UnitOfPower.KILO_WATT, 'name': 'Battery power'},
}

_sensorStateClass = {
    'energy_total': SensorStateClass.TOTAL_INCREASING,
    'energy_total_corrected': SensorStateClass.TOTAL_INCREASING,
    'current_session_charged_energy': SensorStateClass.TOTAL_INCREASING,
    'current_session_charged_energy_corrected': SensorStateClass.TOTAL_INCREASING,
    **{
        sensor: SensorStateClass.MEASUREMENT
        for sensor in _POWER_SENSORS + _VOLTAGE_SENSORS + _CURRENT_SENSORS + _TEMPERATURE_SENSORS
    },
}

_sensorDeviceClass = {
    'energy_total': SensorDeviceClass.ENERGY,
    'energy_total_corrected': SensorDeviceClass.ENERGY,
    'current_session_charged_energy': SensorDeviceClass.ENERGY,
    'current_session_charged_energy_corrected': SensorDeviceClass.ENERGY,
    **{sensor: SensorDeviceClass.POWER for sensor in _POWER_SENSORS},
    **{sensor: SensorDeviceClass.VOLTAGE for sensor in _VOLTAGE_SENSORS},
    **{sensor: SensorDeviceClass.CURRENT for sensor in _CURRENT_SENSORS},
    **{sensor: SensorDeviceClass.TEMPERATURE for sensor in _TEMPERATURE_SENSORS},
}

_sensors = [
    'car_status',
    'charger_max_current',
    'charger_absolute_max_current',
    'charger_err',
    'charger_access',
    'stop_mode',
    'cable_lock_mode',
    'cable_max_current',
    'pre_contactor_l1',
    'pre_contactor_l2',
    'pre_contactor_l3',
    'post_contactor_l1',
    'post_contactor_l2',
    'post_contactor_l3',
    'charger_temp',
    'charger_temp0',
    'charger_temp1',
    'charger_temp2',
    'charger_temp3',
    'current_session_charged_energy',
    'current_session_charged_energy_corrected',
    'charge_limit',
    'adapter',
    'unlocked_by_card',
    'energy_total',
    'energy_total_corrected',
    'wifi',

    'u_l1',
    'u_l2',
    'u_l3',
    'u_n',
    'i_l1',
    'i_l2',
    'i_l3',
    'p_l1',
    'p_l2',
    'p_l3',
    'p_n',
    'p_all',
    'lf_l1',
    'lf_l2',
    'lf_l3',
    'lf_n',

    'firmware',
    'serial_number',
    'wifi_ssid',
    'wifi_enabled',
    'timezone_offset',
    'timezone_dst_offset',
]
_v2Sensors = [
    'model_status',
    'allowed_current',
    'force_single_phase',
    'p_grid',
    'p_pv',
    'p_akku',
]


def _create_sensors_for_charger(chargerName, hass, correctionFactor, chargerApi=None):
    entities = []

    sensors = _sensors + (_v2Sensors if isinstance(chargerApi, GoeChargerV2) else [])
    sensorUnits = {**_sensorUnits, **_v2SensorUnits}

    for sensor in sensors:

        _LOGGER.debug(f"adding Sensor: {sensor} for charger {chargerName}")
        sensorUnit = sensorUnits.get(sensor).get('unit') if sensorUnits.get(sensor) else ''
        sensorName = sensorUnits.get(sensor).get('name') if sensorUnits.get(sensor) else sensor
        sensorStateClass = _sensorStateClass[sensor] if sensor in _sensorStateClass else ''
        sensorDeviceClass = _sensorDeviceClass[sensor] if sensor in _sensorDeviceClass else ''
        entities.append(
            GoeChargerSensor(
                hass.data[DOMAIN]["coordinator"],
                charger_entity_id("sensor", chargerName, sensor),
                chargerName, sensorName, sensor, sensorUnit, sensorStateClass, sensorDeviceClass, correctionFactor
            )
        )

    return entities


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    _LOGGER.debug("setup sensors...")
    config = config_entry.as_dict()["data"]

    chargerName = config[CONF_NAME]

    correctionFactor = 1.0
    if CONF_CORRECTION_FACTOR in config:
        try:
            correctionFactor = float(config[CONF_CORRECTION_FACTOR])
        except:
            correctionFactor = 1.0 

    _LOGGER.debug(f"charger name: '{chargerName}'")
    _LOGGER.debug(f"config: '{config}'")
    async_add_entities(_create_sensors_for_charger(chargerName, hass, correctionFactor, hass.data[DOMAIN]["api"][chargerName]))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up go-eCharger Sensor platform."""
    _LOGGER.debug("setup_platform")
    if discovery_info is None:
        return

    chargers = discovery_info[CONF_CHARGERS]
    chargerApi = discovery_info.get(CHARGER_API, {})

    entities = []
    for charger in chargers:
        chargerName = charger[0][CONF_NAME]
        _LOGGER.debug(f"charger name: '{chargerName}'")
        _LOGGER.debug(f"charger[0]: '{charger[0]}'")
        correctionFactor = 1.0
        if CONF_CORRECTION_FACTOR in charger[0]:
            try:
                correctionFactor = charger[0][CONF_CORRECTION_FACTOR]
            except:
                __LOGGER.warn(f"can't parse correctionFactor. Using 1.0")
                correctionFactor = 1.0

        entities.extend(_create_sensors_for_charger(chargerName, hass, correctionFactor, chargerApi.get(chargerName)))

    async_add_entities(entities)


class GoeChargerSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entity_id, chargerName, name, attribute, unit, stateClass, deviceClass, correctionFactor):
        """Initialize the go-eCharger sensor."""

        super().__init__(coordinator)
        self._chargername = chargerName
        self.entity_id = entity_id
        self._name = name
        self._attribute = attribute
        self._unit = unit
        self._attr_state_class = stateClass
        self._attr_device_class = deviceClass
        self.correctionFactor = correctionFactor


    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._chargername)
            },
            "name": self._chargername,
            "manufacturer": "go-e",
            "model": "HOME",
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique_id of the sensor."""
        return f"{self._chargername}_{self._attribute}"

    def _charger_data(self):
        return (self.coordinator.data or {}).get(self._chargername, {})

    @property
    def available(self):
        """Return if entity is available."""
        if not super().available:
            return False
        data = self._charger_data()
        if self._attribute == 'energy_total_corrected':
            return 'energy_total' in data
        if self._attribute == 'current_session_charged_energy_corrected':
            return 'current_session_charged_energy' in data
        return self._attribute in data

    @property
    def state(self):
        """Return the state of the sensor."""
        data = self._charger_data()
        if (self._attribute == 'energy_total_corrected'):
            value = data.get('energy_total')
            return value * self.correctionFactor if value is not None else None
        if (self._attribute == 'current_session_charged_energy_corrected'):
            value = data.get('current_session_charged_energy')
            return value * self.correctionFactor if value is not None else None
        return data.get(self._attribute)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit
