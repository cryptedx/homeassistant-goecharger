# Changelog

Version numbers follow SemVer 2.0.0. The installable integration version lives in
`custom_components/goecharger/manifest.json`.

## Unreleased

## 0.31.0 - 2026-07-22

- Limit API v2 current controls to the charger hardware, an active 16 A adapter,
  and the configured absolute maximum instead of always advertising 32 A.
- Keep the read-only `pwm` phase wish as status and expose writable `psm` phase
  switching separately when the charger reports it.
- Keep documented API v2 error states available and map `charger_err` enum names
  according to charger firmware.
- Correct API v2 grid, PV, and battery power values from watts to kilowatts.
- Restore API-key-based values for tuning numbers and represent a disabled
  charge limit as zero.

## 0.30.2 - 2026-06-25

- fix: sort manifest keys for hassfest

## 0.30.1 - 2026-06-25

- Merge remote-tracking branch 'origin/main'
- fix: satisfy hassfest zeroconf validation

## 0.30.0 - 2026-06-25

- Merge remote-tracking branch 'origin/main'
- test: isolate zeroconf config flow stub
- Merge branch 'codex/config-flow-autodetect' into codex/integrate-next-features
- Merge branch 'codex/zeroconf-discovery' into codex/integrate-next-features
- Merge branch 'codex/diagnostics-export' into codex/integrate-next-features
- Merge branch 'codex/binary-sensors' into codex/integrate-next-features
- feat: autodetect charger api version
- feat: add go-e zeroconf discovery
- feat: add charger binary sensors
- feat: add sensor device classes
- feat: add diagnostics export
- docs: plan next goecharger features

## 0.29.3 - 2026-06-24

- Refresh project metadata for GoAmpLocal.

## 0.29.2 - 2026-06-24

- fix: mark API v2 as recommended

## 0.29.1 - 2026-06-24

- Mark API v2 as the recommended local API option in the setup UI.

## 0.29.0 - 2026-06-24

- feat: add selectable go-eCharger API v2 backend
- Handle failed goecharger updates gracefully

## 0.28.0 - 2026-06-24

- Added selectable local API v2 support while keeping API v1 as the default.
- Added curated API v2 number, select, and switch entities for core charger controls.
- Added `goecharger.set_api_key` for expert API v2 writes.

## 0.27.4 - 2026-06-24

- Publish HACS release ZIP assets so installs do not depend on HACS' cached repository path.

## 0.27.3 - 2026-06-24

- Clean up translations and update checkout action

## 0.27.2 - 2026-06-24

- Added repository versioning policy, changelog, and versioning checks.
- Added automatic SemVer bumping, Git tag creation, and GitHub Release publishing.

## 0.27.1 - 2026-06-24

- Updated the go-eCharger API V1 Python client from `goecharger==0.0.16` to `goecharger==0.1.0`.

## 0.27.0 - 2026-06-24

- Current maintained-fork baseline.
