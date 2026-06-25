import json
import asyncio
import importlib
import sys
import types
import unittest


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


voluptuous = _install_module("voluptuous", types.ModuleType("voluptuous"))
voluptuous.ALLOW_EXTRA = object()


class FakeMarker:
    def __init__(self, key, **kwargs):
        self.schema = key
        self.default = kwargs.get("default")


class FakeSchema:
    def __init__(self, schema, **kwargs):
        self.schema = schema

    def __call__(self, value):
        return value


class FakeIn:
    def __init__(self, container):
        self.container = container

    def __call__(self, value):
        return value


voluptuous.Schema = FakeSchema
voluptuous.All = lambda *args, **kwargs: lambda value: value
voluptuous.Optional = lambda key, **kwargs: FakeMarker(key, **kwargs)
voluptuous.Required = lambda key, **kwargs: FakeMarker(key, **kwargs)
voluptuous.Clamp = lambda *args, **kwargs: lambda value: value
voluptuous.In = lambda container: FakeIn(container)

homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.core.callback = lambda func: func
homeassistant.core.valid_entity_id = lambda value: False
homeassistant.config_entries = _install_module(
    "homeassistant.config_entries", types.ModuleType("homeassistant.config_entries")
)


class FakeFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}


homeassistant.config_entries.ConfigFlow = FakeFlow
homeassistant.config_entries.OptionsFlow = FakeFlow
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

goecharger = _install_module("goecharger", types.ModuleType("goecharger"))
goecharger.GoeCharger = object


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeHass:
    async def async_add_executor_job(self, job, *args):
        return job(*args)


class FakeCharger:
    def requestStatus(self):
        return {"car_status": "idle"}


class BrokenCharger:
    def requestStatus(self):
        raise TimeoutError("offline")


def _default_for(schema, key):
    for marker in schema.schema:
        if marker.schema == key:
            return marker.default
    raise AssertionError(f"{key} not found in schema")


def _validator_for(schema, key):
    for marker, validator in schema.schema.items():
        if marker.schema == key:
            return validator
    raise AssertionError(f"{key} not found in schema")


def _load_config_flow():
    voluptuous.Schema = FakeSchema
    voluptuous.Optional = lambda key, **kwargs: FakeMarker(key, **kwargs)
    voluptuous.Required = lambda key, **kwargs: FakeMarker(key, **kwargs)
    voluptuous.In = lambda container: FakeIn(container)
    homeassistant.core.callback = lambda func: func
    homeassistant.config_entries.ConfigFlow = FakeFlow
    homeassistant.config_entries.OptionsFlow = FakeFlow
    sys.modules.pop("custom_components.goecharger.config_flow", None)
    return importlib.import_module("custom_components.goecharger.config_flow")


class ConfigFlowAutodetectTests(unittest.TestCase):
    def test_detect_api_version_returns_v2_for_status_response(self):
        from custom_components.goecharger.api import detect_api_version
        from custom_components.goecharger.const import API_VERSION_V2

        urls = []

        def open_url(request, timeout):
            urls.append(request.full_url)
            return FakeResponse({"fwv": "060.0"})

        self.assertEqual(detect_api_version("192.0.2.10", open_url=open_url), API_VERSION_V2)
        self.assertEqual(urls, ["http://192.0.2.10/api/status?filter=fwv"])

    def test_detect_api_version_returns_v1_on_exception(self):
        from custom_components.goecharger.api import detect_api_version
        from custom_components.goecharger.const import API_VERSION_V1

        def open_url(request, timeout):
            raise TimeoutError("offline")

        self.assertEqual(detect_api_version("192.0.2.10", open_url=open_url), API_VERSION_V1)

    def test_user_form_defaults_to_auto(self):
        from custom_components.goecharger.const import (
            API_VERSION_AUTO,
            API_VERSION_V1,
            API_VERSION_V2,
            CONF_API_VERSION,
        )

        config_flow = _load_config_flow()

        result = asyncio.run(config_flow.ConfigFlowHandler().async_step_user())

        self.assertEqual(result["type"], "form")
        self.assertEqual(_default_for(result["data_schema"], CONF_API_VERSION), API_VERSION_AUTO)
        self.assertEqual(
            set(_validator_for(result["data_schema"], CONF_API_VERSION).container),
            {API_VERSION_AUTO, API_VERSION_V1, API_VERSION_V2},
        )

    def test_options_form_includes_auto(self):
        from custom_components.goecharger.const import (
            API_VERSION_AUTO,
            API_VERSION_V1,
            API_VERSION_V2,
            CONF_API_VERSION,
        )
        from homeassistant.const import CONF_HOST

        config_flow = _load_config_flow()
        entry = types.SimpleNamespace(data={CONF_HOST: "192.0.2.10"}, options={})

        result = asyncio.run(config_flow.OptionsFlowHandler(entry).async_step_init())

        self.assertEqual(result["type"], "form")
        self.assertEqual(
            set(_validator_for(result["data_schema"], CONF_API_VERSION).container),
            {API_VERSION_AUTO, API_VERSION_V1, API_VERSION_V2},
        )

    def test_user_submit_autodetects_validates_and_stores_concrete_version(self):
        from custom_components.goecharger.const import (
            API_VERSION_AUTO,
            API_VERSION_V2,
            CONF_API_VERSION,
            CONF_CORRECTION_FACTOR,
            CONF_NAME,
        )
        from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL

        config_flow = _load_config_flow()
        calls = []

        def detect_api_version(host):
            calls.append(("detect", host))
            return API_VERSION_V2

        def create_charger(host, api_version):
            calls.append(("create", host, api_version))
            return FakeCharger()

        flow = config_flow.ConfigFlowHandler()
        flow.hass = FakeHass()
        user_input = {
            CONF_HOST: "192.0.2.10",
            CONF_NAME: "charger",
            CONF_SCAN_INTERVAL: 20,
            CONF_CORRECTION_FACTOR: "1.0",
            CONF_API_VERSION: API_VERSION_AUTO,
        }

        original_detect = config_flow.detect_api_version
        original_create = config_flow.create_charger
        try:
            config_flow.detect_api_version = detect_api_version
            config_flow.create_charger = create_charger
            result = asyncio.run(flow.async_step_user(user_input))
        finally:
            config_flow.detect_api_version = original_detect
            config_flow.create_charger = original_create

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"][CONF_API_VERSION], API_VERSION_V2)
        self.assertEqual(calls, [("detect", "192.0.2.10"), ("create", "192.0.2.10", API_VERSION_V2)])

    def test_user_submit_shows_cannot_connect_on_validation_failure(self):
        from custom_components.goecharger.const import (
            API_VERSION_V2,
            CONF_API_VERSION,
            CONF_CORRECTION_FACTOR,
            CONF_NAME,
        )
        from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL

        config_flow = _load_config_flow()
        flow = config_flow.ConfigFlowHandler()
        flow.hass = FakeHass()
        user_input = {
            CONF_HOST: "192.0.2.10",
            CONF_NAME: "charger",
            CONF_SCAN_INTERVAL: 20,
            CONF_CORRECTION_FACTOR: "1.0",
            CONF_API_VERSION: API_VERSION_V2,
        }

        original_create = config_flow.create_charger
        try:
            config_flow.create_charger = lambda host, api_version: BrokenCharger()
            result = asyncio.run(flow.async_step_user(user_input))
        finally:
            config_flow.create_charger = original_create

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "cannot_connect"})

    def test_options_auto_detects_and_stores_concrete_version(self):
        from custom_components.goecharger.const import (
            API_VERSION_AUTO,
            API_VERSION_V2,
            CONF_API_VERSION,
            CONF_CORRECTION_FACTOR,
        )
        from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL

        config_flow = _load_config_flow()
        entry = types.SimpleNamespace(data={CONF_HOST: "192.0.2.10"}, options={})
        flow = config_flow.OptionsFlowHandler(entry)
        flow.hass = FakeHass()
        calls = []

        original_detect = config_flow.detect_api_version
        original_create = config_flow.create_charger
        try:
            config_flow.detect_api_version = lambda host: API_VERSION_V2
            config_flow.create_charger = lambda host, api_version: calls.append(
                ("create", host, api_version)
            ) or FakeCharger()
            result = asyncio.run(
                flow.async_step_init(
                    {
                        CONF_API_VERSION: API_VERSION_AUTO,
                        CONF_SCAN_INTERVAL: 20,
                        CONF_CORRECTION_FACTOR: "1.0",
                    }
                )
            )
        finally:
            config_flow.detect_api_version = original_detect
            config_flow.create_charger = original_create

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"][CONF_API_VERSION], API_VERSION_V2)
        self.assertEqual(calls, [("create", "192.0.2.10", API_VERSION_V2)])


if __name__ == "__main__":
    unittest.main()
