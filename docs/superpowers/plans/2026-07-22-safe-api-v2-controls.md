# Safe API v2 Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent invalid charger-current writes, preserve phase status while adding a correctly separated phase control, and decode errors according to charger firmware.

**Architecture:** Keep all physical current limits in `GoeChargerV2`, which already serves every API v2 caller. Expose the cached limits through coordinator data so Home Assistant Number entities use the same boundaries. Keep `pwm` as read-only sensor data, add `psm` as a distinct select, and choose error tables from `fwv`.

**Tech Stack:** Python standard library, Home Assistant entity APIs, existing `unittest` test harness.

## Global Constraints

- Do not add dependencies or manually bump the manifest version.
- Keep code, tests, and repository documentation in English.
- Preserve all pre-existing working-tree changes.
- Do not deploy to Home Assistant or write to the physical charger.
- Keep genuine 32 A installations at 32 A.
- Run `python3 -m unittest discover -s tests -v` before the integration commit.

---

### Task 1: Enforce dynamic current limits

**Files:**
- Modify: `custom_components/goecharger/api.py`
- Modify: `custom_components/goecharger/number.py`
- Test: `tests/test_api.py`
- Test: `tests/test_state_fetcher.py`

**Interfaces:**
- Produces: coordinator keys `charger_hardware_max_current: int` and `charger_requested_current_limit: int`.
- Produces: `GoeChargerNumber.native_max_value` derived from those keys.
- Consumes: API v2 status keys `adi`, `ama`, and `var`.

- [ ] **Step 1: Add failing API limit tests**

Add tests that request status with `adi=True`, `ama=16`, `var=22` and assert both limits are 16. Add a second status with `adi=False`, `ama=32`, `var=22` and assert both limits are 32. After the 16 A status, call `setTmpMaxCurrent(32)`, `setAbsoluteMaxCurrent(32)`, and `setApiKey("mca", 32)` and assert the generated values are 16.

```python
self.assertEqual(status["charger_hardware_max_current"], 16)
self.assertEqual(status["charger_requested_current_limit"], 16)
self.assertIn("/api/set?amp=16", urls[-3])
self.assertIn("/api/set?ama=16", urls[-2])
self.assertIn("/api/set?mca=16", urls[-1])
```

- [ ] **Step 2: Add a failing Number boundary test**

Construct an `amp` Number with coordinator data containing both 16 A limit keys. Assert `native_max_value == 16`, assert a 17 A write raises `ValueError`, and assert a 16 A write reaches `/api/set?amp=16`.

```python
self.assertEqual(number.native_max_value, 16)
with self.assertRaisesRegex(ValueError, "maximum is 16 A"):
    asyncio.run(number.async_set_native_value(17))
asyncio.run(number.async_set_native_value(16))
```

- [ ] **Step 3: Run the targeted tests and verify RED**

Run: `python3 -m unittest tests.test_api.ApiTests.test_v2_current_limits_follow_hardware_and_configuration tests.test_state_fetcher.StateFetcherTests.test_v2_number_enforces_dynamic_current_limit -v`

Expected: failures because the limit keys and dynamic Number boundary do not exist.

- [ ] **Step 4: Implement the minimum shared limit logic**

In `GoeChargerV2`, initialize both cached limits to 32, add `var` to `FILTER_KEYS`, and update the caches during `requestStatus()`:

```python
hardware_limit = 16 if status.get("var") == 11 or status.get("adi") else 32
absolute_limit = status.get("ama")
self._hardware_max_current = hardware_limit
self._requested_current_limit = (
    min(hardware_limit, int(absolute_limit))
    if isinstance(absolute_limit, (int, float)) and absolute_limit >= 6
    else hardware_limit
)
```

Expose both cached limits in returned coordinator data. Route `amp`, `ama`, and `mca` through one key-aware clamp in `setApiKey()`; have the existing current setter methods call `setApiKey()`.

In `GoeChargerNumber`, retain the configured fallback max, override `native_max_value`, and reject values above it before the executor job:

```python
@property
def native_max_value(self):
    data = (self.coordinator.data or {}).get(self._chargername, {})
    key = "charger_hardware_max_current" if self._api_key == "ama" else "charger_requested_current_limit"
    return data.get(key, self._configured_max) if self._api_key in {"amp", "ama", "mca"} else self._configured_max
```

- [ ] **Step 5: Run the targeted tests and verify GREEN**

Run the command from Step 3.

Expected: both tests pass.

---

### Task 2: Separate read-only phase wish from writable phase mode

**Files:**
- Modify: `custom_components/goecharger/api.py`
- Modify: `custom_components/goecharger/sensor.py`
- Test: `tests/test_api.py`
- Test: `tests/test_state_fetcher.py`

**Interfaces:**
- Produces: `phase_wish_mode` sensor value from `pwm`.
- Produces: `phase_switch_mode` select value from `psm`.
- Produces: `V2_SELECTS["psm"]` with `Automatic`, `Single phase`, and `Three phases` options.

- [ ] **Step 1: Add failing phase entity tests**

Extend API status input with `pwm=1` and `psm=2`; assert the returned fields stay separate and the status filter requests both keys. Assert `pwm` is not a select and `psm` is.

```python
self.assertEqual(status["phase_wish_mode"], 1)
self.assertEqual(status["phase_switch_mode"], 2)
self.assertNotIn("pwm", V2_SELECTS)
self.assertIn("psm", V2_SELECTS)
```

Create the `psm` select from coordinator data, assert its current option is `Three phases`, select `Single phase`, and assert `/api/set?psm=1` was requested. Also assert `phase_wish_mode` appears in the API v2 sensor inventory.

- [ ] **Step 2: Run targeted phase tests and verify RED**

Run: `python3 -m unittest tests.test_api.ApiTests.test_v2_phase_status_and_control_are_separate tests.test_state_fetcher.StateFetcherTests.test_v2_phase_control_writes_psm -v`

Expected: failures because no `psm` select or phase-wish sensor exists.

- [ ] **Step 3: Implement the separated entities**

Add this select description and add `psm` to `FILTER_KEYS`:

```python
"psm": {
    "name": "Phase switch mode",
    "attribute": "phase_switch_mode",
    "options": {"Automatic": 0, "Single phase": 1, "Three phases": 2},
},
```

Map `phase_switch_mode` from `psm`, keep `phase_wish_mode` mapped from `pwm`, and add `phase_wish_mode` to `_v2Sensors` with a plain status name. Existing Select availability already makes `psm` unavailable when its status key is absent.

- [ ] **Step 4: Run targeted phase tests and verify GREEN**

Run the command from Step 2.

Expected: both tests pass.

---

### Task 3: Decode error codes by firmware

**Files:**
- Modify: `custom_components/goecharger/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `GoeChargerV2._error_name(code, firmware) -> str`.
- Consumes: `fwv` from the same status response as `err`.

- [ ] **Step 1: Replace the single-table test with failing firmware cases**

Test representative ambiguous codes on both sides of the boundary:

```python
cases = (
    ("60.4", 13, "STATUS_LOCK_STUCK_LOCKED"),
    ("60.4", 16, "OVERTEMP"),
    ("60.4", 23, "RDC_SELF_TEST_FAILED"),
    ("60.5", 13, "OVERTEMP"),
    ("60.5", 16, "STATUS_LOCK_STUCK_LOCKED"),
    ("60.5", 23, "RESERVED_23"),
    (None, 13, "UNKNOWN"),
)
```

- [ ] **Step 2: Run the error test and verify RED**

Run: `python3 -m unittest tests.test_api.ApiTests.test_v2_error_codes_follow_firmware -v`

Expected: older-firmware and missing-firmware cases fail under the current single table.

- [ ] **Step 3: Implement two tables and a safe selector**

Keep stable codes 0-10 in a shared table. Add the archived pre-60.5 suffix and current 60.5+ suffix. Parse only the first two numeric firmware components with the standard library; malformed or missing versions use only the shared table.

```python
try:
    version = tuple(int(part) for part in str(firmware).split(".")[:2])
except (TypeError, ValueError):
    version = None
mapping = self.ERR_CURRENT if version and version >= (60, 5) else self.ERR_LEGACY if version else self.ERR_STABLE
return mapping.get(code, "UNKNOWN")
```

- [ ] **Step 4: Run the error test and verify GREEN**

Run the command from Step 2.

Expected: all firmware cases pass.

---

### Task 4: Document, verify, and commit the cohesive integration change

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Verify: all tracked integration and test changes

**Interfaces:**
- Documents: dynamic current ranges, read-only `pwm`, writable `psm`, and firmware-aware error names.

- [ ] **Step 1: Update user-facing documentation**

Document that current ranges follow hardware, adapter, and `ama`; list the new phase switch select and read-only phase wish sensor; state that error names are firmware-aware. Expand `## Unreleased` to cover every installable behavior change already present in the working tree.

- [ ] **Step 2: Run fresh full verification**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components/goecharger tests
git diff --check
```

Expected: 0 failures, exit code 0 for all commands.

- [ ] **Step 3: Review the final diff and scope**

Run: `git status --short && git diff --stat && git diff -- custom_components/goecharger tests README.md CHANGELOG.md`

Expected: no Tesla cable-unlock document in the integration diff and no manifest version change.

- [ ] **Step 4: Commit the verified integration change**

```bash
git add CHANGELOG.md README.md custom_components/goecharger/api.py custom_components/goecharger/number.py custom_components/goecharger/sensor.py tests/test_api.py tests/test_sensor_metadata.py tests/test_state_fetcher.py
git commit -m "feat: harden API v2 controls and status"
```

The single integration commit is intentional because the pre-existing changes overlap in the same API and test files; partial commits would leave an invalid intermediate entity surface.
