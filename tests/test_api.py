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
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.core.valid_entity_id = lambda value: False
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
homeassistant.helpers.update_coordinator.UpdateFailed = Exception

goecharger = sys.modules.setdefault("goecharger", types.ModuleType("goecharger"))


class FakeV1Charger:
    def __init__(self, host):
        self.host = host

    def requestStatus(self):
        return {"car_status": "idle"}


goecharger.GoeCharger = FakeV1Charger


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ApiTests(unittest.TestCase):
    def test_api_version_constants_are_stable(self):
        from custom_components.goecharger import const

        self.assertEqual(const.CONF_API_VERSION, "api_version")
        self.assertEqual(const.API_VERSION_V1, "v1")
        self.assertEqual(const.API_VERSION_V2, "v2")
        self.assertEqual(const.DEFAULT_API_VERSION, "v1")

    def test_factory_returns_selected_backend(self):
        from custom_components.goecharger.api import GoeChargerV1, GoeChargerV2, create_charger

        goecharger.GoeCharger = FakeV1Charger
        self.assertIsInstance(create_charger("192.0.2.10", None), GoeChargerV1)
        self.assertIsInstance(create_charger("192.0.2.10", "v2"), GoeChargerV2)
        with self.assertRaises(ValueError):
            create_charger("192.0.2.10", "v3")

    def test_v2_status_maps_existing_and_v2_fields(self):
        from custom_components.goecharger.api import GoeChargerV2

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse(
                {
                    "car": 2,
                    "amp": 16,
                    "ama": 32,
                    "alw": True,
                    "dwo": 2500,
                    "eto": 123456,
                    "frc": 2,
                    "fup": True,
                    "fwv": "060.0",
                    "lmo": 3,
                    "mca": 6,
                    "modelStatus": 3,
                    "nrg": [230, 231, 232, 0, 6.1, 6.2, 6.3, 1400, 1410, 1420, 0, 4230, 100, 99, 98, 0],
                    "pgrid": -120.5,
                    "ppv": 820.0,
                    "sse": "123456",
                    "ust": 1,
                    "wh": 1500,
                    "wst": 3,
                }
            )

        status = GoeChargerV2("192.0.2.10", open_url=open_url).requestStatus()

        self.assertIn("/api/status?filter=", urls[0])
        self.assertNotIn("%5B", urls[0])
        self.assertEqual(status["car_status"], "charging")
        self.assertEqual(status["charger_max_current"], 16)
        self.assertEqual(status["charger_absolute_max_current"], 32)
        self.assertEqual(status["allow_charging"], "on")
        self.assertEqual(status["charge_limit"], 2.5)
        self.assertEqual(status["current_session_charged_energy"], 1.5)
        self.assertEqual(status["energy_total"], 123.456)
        self.assertEqual(status["p_all"], 4.23)
        self.assertEqual(status["force_state"], 2)
        self.assertEqual(status["pv_surplus"], "on")
        self.assertEqual(status["logic_mode"], 3)
        self.assertEqual(status["model_status"], 3)
        self.assertEqual(status["p_grid"], -120.5)
        self.assertEqual(status["p_pv"], 820.0)

    def test_v2_writes_existing_controls_and_expert_keys(self):
        from custom_components.goecharger.api import GoeChargerV2

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse({"ok": True})

        charger = GoeChargerV2("192.0.2.10", open_url=open_url)
        charger.setTmpMaxCurrent(16)
        charger.setAbsoluteMaxCurrent(32)
        charger.setCableLockMode(2)
        charger.setChargeLimit(2.5)
        charger.setAllowCharging(False)
        charger.setApiKey("fup", True)

        self.assertIn("/api/set?amp=16", urls[0])
        self.assertIn("/api/set?ama=32", urls[1])
        self.assertIn("/api/set?ust=2", urls[2])
        self.assertIn("/api/set?dwo=2500", urls[3])
        self.assertIn("/api/set?frc=1", urls[4])
        self.assertIn("/api/set?fup=true", urls[5])

    def test_v2_feature_descriptions_cover_curated_entities(self):
        from custom_components.goecharger.api import V2_NUMBERS, V2_SELECTS, V2_SWITCHES

        self.assertIn("amp", V2_NUMBERS)
        self.assertIn("frc", V2_SELECTS)
        self.assertIn("fup", V2_SWITCHES)

    def test_integration_uses_adapter_factory(self):
        source = (ROOT / "custom_components" / "goecharger" / "__init__.py").read_text(encoding="utf-8")

        self.assertIn("from .api import create_charger", source)
        self.assertIn("create_charger(", source)
        self.assertNotIn("GoeCharger(", source)

    def test_switch_uses_stored_adapter(self):
        source = (ROOT / "custom_components" / "goecharger" / "switch.py").read_text(encoding="utf-8")

        self.assertIn('hass.data[DOMAIN]["api"][chargerName]', source)
        self.assertNotIn("GoeCharger(host)", source)


if __name__ == "__main__":
    unittest.main()
