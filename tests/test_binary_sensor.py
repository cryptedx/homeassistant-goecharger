import importlib
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.components = _install_module(
    "homeassistant.components", types.ModuleType("homeassistant.components")
)
homeassistant.components.binary_sensor = _install_module(
    "homeassistant.components.binary_sensor", types.ModuleType("homeassistant.components.binary_sensor")
)
homeassistant.components.binary_sensor.BinarySensorEntity = object
homeassistant.config_entries = _install_module(
    "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
)
homeassistant.config_entries.ConfigEntry = object
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.helpers = _install_module("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
homeassistant.helpers.update_coordinator = _install_module(
    "homeassistant.helpers.update_coordinator", types.ModuleType("homeassistant.helpers.update_coordinator")
)


class CoordinatorEntity:
    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator

    @property
    def available(self):
        return getattr(self.coordinator, "last_update_success", True)


homeassistant.helpers.update_coordinator.CoordinatorEntity = CoordinatorEntity

custom_components = _install_module("custom_components", types.ModuleType("custom_components"))
custom_components.__path__ = [str(ROOT / "custom_components")]
goecharger_package = _install_module(
    "custom_components.goecharger", types.ModuleType("custom_components.goecharger")
)
goecharger_package.__path__ = [str(ROOT / "custom_components" / "goecharger")]
goecharger_binary_sensor = importlib.import_module("custom_components.goecharger.binary_sensor")
sys.modules.pop("custom_components.goecharger", None)
sys.modules.pop("custom_components", None)


class BinarySensorTests(unittest.TestCase):
    def _sensor(self, attribute, data):
        return goecharger_binary_sensor.GoeChargerBinarySensor(
            types.SimpleNamespace(data={"charger1": data}),
            "binary_sensor.test",
            "charger1",
            attribute,
        )

    def test_car_connected_is_on_for_connected_car_statuses(self):
        for status in (
            "charging",
            "Waiting for vehicle",
            "charging finished, vehicle still connected",
        ):
            with self.subTest(status=status):
                self.assertTrue(self._sensor("car_connected", {"car_status": status}).is_on)

        self.assertFalse(self._sensor("car_connected", {"car_status": "Charger ready, no vehicle"}).is_on)

    def test_charging_is_on_only_while_charging(self):
        self.assertTrue(self._sensor("charging", {"car_status": "charging"}).is_on)
        self.assertFalse(self._sensor("charging", {"car_status": "Waiting for vehicle"}).is_on)

    def test_error_present_is_on_when_error_is_not_ok(self):
        self.assertTrue(self._sensor("error_present", {"charger_err": "RCCB"}).is_on)
        self.assertFalse(self._sensor("error_present", {"charger_err": "OK"}).is_on)
        self.assertFalse(self._sensor("error_present", {}).is_on)

    def test_wifi_connected_is_on_when_wifi_is_connected(self):
        self.assertTrue(self._sensor("wifi_connected", {"wifi": "connected"}).is_on)
        self.assertFalse(self._sensor("wifi_connected", {"wifi": "not connected"}).is_on)


if __name__ == "__main__":
    unittest.main()
