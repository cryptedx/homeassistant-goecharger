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
homeassistant.components.switch = _install_module(
    "homeassistant.components.switch", types.ModuleType("homeassistant.components.switch")
)
homeassistant.components.switch.SwitchEntity = object
homeassistant.components.number = _install_module(
    "homeassistant.components.number", types.ModuleType("homeassistant.components.number")
)
homeassistant.components.number.NumberEntity = object
homeassistant.components.select = _install_module(
    "homeassistant.components.select", types.ModuleType("homeassistant.components.select")
)
homeassistant.components.select.SelectEntity = object
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
goecharger_api = importlib.import_module("custom_components.goecharger.api")
goecharger_number = importlib.import_module("custom_components.goecharger.number")
goecharger_select = importlib.import_module("custom_components.goecharger.select")
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


class ApiResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


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

    def test_v2_api_error_states_remain_available(self):
        chargers = {
            "unknown_error": goecharger_api.GoeChargerV2(
                "192.0.2.10",
                open_url=lambda request, timeout: ApiResponse({"car": 0, "err": 0}),
            ),
            "internal_error": goecharger_api.GoeChargerV2(
                "192.0.2.11",
                open_url=lambda request, timeout: ApiResponse({"car": None, "err": None}),
            ),
        }
        fetcher = goecharger_integration.ChargerStateFetcher(FakeHass(chargers))
        fetcher.coordinator = types.SimpleNamespace(data=None)

        data = asyncio.run(fetcher.fetch_states())

        self.assertEqual(data["unknown_error"]["car_status"], "error")
        self.assertEqual(data["unknown_error"]["charger_err"], "OK")
        self.assertEqual(data["internal_error"]["car_status"], "error")
        self.assertEqual(data["internal_error"]["charger_err"], "INTERNAL")

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

    def test_switch_uses_configured_name(self):
        switch = goecharger_switch.GoeChargerSwitch(
            types.SimpleNamespace(data={}),
            FakeHass({}),
            WorkingCharger(),
            "switch.test",
            "charger1",
            "Charging allowed",
            "allow_charging",
        )

        self.assertEqual(switch.name, "Charging allowed")

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

    def test_v2_extra_sensors_are_only_created_for_v2_chargers(self):
        hass = types.SimpleNamespace(
            data={
                goecharger_integration.DOMAIN: {
                    "coordinator": types.SimpleNamespace(data={}),
                }
            }
        )

        v1_sensors = goecharger_sensor._create_sensors_for_charger(
            "charger1", hass, 1.0, WorkingCharger()
        )
        v2_sensors = goecharger_sensor._create_sensors_for_charger(
            "charger1", hass, 1.0, goecharger_api.GoeChargerV2("192.0.2.10")
        )

        self.assertNotIn("p_grid", [sensor._attribute for sensor in v1_sensors])
        self.assertIn("p_grid", [sensor._attribute for sensor in v2_sensors])

    def test_v2_controls_are_only_created_for_v2_chargers(self):
        hass = types.SimpleNamespace(
            data={
                goecharger_integration.DOMAIN: {
                    "coordinator": types.SimpleNamespace(data={}),
                }
            }
        )

        self.assertEqual(
            goecharger_number._create_numbers_for_charger(hass, "charger1", WorkingCharger()),
            [],
        )
        self.assertEqual(
            goecharger_select._create_selects_for_charger(hass, "charger1", WorkingCharger()),
            [],
        )
        self.assertGreater(
            len(goecharger_number._create_numbers_for_charger(hass, "charger1", goecharger_api.GoeChargerV2("192.0.2.10"))),
            0,
        )
        self.assertGreater(
            len(goecharger_select._create_selects_for_charger(hass, "charger1", goecharger_api.GoeChargerV2("192.0.2.10"))),
            0,
        )

    def test_disabled_v2_charge_limit_is_exposed_as_zero(self):
        number = goecharger_number.GoeChargerNumber(
            types.SimpleNamespace(
                data={"charger1": {"charge_limit": None}},
                last_update_success=True,
            ),
            FakeHass({}),
            goecharger_api.GoeChargerV2("192.0.2.10"),
            "charger1",
            "dwo",
            goecharger_api.V2_NUMBERS["dwo"],
        )

        self.assertTrue(number.available)
        self.assertEqual(number.native_value, 0)

    def test_unavailable_v2_charge_limit_has_no_value(self):
        number = goecharger_number.GoeChargerNumber(
            types.SimpleNamespace(data={}, last_update_success=True),
            FakeHass({}),
            goecharger_api.GoeChargerV2("192.0.2.10"),
            "charger1",
            "dwo",
            goecharger_api.V2_NUMBERS["dwo"],
        )

        self.assertFalse(number.available)
        self.assertIsNone(number.native_value)

    def test_v2_number_enforces_dynamic_current_limit(self):
        class Coordinator:
            data = {
                "charger1": {
                    "charger_max_current": 6,
                    "charger_hardware_max_current": 16,
                    "charger_requested_current_limit": 16,
                }
            }
            last_update_success = True

            async def async_request_refresh(self):
                return None

        urls = []
        api = goecharger_api.GoeChargerV2(
            "192.0.2.10",
            open_url=lambda request, timeout: (
                urls.append(request.full_url) or ApiResponse({"ok": True})
            ),
        )
        number = goecharger_number.GoeChargerNumber(
            Coordinator(),
            FakeHass({}),
            api,
            "charger1",
            "amp",
            goecharger_api.V2_NUMBERS["amp"],
        )

        self.assertEqual(number.native_max_value, 16)
        with self.assertRaisesRegex(ValueError, "maximum is 16 A"):
            asyncio.run(number.async_set_native_value(17))
        self.assertEqual(urls, [])

        asyncio.run(number.async_set_native_value(16))
        self.assertIn("/api/set?amp=16", urls[0])

    def test_v2_phase_control_writes_psm(self):
        class Coordinator:
            data = {"charger1": {"phase_switch_mode": 2, "phase_wish_mode": 1}}
            last_update_success = True

            async def async_request_refresh(self):
                return None

        coordinator = Coordinator()
        urls = []
        api = goecharger_api.GoeChargerV2(
            "192.0.2.10",
            open_url=lambda request, timeout: (
                urls.append(request.full_url) or ApiResponse({"ok": True})
            ),
        )
        select = goecharger_select.GoeChargerSelect(
            coordinator,
            FakeHass({}),
            api,
            "charger1",
            "psm",
            goecharger_api.V2_SELECTS["psm"],
        )

        self.assertTrue(select.available)
        self.assertEqual(select.current_option, "Three phases")
        asyncio.run(select.async_select_option("Single phase"))
        self.assertIn("/api/set?psm=1", urls[0])

        hass = types.SimpleNamespace(
            data={goecharger_integration.DOMAIN: {"coordinator": coordinator}}
        )
        sensors = goecharger_sensor._create_sensors_for_charger(
            "charger1", hass, 1.0, api
        )
        self.assertIn("phase_wish_mode", [sensor._attribute for sensor in sensors])


if __name__ == "__main__":
    unittest.main()
