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
        self.assertEqual(const.API_VERSION_AUTO, "auto")
        self.assertEqual(const.DEFAULT_API_VERSION, "v1")
        self.assertEqual(set(const.API_VERSIONS), {const.API_VERSION_V1, const.API_VERSION_V2})
        self.assertEqual(
            set(getattr(const, "API_VERSION_OPTIONS", {})),
            {const.API_VERSION_AUTO, const.API_VERSION_V1, const.API_VERSION_V2},
        )
        self.assertEqual(const.API_VERSION_OPTIONS[const.API_VERSION_AUTO], "Auto-detect")
        self.assertEqual(const.API_VERSIONS[const.API_VERSION_V1], "v1")
        self.assertEqual(const.API_VERSIONS[const.API_VERSION_V2], "v2 (recommended)")

    def test_factory_returns_selected_backend(self):
        from custom_components.goecharger.api import GoeChargerV1, GoeChargerV2, create_charger

        goecharger.GoeCharger = FakeV1Charger
        self.assertIsInstance(create_charger("192.0.2.10", None), GoeChargerV1)
        self.assertIsInstance(create_charger("192.0.2.10", "v2"), GoeChargerV2)
        with self.assertRaises(ValueError):
            create_charger("192.0.2.10", "v3")

    def test_factory_rejects_auto_without_detecting(self):
        from custom_components.goecharger import api
        from custom_components.goecharger.const import API_VERSION_AUTO

        original_detect = api.detect_api_version
        try:
            api.detect_api_version = lambda host: self.fail("create_charger must not auto-detect")
            with self.assertRaises(ValueError):
                api.create_charger("192.0.2.10", API_VERSION_AUTO)
        finally:
            api.detect_api_version = original_detect

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
                    "pakku": 50.0,
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
        self.assertEqual(status["p_grid"], -0.12)
        self.assertEqual(status["p_pv"], 0.82)
        self.assertEqual(status["p_akku"], 0.05)

    def test_v2_number_status_fields_match_their_api_keys(self):
        from custom_components.goecharger.api import GoeChargerV2

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse(
                {
                    "car": 1,
                    "err": 0,
                    "mca": 6,
                    "fst": 1400,
                    "pgt": -500,
                    "zfo": 100,
                }
            )

        status = GoeChargerV2("192.0.2.10", open_url=open_url).requestStatus()

        self.assertIn("pgt", urls[0])
        self.assertEqual(
            {key: status.get(key) for key in ("mca", "fst", "pgt", "zfo")},
            {"mca": 6, "fst": 1400, "pgt": -500, "zfo": 100},
        )

    def test_v2_current_limits_follow_hardware_and_configuration(self):
        from custom_components.goecharger.api import GoeChargerV2

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse(
                {"car": 1, "err": 0, "fwv": "60.5", "adi": True, "ama": 16, "var": 22}
                if "/api/status" in request.full_url
                else {"ok": True}
            )

        charger = GoeChargerV2("192.0.2.10", open_url=open_url)
        status = charger.requestStatus()

        self.assertEqual(status["charger_hardware_max_current"], 16)
        self.assertEqual(status["charger_requested_current_limit"], 16)

        charger.setTmpMaxCurrent(32)
        charger.setAbsoluteMaxCurrent(32)
        charger.setApiKey("mca", 32)

        self.assertIn("/api/set?amp=16", urls[-3])
        self.assertIn("/api/set?ama=16", urls[-2])
        self.assertIn("/api/set?mca=16", urls[-1])

        status_32a = GoeChargerV2(
            "192.0.2.11",
            open_url=lambda request, timeout: FakeResponse(
                {"car": 1, "err": 0, "fwv": "60.5", "adi": False, "ama": 32, "var": 22}
            ),
        ).requestStatus()

        self.assertEqual(status_32a["charger_hardware_max_current"], 32)
        self.assertEqual(status_32a["charger_requested_current_limit"], 32)

        status_configured_16a = GoeChargerV2(
            "192.0.2.12",
            open_url=lambda request, timeout: FakeResponse(
                {"car": 1, "err": 0, "fwv": "60.5", "adi": False, "ama": 16, "var": 22}
            ),
        ).requestStatus()
        self.assertEqual(status_configured_16a["charger_hardware_max_current"], 32)
        self.assertEqual(status_configured_16a["charger_requested_current_limit"], 16)

        status_11kw = GoeChargerV2(
            "192.0.2.13",
            open_url=lambda request, timeout: FakeResponse(
                {"car": 1, "err": 0, "fwv": "60.5", "adi": False, "ama": 32, "var": 11}
            ),
        ).requestStatus()
        self.assertEqual(status_11kw["charger_hardware_max_current"], 16)
        self.assertEqual(status_11kw["charger_requested_current_limit"], 16)

    def test_v2_phase_status_and_control_are_separate(self):
        from custom_components.goecharger.api import GoeChargerV2, V2_SELECTS

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse({"car": 1, "err": 0, "fwv": "60.5", "psm": 2, "pwm": 1})

        status = GoeChargerV2("192.0.2.10", open_url=open_url).requestStatus()

        self.assertIn("psm", urls[0])
        self.assertIn("pwm", urls[0])
        self.assertEqual(status["phase_wish_mode"], "Wish 1")
        self.assertEqual(status["phase_switch_mode"], 2)
        self.assertNotIn("pwm", V2_SELECTS)
        self.assertIn("psm", V2_SELECTS)

        missing = GoeChargerV2(
            "192.0.2.11",
            open_url=lambda request, timeout: FakeResponse(
                {"car": 1, "err": 0, "fwv": "60.5"}
            ),
        ).requestStatus()
        self.assertNotIn("phase_switch_mode", missing)
        self.assertNotIn("phase_wish_mode", missing)

    def test_v2_error_status_and_codes_follow_the_api(self):
        from custom_components.goecharger.api import GoeChargerV2

        expected_errors = {
            0: "OK",
            1: "FI_AC",
            2: "FI_DC",
            3: "PHASE",
            4: "OVERVOLT",
            5: "OVERAMP",
            6: "DIODE",
            7: "PP_INVALID",
            8: "GND_INVALID",
            9: "CONTACTOR_STUCK",
            10: "CONTACTOR_MISS",
            11: "FI_UNKNOWN",
            12: "UNKNOWN",
            13: "OVERTEMP",
            14: "NO_COMM",
            15: "STATUS_LOCK_STUCK_OPEN",
            16: "STATUS_LOCK_STUCK_LOCKED",
            20: "RESERVED_20",
            21: "RESERVED_21",
            22: "RESERVED_22",
            23: "RESERVED_23",
            24: "RESERVED_24",
        }

        for code, expected in expected_errors.items():
            with self.subTest(code=code):
                status = GoeChargerV2(
                    "192.0.2.10",
                    open_url=lambda request, timeout, code=code: FakeResponse(
                        {"car": 5, "err": code, "fwv": "60.5"}
                    ),
                ).requestStatus()
                self.assertEqual(status["car_status"], "error")
                self.assertEqual(status["charger_err"], expected)

    def test_v2_error_codes_follow_firmware(self):
        from custom_components.goecharger.api import GoeChargerV2

        cases = (
            ("60.4", 13, "STATUS_LOCK_STUCK_LOCKED"),
            ("60.4", 16, "OVERTEMP"),
            ("60.4", 23, "RDC_SELF_TEST_FAILED"),
            ("60.5", 13, "OVERTEMP"),
            ("60.5", 16, "STATUS_LOCK_STUCK_LOCKED"),
            ("60.5", 23, "RESERVED_23"),
            (None, 13, "UNKNOWN"),
        )

        for firmware, code, expected in cases:
            with self.subTest(firmware=firmware, code=code):
                payload = {"car": 5, "err": code}
                if firmware is not None:
                    payload["fwv"] = firmware
                status = GoeChargerV2(
                    "192.0.2.10",
                    open_url=lambda request, timeout, payload=payload: FakeResponse(payload),
                ).requestStatus()
                self.assertEqual(status["charger_err"], expected)

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
        self.assertNotIn("pwm", V2_SELECTS)
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
