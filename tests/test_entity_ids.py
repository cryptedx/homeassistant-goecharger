import importlib.util
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "goecharger_const",
    Path(__file__).parents[1] / "custom_components" / "goecharger" / "const.py",
)
goecharger_const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(goecharger_const)


class EntityIdTests(unittest.TestCase):
    def test_charger_entity_id_slugifies_device_name(self):
        self.assertEqual(
            goecharger_const.charger_entity_id("sensor", "go-eCharger Outdoor V2", "p_all"),
            "sensor.goecharger_go_echarger_outdoor_v2_p_all",
        )


if __name__ == "__main__":
    unittest.main()
