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

goecharger = _install_module("goecharger", types.ModuleType("goecharger"))
goecharger.GoeCharger = object

sys.path.insert(0, str(ROOT))
goecharger_integration = importlib.import_module("custom_components.goecharger")


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

        self.assertEqual(data["broken"], {"car_status": "charging", "p_all": 2})
        self.assertEqual(data["working"], {"car_status": "idle", "p_all": 0})
        self.assertIn("Unable to fetch state for Charger broken", logs.output[0])


if __name__ == "__main__":
    unittest.main()
