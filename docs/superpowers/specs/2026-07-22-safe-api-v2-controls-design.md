# Safe API v2 controls design

Date: 2026-07-22

## Goal

Fix the Home Assistant HTTP 500 caused by invalid current writes without
removing phase information or silently changing error meanings on older
charger firmware.

## Current limits

`GoeChargerV2` will derive two limits from every status response:

- hardware limit: 16 A for an 11 kW variant or an active 16 A adapter,
  otherwise 32 A;
- requested-current limit: the lower of the hardware limit and a valid `ama`
  value.

The API adapter will retain those limits so every existing write path uses the
same guard. `amp` and `mca` use the requested-current limit; `ama` uses the
hardware limit. The Home Assistant number entities expose the same limits
dynamically and reject out-of-range writes before calling the charger. A real
32 A installation keeps its 32 A range.

## Phase controls

`pwm` remains read-only and is exposed as charger status instead of a select.
The writable phase control is a separate `psm` select with explicit Automatic,
single-phase, and three-phase options. It has a new entity identity so the old
`pwm` option meanings cannot be silently reinterpreted.

The `psm` select is available only when the charger returns a readable `psm`
value. If a firmware accepts writes but does not return that key, the entity is
unavailable rather than displaying an invented state; the existing expert
`set_api_key` service remains available.

## Error codes

Error labels are selected from a firmware-specific table. Firmware 60.5 and
newer use the current API table; older firmware uses the archived mapping. If
the firmware version is missing or malformed, only codes whose meanings are
stable across both tables are named and ambiguous codes remain `UNKNOWN`.

## Compatibility and scope

- Existing raw `psm` automations continue to work.
- The removed `select.*_phase_wish_mode` is not reused with changed semantics.
- The stable `binary_sensor.*_error_present` contract is unchanged.
- Power-unit, charge-limit, number-key, and energy-metadata corrections already
  present in the working tree remain in scope.
- The installation-specific Tesla cable-unlock document is not included in the
  integration commit.
- No live Home Assistant deployment or physical charger write is part of this
  implementation.

## Verification

Regression tests must first fail for:

1. a 16 A adapter with `ama=16` exposing or accepting 17-32 A;
2. a genuine 32 A setup losing its 32 A range;
3. writable `pwm` or missing `psm` read/write behavior;
4. different error-code meanings on firmware 60.4 and 60.5.

After implementation, run the targeted tests, the full unittest suite,
`compileall`, and `git diff --check` before committing.
