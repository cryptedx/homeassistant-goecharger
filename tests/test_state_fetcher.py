import asyncio
import importlib
import json
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

homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant.const.UnitOfEnergy = types.SimpleNamespace(KILO_WATT_HOUR="kWh")
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
homeassistant.components.sensor.SensorDeviceClass = types.SimpleNamespace(ENERGY="energy")
homeassistant.components.sensor.SensorEntity = object
homeassistant.components.sensor.SensorStateClass = types.SimpleNamespace(TOTAL_INCREASING="total_increasing")
homeassistant.components.switch = _install_module(
    "homeassistant.components.switch", types.ModuleType("homeassistant.components.switch")
)
homeassistant.components.switch.SwitchEntity = object
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
goecharger_integration = importlib.import_module("custom_components.goecharger")
goecharger_sensor = importlib.import_module("custom_components.goecharger.sensor")
goecharger_switch = importlib.import_module("custom_components.goecharger.switch")


class FakeHass:
    def __init__(self, chargers):
        self.data = {goecharger_integration.DOMAIN: {"api": chargers}}

    async def async_add_executor_job(self, job, *args):
        return job(*args)


class BrokenCharger:
    def requestStatus(self):
        raise json.JSONDecodeError("Expecting value", "", 0)


class WorkingCharger:
    def requestStatus(self):
        return {"car_status": "idle", "p_all": 0}


class StateFetcherTests(unittest.TestCase):
    def test_bad_charger_response_does_not_abort_update(self):
        fetcher = goecharger_integration.ChargerStateFetcher(
            FakeHass({"broken": BrokenCharger(), "working": WorkingCharger()})
        )
        fetcher.coordinator = types.SimpleNamespace(
            data={"broken": {"car_status": "charging", "p_all": 2}}
        )

        with self.assertLogs(goecharger_integration._LOGGER, level="ERROR") as logs:
            data = asyncio.run(fetcher.fetch_states())

        self.assertNotIn("broken", data)
        self.assertEqual(data["working"], {"car_status": "idle", "p_all": 0})
        self.assertIn("Unable to fetch state for Charger broken", logs.output[0])

    def test_all_bad_charger_responses_fail_update(self):
        fetcher = goecharger_integration.ChargerStateFetcher(
            FakeHass({"broken": BrokenCharger()})
        )
        fetcher.coordinator = types.SimpleNamespace(data=None)

        with self.assertLogs(goecharger_integration._LOGGER, level="ERROR"):
            with self.assertRaises(UpdateFailed):
                asyncio.run(fetcher.fetch_states())

    def test_sensor_is_unavailable_without_charger_data(self):
        sensor = goecharger_sensor.GoeChargerSensor(
            types.SimpleNamespace(data={}),
            "sensor.test",
            "broken",
            "Power",
            "p_all",
            "kW",
            "",
            "",
            1.0,
        )

        self.assertFalse(sensor.available)
        self.assertIsNone(sensor.state)

    def test_switch_is_unavailable_without_charger_data(self):
        switch = goecharger_switch.GoeChargerSwitch(
            types.SimpleNamespace(data={}),
            FakeHass({}),
            WorkingCharger(),
            "switch.test",
            "broken",
            "Charging allowed",
            "allow_charging",
        )

        self.assertFalse(switch.available)
        self.assertIsNone(switch.is_on)

    def test_entities_are_unavailable_when_coordinator_update_failed(self):
        coordinator = types.SimpleNamespace(
            data={"broken": {"p_all": 1, "allow_charging": "on"}},
            last_update_success=False,
        )
        sensor = goecharger_sensor.GoeChargerSensor(
            coordinator,
            "sensor.test",
            "broken",
            "Power",
            "p_all",
            "kW",
            "",
            "",
            1.0,
        )
        switch = goecharger_switch.GoeChargerSwitch(
            coordinator,
            FakeHass({}),
            WorkingCharger(),
            "switch.test",
            "broken",
            "Charging allowed",
            "allow_charging",
        )

        self.assertFalse(sensor.available)
        self.assertFalse(switch.available)


if __name__ == "__main__":
    unittest.main()
