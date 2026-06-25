# GoAmpLocal

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cryptedx&repository=homeassistant-goecharger&category=integration)
[![Validate with hassfest](https://github.com/cryptedx/homeassistant-goecharger/actions/workflows/hassfest.yaml/badge.svg?branch=main)](https://github.com/cryptedx/homeassistant-goecharger/actions/workflows/hassfest.yaml)

GoAmpLocal is a maintained Home Assistant custom integration for controlling
compatible go-e chargers over the local network.

It is based on the original `cathiele/homeassistant-goecharger` project and has
been refreshed with selectable local API v2 support while keeping API v1 as a
fallback for existing installations.

This project is not affiliated with go-e GmbH and is not an official takeover of
the original upstream project. The Home Assistant integration domain remains
`goecharger` for compatibility.

## Features

- Local polling and control; no cloud connection required for charger control.
- API v2 support for newer chargers, selectable per charger.
- API v1 fallback for existing setups.
- Sensors for charger status, current, voltage, power, temperature, energy, and
  selected API v2 values.
- Switch, number, and select entities for common API v2 controls.
- Expert `goecharger.set_api_key` service for API v2 keys that do not need a
  dedicated entity.
- Optional correction factor for older devices that report slightly low voltage
  and energy values.
- LAN auto-discovery via zeroconf/mDNS.
- Binary sensor entities for charger states.
- Sensor metadata includes proper Home Assistant sensor device classes.
- Diagnostics export for easy troubleshooting.
- API version auto-detect in config flow for easier setup.

## Installation

### HACS

Use the My Home Assistant button above, or add this repository in HACS and
install the integration from there.

### Manual

Copy `custom_components/goecharger` into your Home Assistant
`custom_components` directory and restart Home Assistant.

```bash
mkdir -p <your-ha-config-dir>/custom_components
cp -r custom_components/goecharger <your-ha-config-dir>/custom_components/
```

## Configuration

For new setups, add the integration through Home Assistant:

`Settings -> Devices & services -> Add integration -> go-eCharger`

Enable the local HTTP API v2 in the go-e app first if you want to use API v2
controls. Existing installations without an `api_version` setting keep API v1.

YAML configuration is still supported:

```yaml
goecharger:
  chargers:
    - name: charger1
      host: 192.0.2.10
      api_version: v2
    - name: charger2
      host: charger2.local
      api_version: v1
      correction_factor: 1.05
```

## API v2 Controls

API v2 exposes curated Home Assistant entities instead of one entity per raw API
key:

- `number`: requested current, absolute max current, charge limit, minimum
  charging current, grid target power, and related tuning values.
- `select`: force state, cable lock mode, logic mode, access control, and phase
  wish mode.
- `switch`: charging allowed, PV surplus, Awattar, zero feed-in, and selected
  simulation switches.

For advanced keys, call the expert service:

```yaml
action: goecharger.set_api_key
data:
  charger_name: charger1
  key: fup
  value: true
```

## Generic BEV Automation Template

Create an `input_select.ev_charging_mode` helper with these options:

- `Off`
- `Immediate`
- `PV surplus`
- `Departure`

Then adapt the placeholder entity IDs to your charger name. This example assumes
the charger is named `charger1` and uses a signed grid sensor where negative
values mean export to the grid.

```yaml
- id: goamplocal_bev_mode_template
  alias: "EV charging: apply selected mode"
  mode: restart
  triggers:
    - trigger: state
      entity_id:
        - input_select.ev_charging_mode
        - sensor.house_grid_power
        - sensor.goecharger_charger1_car_status
  conditions:
    - condition: state
      entity_id: sensor.goecharger_charger1_car_status
      state:
        - "charging"
        - "Waiting for vehicle"
        - "charging finished, vehicle still connected"
  actions:
    - choose:
        - conditions:
            - condition: state
              entity_id: input_select.ev_charging_mode
              state: "Off"
          sequence:
            - action: switch.turn_off
              target:
                entity_id: switch.goecharger_charger1_allow_charging

        - conditions:
            - condition: state
              entity_id: input_select.ev_charging_mode
              state: "Immediate"
          sequence:
            - action: switch.turn_off
              target:
                entity_id: switch.goecharger_charger1_pv_surplus
            - action: number.set_value
              target:
                entity_id: number.goecharger_charger1_charger_max_current
              data:
                value: 16
            - action: switch.turn_on
              target:
                entity_id: switch.goecharger_charger1_allow_charging

        - conditions:
            - condition: state
              entity_id: input_select.ev_charging_mode
              state: "Departure"
          sequence:
            - action: switch.turn_off
              target:
                entity_id: switch.goecharger_charger1_pv_surplus
            - action: select.select_option
              target:
                entity_id: select.goecharger_charger1_phase_wish_mode
              data:
                option: "Wish 3"
            - action: number.set_value
              target:
                entity_id: number.goecharger_charger1_charger_max_current
              data:
                value: 10
            - action: switch.turn_on
              target:
                entity_id: switch.goecharger_charger1_allow_charging

        - conditions:
            - condition: state
              entity_id: input_select.ev_charging_mode
              state: "PV surplus"
          sequence:
            - choose:
                - conditions:
                    - condition: numeric_state
                      entity_id: sensor.house_grid_power
                      below: -1500
                  sequence:
                    - action: switch.turn_on
                      target:
                        entity_id: switch.goecharger_charger1_pv_surplus
                    - action: select.select_option
                      target:
                        entity_id: select.goecharger_charger1_phase_wish_mode
                      data:
                        option: "Wish 1"
                    - action: number.set_value
                      target:
                        entity_id: number.goecharger_charger1_charger_max_current
                      data:
                        value: 6
                    - action: switch.turn_on
                      target:
                        entity_id: switch.goecharger_charger1_allow_charging
                - conditions:
                    - condition: numeric_state
                      entity_id: sensor.house_grid_power
                      above: 500
                  sequence:
                    - action: switch.turn_off
                      target:
                        entity_id: switch.goecharger_charger1_allow_charging
```

This mirrors a small Home Assistant driven setup: one mode helper, charger-local
controls, house power as the PV signal, and no vehicle-specific SoC assumptions.
Use evcc or another dedicated controller if you need tariff-aware plans, battery
coordination, or advanced load management.

## Development

- Keep `README.md` up to date for every user-facing integration change.

Run the test suite before committing:

```bash
python3 -m unittest discover -s tests -v
```

Version numbers follow SemVer. The installable integration version lives in
`custom_components/goecharger/manifest.json` and is bumped by the release
workflow.

## License And Attribution

This project is released under the MIT License. It keeps the upstream copyright
and license notice from `cathiele/homeassistant-goecharger`, as required by the
license.
