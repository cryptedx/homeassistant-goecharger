import asyncio
import importlib
import sys
import types
import unittest
from pathlib import Path


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.components = _install_module(
    "homeassistant.components", types.ModuleType("homeassistant.components")
)
homeassistant.components.diagnostics = _install_module(
    "homeassistant.components.diagnostics",
    types.ModuleType("homeassistant.components.diagnostics"),
)
homeassistant.components.diagnostics.async_redact_data = (
    lambda data, keys: {key: ("**REDACTED**" if key in keys else value) for key, value in data.items()}
)

ROOT = Path(__file__).parents[1]
PACKAGE = "goecharger_diagnostics_test"
package = _install_module(PACKAGE, types.ModuleType(PACKAGE))
package.__path__ = [str(ROOT / "custom_components" / "goecharger")]

goecharger_const = importlib.import_module(f"{PACKAGE}.const")
goecharger_diagnostics = importlib.import_module(f"{PACKAGE}.diagnostics")


class DiagnosticsTests(unittest.TestCase):
    def test_diagnostics_redacts_host_and_omits_sensitive_status(self):
        config_entry = types.SimpleNamespace(
            data={goecharger_const.CONF_NAME: "garage", "host": "192.0.2.10"},
            options={"scan_interval": 20},
        )
        hass = types.SimpleNamespace(
            data={
                goecharger_const.DOMAIN: {
                    "coordinator": types.SimpleNamespace(
                        data={
                            "garage": {
                                "serial_number": "abc123",
                                "firmware": "060.0",
                                "charger_err": "OK",
                                "wifi_ssid": "private-wifi",
                                "unlocked_by_card": "secret-card",
                            }
                        }
                    )
                }
            }
        )

        diagnostics = asyncio.run(
            goecharger_diagnostics.async_get_config_entry_diagnostics(hass, config_entry)
        )

        self.assertEqual(diagnostics["config_entry"]["host"], "**REDACTED**")
        self.assertEqual(diagnostics["options"], {"scan_interval": 20})
        self.assertEqual(
            diagnostics["charger_status"],
            {"charger_err": "OK", "firmware": "060.0", "serial_number": "abc123"},
        )
        self.assertEqual(
            diagnostics["available_status_keys"],
            ["charger_err", "firmware", "serial_number", "unlocked_by_card", "wifi_ssid"],
        )


if __name__ == "__main__":
    unittest.main()
