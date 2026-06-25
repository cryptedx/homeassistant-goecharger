import asyncio
import importlib
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _install_homeassistant_stubs():
    voluptuous = sys.modules.setdefault("voluptuous", types.ModuleType("voluptuous"))
    voluptuous.Schema = getattr(voluptuous, "Schema", lambda *args, **kwargs: lambda value: value)
    voluptuous.Optional = getattr(voluptuous, "Optional", lambda key, **kwargs: key)
    voluptuous.Required = getattr(voluptuous, "Required", lambda key, **kwargs: key)
    voluptuous.In = getattr(voluptuous, "In", lambda *args, **kwargs: lambda value: value)

    homeassistant = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    config_entries = sys.modules.setdefault(
        "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
    )
    const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))

    const.CONF_HOST = "host"
    const.CONF_SCAN_INTERVAL = "scan_interval"
    core.callback = lambda func: func

    class AbortFlow(Exception):
        def __init__(self, reason, updates=None):
            super().__init__(reason)
            self.reason = reason
            self.updates = updates

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        def __init__(self):
            self.context = {}
            self.unique_id = None
            self._configured_unique_ids = set()
            self.discovery_without_unique_id_handled = False
            self.discovery_without_unique_id_abort_reason = None

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self, updates=None):
            if self.unique_id in self._configured_unique_ids:
                raise AbortFlow("already_configured", updates)

        async def _async_handle_discovery_without_unique_id(self):
            await asyncio.sleep(0)
            self.discovery_without_unique_id_handled = True
            if self.discovery_without_unique_id_abort_reason is not None:
                raise AbortFlow(self.discovery_without_unique_id_abort_reason)

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, step_id, data_schema=None):
            return {"type": "form", "step_id": step_id, "data_schema": data_schema}

    config_entries.AbortFlow = AbortFlow
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = object
    homeassistant.config_entries = config_entries
    homeassistant.const = const
    homeassistant.core = core

    if "custom_components.goecharger" not in sys.modules:
        package = types.ModuleType("custom_components.goecharger")
        package.__path__ = [str(ROOT / "custom_components" / "goecharger")]
        sys.modules["custom_components.goecharger"] = package


class ZeroconfTests(unittest.TestCase):
    def manifest(self):
        return json.loads(
            (ROOT / "custom_components" / "goecharger" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def config_flow_source(self):
        return (ROOT / "custom_components" / "goecharger" / "config_flow.py").read_text(
            encoding="utf-8"
        )

    def config_flow_module(self):
        _install_homeassistant_stubs()
        sys.modules.pop("custom_components.goecharger.config_flow", None)
        return importlib.import_module("custom_components.goecharger.config_flow")

    def test_manifest_advertises_go_echarger_http_zeroconf(self):
        self.assertEqual(
            self.manifest().get("zeroconf"),
            [{"type": "_http._tcp.local.", "name": "go-eCharger*"}],
        )

    def test_config_flow_contains_zeroconf_entrypoint(self):
        source = self.config_flow_source()

        self.assertIn("async_step_zeroconf", source)
        self.assertIn("discovery_info.host", source)
        self.assertIn("title_placeholders", source)

    def test_zeroconf_shows_confirm_form(self):
        config_flow = self.config_flow_module()
        self.assertTrue(
            hasattr(config_flow.ConfigFlowHandler, "async_step_zeroconf"),
            "ConfigFlowHandler.async_step_zeroconf is missing",
        )

        flow = config_flow.ConfigFlowHandler()
        discovery_info = types.SimpleNamespace(
            host="192.0.2.10", name="go-eCharger 123._http._tcp.local."
        )

        result = asyncio.run(flow.async_step_zeroconf(discovery_info))

        self.assertIsNone(flow.unique_id)
        self.assertTrue(flow.discovery_without_unique_id_handled)
        self.assertEqual(
            flow.context["title_placeholders"],
            {"name": "go-eCharger 123._http._tcp.local."},
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["step_id"], "confirm")

    def test_zeroconf_awaits_discovery_without_unique_id_abort(self):
        config_flow = self.config_flow_module()
        flow = config_flow.ConfigFlowHandler()
        flow.discovery_without_unique_id_abort_reason = "already_in_progress"
        discovery_info = types.SimpleNamespace(
            host="192.0.2.10", name="go-eCharger 123._http._tcp.local."
        )

        with self.assertRaises(config_flow.config_entries.AbortFlow) as raised:
            asyncio.run(flow.async_step_zeroconf(discovery_info))

        self.assertTrue(flow.discovery_without_unique_id_handled)
        self.assertEqual(raised.exception.reason, "already_in_progress")

    def test_zeroconf_confirm_creates_default_entry(self):
        config_flow = self.config_flow_module()
        flow = config_flow.ConfigFlowHandler()
        discovery_info = types.SimpleNamespace(
            host="192.0.2.10", name="go-eCharger 123._http._tcp.local."
        )

        asyncio.run(flow.async_step_zeroconf(discovery_info))
        result = asyncio.run(flow.async_step_confirm({}))

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "go-eCharger 123")
        self.assertEqual(
            result["data"],
            {
                "host": "192.0.2.10",
                "name": "go-eCharger 123",
                "scan_interval": 20,
                "correction_factor": "1.0",
                "api_version": config_flow.DEFAULT_API_VERSION,
            },
        )


if __name__ == "__main__":
    unittest.main()
