# GoAmpLocal Next Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement five independent, Home Assistant-native go-eCharger improvements on separate branches: Zeroconf discovery, binary sensors, correct sensor metadata, diagnostics export, and config-flow API autodetection.

**Architecture:** Each feature branch starts from `main` and lives in its own worktree under `.worktrees/`. Branches must stay independently reviewable and must not depend on another feature branch. Do not bump `manifest.json` versions by hand; release automation handles versioning.

**Tech Stack:** Python stdlib, Home Assistant custom integration APIs, existing local `unittest` test stubs, git worktrees, no new runtime dependencies.

---

## Repository Setup

Current checkout has an unrelated local `README.md` modification. Do not stage, edit, or revert it.

Worktree branches:

- `codex/zeroconf-discovery` at `.worktrees/zeroconf-discovery`
- `codex/binary-sensors` at `.worktrees/binary-sensors`
- `codex/sensor-device-classes` at `.worktrees/sensor-device-classes`
- `codex/diagnostics-export` at `.worktrees/diagnostics-export`
- `codex/config-flow-autodetect` at `.worktrees/config-flow-autodetect`

Before creating worktrees:

```bash
git check-ignore -q .worktrees || printf '.worktrees/\n' >> .gitignore
python3 -m unittest discover -s tests -v
git add .gitignore docs/superpowers/plans/2026-06-25-goecharger-next-features.md
git commit -m "docs: plan next goecharger features"
```

Expected baseline: all current tests pass. If baseline fails, stop and report the exact failure.

---

## Task 1: Zeroconf Discovery

**Branch:** `codex/zeroconf-discovery`

**Files:**

- Modify: `custom_components/goecharger/manifest.json`
- Modify: `custom_components/goecharger/config_flow.py`
- Modify: `custom_components/goecharger/translations/en.json`
- Modify: `custom_components/goecharger/translations/de.json`
- Test: `tests/test_zeroconf.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_zeroconf.py`:

```python
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ZeroconfTests(unittest.TestCase):
    def test_manifest_declares_goe_http_zeroconf(self):
        manifest = json.loads(
            (ROOT / "custom_components" / "goecharger" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            {"type": "_http._tcp.local.", "name": "go-eCharger*"},
            manifest["zeroconf"],
        )

    def test_config_flow_has_zeroconf_step(self):
        source = (
            ROOT / "custom_components" / "goecharger" / "config_flow.py"
        ).read_text(encoding="utf-8")

        self.assertIn("async_step_zeroconf", source)
        self.assertIn("discovery_info.host", source)
        self.assertIn("self.context[\"title_placeholders\"]", source)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_zeroconf -v
```

Expected: FAIL because `zeroconf` and `async_step_zeroconf` do not exist.

- [ ] **Step 3: Add minimal Zeroconf support**

In `custom_components/goecharger/manifest.json`, add:

```json
"zeroconf": [
  {
    "type": "_http._tcp.local.",
    "name": "go-eCharger*"
  }
],
```

In `custom_components/goecharger/config_flow.py`, add an `async_step_zeroconf` method to `ConfigFlowHandler`:

```python
    async def async_step_zeroconf(self, discovery_info):
        host = discovery_info.host
        name = getattr(discovery_info, "name", None) or host
        self.context["title_placeholders"] = {"name": name}
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return await self.async_step_user(
            {
                CONF_HOST: host,
                CONF_NAME: name.replace("._http._tcp.local.", "").strip("."),
                CONF_SCAN_INTERVAL: 20,
                CONF_CORRECTION_FACTOR: "1.0",
                CONF_API_VERSION: DEFAULT_API_VERSION,
            }
        )
```

If the Home Assistant config-flow stub needs no runtime import in this test, keep the test source-based.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_zeroconf -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/goecharger/manifest.json custom_components/goecharger/config_flow.py custom_components/goecharger/translations/en.json custom_components/goecharger/translations/de.json tests/test_zeroconf.py
git commit -m "feat: add go-e zeroconf discovery"
```

---

## Task 2: Binary Sensors

**Branch:** `codex/binary-sensors`

**Files:**

- Create: `custom_components/goecharger/binary_sensor.py`
- Modify: `custom_components/goecharger/__init__.py`
- Test: `tests/test_binary_sensor.py`

Use reliable state only. Do not add `cable_locked` unless a real lock-state API key is mapped; current `cable_lock_mode` is configuration, not lock state.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_binary_sensor.py`:

```python
import importlib
import sys
import types
import unittest


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.core.valid_entity_id = lambda value: False
homeassistant.config_entries = _install_module("homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))
homeassistant.config_entries.ConfigEntry = object
homeassistant.components = _install_module("homeassistant.components", types.ModuleType("homeassistant.components"))
homeassistant.components.binary_sensor = _install_module("homeassistant.components.binary_sensor", types.ModuleType("homeassistant.components.binary_sensor"))
homeassistant.components.binary_sensor.BinarySensorDeviceClass = types.SimpleNamespace(CONNECTIVITY="connectivity", PROBLEM="problem")
homeassistant.components.binary_sensor.BinarySensorEntity = object
homeassistant.helpers = _install_module("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
homeassistant.helpers.update_coordinator = _install_module("homeassistant.helpers.update_coordinator", types.ModuleType("homeassistant.helpers.update_coordinator"))


class CoordinatorEntity:
    def __init__(self, coordinator, *args, **kwargs):
        self.coordinator = coordinator

    @property
    def available(self):
        return getattr(self.coordinator, "last_update_success", True)


homeassistant.helpers.update_coordinator.CoordinatorEntity = CoordinatorEntity

goecharger_binary_sensor = importlib.import_module("custom_components.goecharger.binary_sensor")


class BinarySensorTests(unittest.TestCase):
    def sensor(self, attribute, data):
        return goecharger_binary_sensor.GoeChargerBinarySensor(
            types.SimpleNamespace(data={"charger1": data}),
            "charger1",
            attribute,
            goecharger_binary_sensor.BINARY_SENSOR_DESCRIPTIONS[attribute],
        )

    def test_car_connected_from_car_status(self):
        sensor = self.sensor("car_connected", {"car_status": "Waiting for vehicle"})

        self.assertTrue(sensor.is_on)

    def test_charging_from_car_status(self):
        sensor = self.sensor("charging", {"car_status": "charging"})

        self.assertTrue(sensor.is_on)

    def test_error_present_ignores_ok(self):
        sensor = self.sensor("error_present", {"charger_err": "OK"})

        self.assertFalse(sensor.is_on)

    def test_wifi_connected_from_wifi_status(self):
        sensor = self.sensor("wifi_connected", {"wifi": "connected"})

        self.assertTrue(sensor.is_on)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_binary_sensor -v
```

Expected: FAIL because `binary_sensor.py` does not exist.

- [ ] **Step 3: Implement minimal binary sensors**

Create `custom_components/goecharger/binary_sensor.py` with:

```python
"""Binary sensor platform for go-eCharger."""

from homeassistant import config_entries, core
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CHARGERS, CONF_NAME, DOMAIN, charger_entity_id


CONNECTED_STATES = {
    "charging",
    "Waiting for vehicle",
    "charging finished, vehicle still connected",
}

BINARY_SENSOR_DESCRIPTIONS = {
    "car_connected": {"name": "Car connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY},
    "charging": {"name": "Charging", "device_class": None},
    "error_present": {"name": "Error present", "device_class": BinarySensorDeviceClass.PROBLEM},
    "wifi_connected": {"name": "Wi-Fi connected", "device_class": BinarySensorDeviceClass.CONNECTIVITY},
}


def _create_binary_sensors_for_charger(hass, charger_name):
    return [
        GoeChargerBinarySensor(
            hass.data[DOMAIN]["coordinator"],
            charger_name,
            attribute,
            description,
        )
        for attribute, description in BINARY_SENSOR_DESCRIPTIONS.items()
    ]


async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry, async_add_entities):
    config = config_entry.as_dict()["data"]
    async_add_entities(_create_binary_sensors_for_charger(hass, config[CONF_NAME]))


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    if discovery_info is None:
        return
    entities = []
    for charger in discovery_info[CONF_CHARGERS]:
        entities.extend(_create_binary_sensors_for_charger(hass, charger[0][CONF_NAME]))
    async_add_entities(entities)


class GoeChargerBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, charger_name, attribute, description):
        super().__init__(coordinator)
        self._chargername = charger_name
        self._attribute = attribute
        self._attr_name = description["name"]
        self._attr_device_class = description["device_class"]
        self.entity_id = charger_entity_id("binary_sensor", charger_name, attribute)
        self._attr_unique_id = f"{charger_name}_{attribute}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._chargername)},
            "name": self._chargername,
            "manufacturer": "go-e",
            "model": "HOME",
        }

    @property
    def available(self):
        return super().available and bool((self.coordinator.data or {}).get(self._chargername))

    @property
    def is_on(self):
        data = (self.coordinator.data or {}).get(self._chargername, {})
        if self._attribute == "car_connected":
            return data.get("car_status") in CONNECTED_STATES
        if self._attribute == "charging":
            return data.get("car_status") == "charging"
        if self._attribute == "error_present":
            return data.get("charger_err") not in (None, "OK")
        if self._attribute == "wifi_connected":
            return data.get("wifi") == "connected"
        return None
```

In `custom_components/goecharger/__init__.py`, change:

```python
PLATFORMS = ["sensor", "switch", "number", "select"]
```

to:

```python
PLATFORMS = ["sensor", "switch", "number", "select", "binary_sensor"]
```

and change the YAML setup platform loop to iterate over `PLATFORMS`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_binary_sensor -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/goecharger/__init__.py custom_components/goecharger/binary_sensor.py tests/test_binary_sensor.py
git commit -m "feat: add charger binary sensors"
```

---

## Task 3: Sensor Device Classes and Units

**Branch:** `codex/sensor-device-classes`

**Files:**

- Modify: `custom_components/goecharger/sensor.py`
- Test: `tests/test_sensor_metadata.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sensor_metadata.py`:

```python
import importlib
import sys
import types
import unittest


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.const = _install_module("homeassistant.const", types.ModuleType("homeassistant.const"))
homeassistant.const.CONF_HOST = "host"
homeassistant.const.CONF_SCAN_INTERVAL = "scan_interval"
homeassistant.const.UnitOfEnergy = types.SimpleNamespace(KILO_WATT_HOUR="kWh")
homeassistant.const.UnitOfPower = types.SimpleNamespace(KILO_WATT="kW", WATT="W")
homeassistant.const.UnitOfElectricCurrent = types.SimpleNamespace(AMPERE="A")
homeassistant.const.UnitOfElectricPotential = types.SimpleNamespace(VOLT="V")
homeassistant.const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="C")
homeassistant.core = _install_module("homeassistant.core", types.ModuleType("homeassistant.core"))
homeassistant.core.HomeAssistant = object
homeassistant.config_entries = _install_module("homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))
homeassistant.config_entries.ConfigEntry = object
homeassistant.components = _install_module("homeassistant.components", types.ModuleType("homeassistant.components"))
homeassistant.components.sensor = _install_module("homeassistant.components.sensor", types.ModuleType("homeassistant.components.sensor"))
homeassistant.components.sensor.SensorDeviceClass = types.SimpleNamespace(ENERGY="energy", POWER="power", CURRENT="current", VOLTAGE="voltage", TEMPERATURE="temperature")
homeassistant.components.sensor.SensorEntity = object
homeassistant.components.sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement", TOTAL_INCREASING="total_increasing")
homeassistant.helpers = _install_module("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
homeassistant.helpers.update_coordinator = _install_module("homeassistant.helpers.update_coordinator", types.ModuleType("homeassistant.helpers.update_coordinator"))
homeassistant.helpers.update_coordinator.CoordinatorEntity = object

goecharger_sensor = importlib.import_module("custom_components.goecharger.sensor")


class SensorMetadataTests(unittest.TestCase):
    def test_power_sensor_has_power_metadata(self):
        self.assertEqual(goecharger_sensor._sensorUnits["p_all"]["unit"], "kW")
        self.assertEqual(goecharger_sensor._sensorDeviceClass["p_all"], "power")
        self.assertEqual(goecharger_sensor._sensorStateClass["p_all"], "measurement")

    def test_voltage_sensor_has_voltage_metadata(self):
        self.assertEqual(goecharger_sensor._sensorUnits["u_l1"]["unit"], "V")
        self.assertEqual(goecharger_sensor._sensorDeviceClass["u_l1"], "voltage")
        self.assertEqual(goecharger_sensor._sensorStateClass["u_l1"], "measurement")

    def test_current_sensor_has_current_metadata(self):
        self.assertEqual(goecharger_sensor._sensorUnits["i_l1"]["unit"], "A")
        self.assertEqual(goecharger_sensor._sensorDeviceClass["i_l1"], "current")
        self.assertEqual(goecharger_sensor._sensorStateClass["i_l1"], "measurement")
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_sensor_metadata -v
```

Expected: FAIL because power/current/voltage metadata is incomplete.

- [ ] **Step 3: Add minimal correct metadata**

In `sensor.py`, import proper HA unit constants and stop assigning `UnitOfEnergy.KILO_WATT`.

Add metadata maps for:

- Power sensors: `p_l1`, `p_l2`, `p_l3`, `p_n`, `p_all`, `p_grid`, `p_pv`, `p_akku`
- Voltage sensors: `u_l1`, `u_l2`, `u_l3`, `u_n`
- Current sensors: `i_l1`, `i_l2`, `i_l3`, `charger_max_current`, `charger_absolute_max_current`, `cable_max_current`, `allowed_current`
- Temperature sensors: `charger_temp`, `charger_temp0`, `charger_temp1`, `charger_temp2`, `charger_temp3`

Keep energy sensors as `TOTAL_INCREASING`. Use `MEASUREMENT` for power/current/voltage/temperature.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_sensor_metadata -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/goecharger/sensor.py tests/test_sensor_metadata.py
git commit -m "feat: add sensor device classes"
```

---

## Task 4: Diagnostics Export

**Branch:** `codex/diagnostics-export`

**Files:**

- Create: `custom_components/goecharger/diagnostics.py`
- Modify: `custom_components/goecharger/manifest.json`
- Test: `tests/test_diagnostics.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_diagnostics.py`:

```python
import asyncio
import importlib
import sys
import types
import unittest


def _install_module(name, module):
    sys.modules.setdefault(name, module)
    return sys.modules[name]


homeassistant = _install_module("homeassistant", types.ModuleType("homeassistant"))
homeassistant.components = _install_module("homeassistant.components", types.ModuleType("homeassistant.components"))
homeassistant.components.diagnostics = _install_module("homeassistant.components.diagnostics", types.ModuleType("homeassistant.components.diagnostics"))
homeassistant.components.diagnostics.async_redact_data = lambda data, keys: {
    key: "**REDACTED**" if key in keys else value for key, value in data.items()
}

goecharger_diagnostics = importlib.import_module("custom_components.goecharger.diagnostics")


class FakeEntry:
    data = {"host": "192.0.2.10", "name": "charger1", "api_version": "v2"}
    options = {"scan_interval": 20}


class DiagnosticsTests(unittest.TestCase):
    def test_diagnostics_redacts_host_and_summarizes_status(self):
        hass = types.SimpleNamespace(
            data={
                "goecharger": {
                    "coordinator": types.SimpleNamespace(
                        data={
                            "charger1": {
                                "serial_number": "123456",
                                "firmware": "060.0",
                                "wifi_ssid": "Private WiFi",
                                "charger_err": "OK",
                            }
                        }
                    )
                }
            }
        )

        result = asyncio.run(
            goecharger_diagnostics.async_get_config_entry_diagnostics(hass, FakeEntry())
        )

        self.assertEqual(result["config_entry"]["host"], "**REDACTED**")
        self.assertEqual(result["charger"]["serial_number"], "123456")
        self.assertNotIn("wifi_ssid", result["charger"])
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_diagnostics -v
```

Expected: FAIL because `diagnostics.py` does not exist.

- [ ] **Step 3: Implement diagnostics**

Create `custom_components/goecharger/diagnostics.py`:

```python
"""Diagnostics support for GoAmpLocal."""

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_NAME, DOMAIN


TO_REDACT = {"host"}
STATUS_DENYLIST = {"wifi_ssid", "unlocked_by_card"}


async def async_get_config_entry_diagnostics(hass, config_entry):
    data = dict(config_entry.data)
    charger_name = data.get(CONF_NAME)
    coordinator_data = (hass.data.get(DOMAIN, {}).get("coordinator").data or {})
    charger_data = dict(coordinator_data.get(charger_name, {}))
    for key in STATUS_DENYLIST:
        charger_data.pop(key, None)
    return {
        "config_entry": async_redact_data(data, TO_REDACT),
        "options": dict(config_entry.options),
        "charger": charger_data,
        "available_status_keys": sorted(charger_data),
    }
```

In `manifest.json`, add:

```json
"integration_type": "device",
```

Do not add a dependency.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_diagnostics -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/goecharger/diagnostics.py custom_components/goecharger/manifest.json tests/test_diagnostics.py
git commit -m "feat: add diagnostics export"
```

---

## Task 5: Config Flow API Autodetection and Validation

**Branch:** `codex/config-flow-autodetect`

**Files:**

- Modify: `custom_components/goecharger/api.py`
- Modify: `custom_components/goecharger/config_flow.py`
- Modify: `custom_components/goecharger/const.py`
- Modify: `custom_components/goecharger/translations/en.json`
- Modify: `custom_components/goecharger/translations/de.json`
- Test: `tests/test_config_flow_autodetect.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config_flow_autodetect.py`:

```python
import json
import unittest


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ConfigFlowAutodetectTests(unittest.TestCase):
    def test_detect_api_version_returns_v2_when_status_endpoint_answers(self):
        from custom_components.goecharger.api import detect_api_version
        from custom_components.goecharger.const import API_VERSION_V2

        version = detect_api_version(
            "192.0.2.10",
            open_url=lambda request, timeout: FakeResponse({"fwv": "060.0"}),
        )

        self.assertEqual(version, API_VERSION_V2)

    def test_detect_api_version_falls_back_to_v1(self):
        from custom_components.goecharger.api import detect_api_version
        from custom_components.goecharger.const import API_VERSION_V1

        def broken_open_url(request, timeout):
            raise OSError("no v2")

        self.assertEqual(detect_api_version("192.0.2.10", open_url=broken_open_url), API_VERSION_V1)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest tests.test_config_flow_autodetect -v
```

Expected: FAIL because `detect_api_version` does not exist.

- [ ] **Step 3: Add autodetection helper**

In `api.py`, add:

```python
def detect_api_version(host, open_url=urlopen):
    try:
        GoeChargerV2(host, open_url=open_url)._get_json("/api/status", {"filter": "fwv"})
    except Exception:
        return API_VERSION_V1
    return API_VERSION_V2
```

In `const.py`, add:

```python
API_VERSION_AUTO = "auto"
API_VERSIONS = {
    API_VERSION_AUTO: "Auto-detect",
    API_VERSION_V1: "v1",
    API_VERSION_V2: "v2 (recommended)",
}
```

In `config_flow.py`, make the form default `api_version` to `API_VERSION_AUTO`; when submitted with `auto`, call `detect_api_version(host)` in the executor and store the detected concrete value (`v1` or `v2`) in the created entry. If the selected or detected version cannot fetch charger status, return `errors["base"] = "cannot_connect"` instead of creating the entry.

Add translation abort/error text:

```json
"error": {
  "cannot_connect": "Cannot connect to the charger"
}
```

German:

```json
"error": {
  "cannot_connect": "Keine Verbindung zum Charger möglich"
}
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_config_flow_autodetect -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/goecharger/api.py custom_components/goecharger/config_flow.py custom_components/goecharger/const.py custom_components/goecharger/translations/en.json custom_components/goecharger/translations/de.json tests/test_config_flow_autodetect.py
git commit -m "feat: autodetect charger api version"
```

---

## Review and Verification

For each branch:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components/goecharger tests
git diff --check
```

Before reporting a branch ready, inspect:

```bash
git status --short --branch
git log --oneline -1
```

Expected: only that branch's feature files changed, tests pass, one feature commit exists.

## Integration Notes

These branches intentionally overlap in `manifest.json`, `config_flow.py`, and `__init__.py`. Keep them separate as requested. A later integration branch should merge them one by one and resolve small conflicts there.

Skipped: cloud control, MQTT, OCPP, Modbus, and full charging optimizer. Add those only if this integration intentionally stops being a small local Home Assistant integration.
