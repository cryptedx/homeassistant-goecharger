import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


voluptuous = _install_module("voluptuous", types.ModuleType("voluptuous"))
voluptuous.ALLOW_EXTRA = object()
voluptuous.Schema = lambda *args, **kwargs: lambda value: value
voluptuous.All = lambda *args, **kwargs: lambda value: value
voluptuous.Optional = lambda key, **kwargs: key
voluptuous.Required = lambda key, **kwargs: key
voluptuous.Clamp = lambda *args, **kwargs: lambda value: value
voluptuous.In = lambda *args, **kwargs: lambda value: value

homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant.const.UnitOfElectricCurrent = types.SimpleNamespace(AMPERE="A")
homeassistant.const.UnitOfElectricPotential = types.SimpleNamespace(VOLT="V")
homeassistant.const.UnitOfEnergy = types.SimpleNamespace(KILO_WATT_HOUR="kWh")
homeassistant.const.UnitOfPower = types.SimpleNamespace(KILO_WATT="kW")
homeassistant.const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="C")
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.core.valid_entity_id = lambda value: False
homeassistant.config_entries = _install_module(
    "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
)
homeassistant.config_entries.ConfigEntry = object
homeassistant.components = _install_module(
    "homeassistant.components", types.ModuleType("homeassistant.components")
)
homeassistant.components.sensor = _install_module(
    "homeassistant.components.sensor", types.ModuleType("homeassistant.components.sensor")
)
homeassistant.components.sensor.SensorDeviceClass = types.SimpleNamespace(
    CURRENT="current",
    ENERGY="energy",
    POWER="power",
    TEMPERATURE="temperature",
    VOLTAGE="voltage",
)
homeassistant.components.sensor.SensorEntity = object
homeassistant.components.sensor.SensorStateClass = types.SimpleNamespace(
    MEASUREMENT="measurement",
    TOTAL_INCREASING="total_increasing",
)
homeassistant.helpers = _install_module("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
homeassistant.helpers.config_validation = _install_module(
    "homeassistant.helpers.config_validation", types.ModuleType("homeassistant.helpers.config_validation")
)
homeassistant.helpers.config_validation.ensure_list = lambda value: value
homeassistant.helpers.config_validation.string = str
homeassistant.helpers.config_validation.time_period = lambda value: value
homeassistant.helpers.discovery = _install_module(
    "homeassistant.helpers.discovery", types.ModuleType("homeassistant.helpers.discovery")
)
homeassistant.helpers.discovery.async_load_platform = lambda *args, **kwargs: None
homeassistant.helpers.update_coordinator = _install_module(
    "homeassistant.helpers.update_coordinator", types.ModuleType("homeassistant.helpers.update_coordinator")
)
homeassistant.helpers.update_coordinator.DataUpdateCoordinator = object


class UpdateFailed(Exception):
    pass


class CoordinatorEntity:
    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator

    @property
    def available(self):
        return getattr(self.coordinator, "last_update_success", True)


homeassistant.helpers.update_coordinator.CoordinatorEntity = CoordinatorEntity
homeassistant.helpers.update_coordinator.UpdateFailed = UpdateFailed

goecharger = _install_module("goecharger", types.ModuleType("goecharger"))
goecharger.GoeCharger = object

sys.path.insert(0, str(ROOT))


class SensorMetadataTests(unittest.TestCase):
    def _sensors_by_attribute(self):
        goecharger_sensor = importlib.import_module("custom_components.goecharger.sensor")
        hass = types.SimpleNamespace(
            data={
                goecharger_sensor.DOMAIN: {
                    "coordinator": types.SimpleNamespace(data={}),
                }
            }
        )

        return {
            sensor._attribute: sensor
            for sensor in goecharger_sensor._create_sensors_for_charger("charger1", hass, 1.0)
        }

    def test_measurement_sensors_have_units_and_device_classes(self):
        sensors = self._sensors_by_attribute()

        self.assertEqual(sensors["p_all"].unit_of_measurement, "kW")
        self.assertEqual(sensors["p_all"]._attr_device_class, "power")
        self.assertEqual(sensors["p_all"]._attr_state_class, "measurement")

        self.assertEqual(sensors["u_l1"].unit_of_measurement, "V")
        self.assertEqual(sensors["u_l1"]._attr_device_class, "voltage")
        self.assertEqual(sensors["u_l1"]._attr_state_class, "measurement")

        self.assertEqual(sensors["i_l1"].unit_of_measurement, "A")
        self.assertEqual(sensors["i_l1"]._attr_device_class, "current")
        self.assertEqual(sensors["i_l1"]._attr_state_class, "measurement")


if __name__ == "__main__":
    unittest.main()
