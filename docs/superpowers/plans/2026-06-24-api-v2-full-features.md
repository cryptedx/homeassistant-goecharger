# API V2 Full Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add selectable local go-eCharger API v2 support with stable existing entities, curated v2-native controls, and an expert API-key service.

**Architecture:** Keep API v1 as the default and map API v2 into the existing status/service surface through a small adapter. Add v2-only `number`, `select`, and `switch` entities for high-value writable keys, plus `goecharger.set_api_key` for every other v2 key. Avoid generating one entity per API key.

**Tech Stack:** Python stdlib (`json`, `urllib.parse`, `urllib.request`), existing `goecharger==0.1.0` for API v1, Home Assistant config flow/options flow, `DataUpdateCoordinator`, `unittest`.

---

## Scope

- Existing v1 entities and services stay stable.
- API version is selected per charger and applied on config-entry reload.
- API v2 status uses `/api/status?filter=...`, not unfiltered `/api/status`.
- API v2 writes use `/api/set?<key>=<json-value>`.
- Curated v2 controls:
  - `number`: `amp`, `ama`, `dwo`, `mca`, `fst`, `pgt`, `zfo`
  - `select`: `frc`, `ust`, `lmo`, `acs`, `pwm`
  - `switch`: `fup`, `awe`, `fzf`, `su`, `sua`
- Expert service: `goecharger.set_api_key` writes any JSON value to any v2 key.

## Tasks

- [ ] Add API-version constants and v2 feature descriptions.
- [ ] Add `custom_components/goecharger/api.py` with v1 wrapper, v2 HTTP client, status mapping, writes, and expert set.
- [ ] Wire config/YAML setup to `create_charger(host, api_version)`.
- [ ] Add config-flow and options-flow API-version selection.
- [ ] Reuse stored adapter in switch setup.
- [ ] Add `number.py` for curated v2 numeric controls.
- [ ] Add `select.py` for curated v2 mode controls.
- [ ] Extend `switch.py` with curated v2 boolean controls.
- [ ] Add `goecharger.set_api_key` service and translations.
- [ ] Update README, changelog, and manifest version to `0.28.0`.
- [ ] Verify with `python3 -m unittest discover -s tests -v` and `git diff --check`.

## Deliberately Skipped

- No automatic entity generation for every API key.
- No MQTT, cloud API, OCPP, or Modbus implementation.
- No live per-request hot-swap; changing API version reloads the config entry.
