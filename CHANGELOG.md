# Changelog

Version numbers follow SemVer 2.0.0. The installable integration version lives in
`custom_components/goecharger/manifest.json`.

## Unreleased

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
