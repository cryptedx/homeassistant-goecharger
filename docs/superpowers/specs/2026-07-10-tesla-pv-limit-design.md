# Tesla PV charging must honor the vehicle charge limit

## Goal

In `PV-Überschuss` mode, charge the connected Model 3 until the live Tesla
charge limit is reached. The current live limit is 80 percent.

## Problem

The go-e charger can report `charging finished, vehicle still connected` while
the Tesla battery is still below its configured charge limit. Treating that
status as definitive completion records the current battery state as the
restart reference and forces the charger off. The existing 5-percentage-point
hysteresis then prevents an immediate PV restart.

## Design

- Keep the existing PV surplus, grid-import, phase-switching, and start-probe
  behavior unchanged.
- Consider charging complete only when Tesla reports `complete` or its battery
  state of charge has reached the live Tesla charge-limit entity.
- Do not stop charging solely because go-e reports `charging finished, vehicle
  still connected` while Tesla remains below the charge limit.
- Record the restart reference and apply the existing 5-percentage-point
  hysteresis only after this actual completion condition.

## Verification

1. Back up the live automation before the edit.
2. Validate the updated Home Assistant configuration.
3. With Tesla below the charge limit and PV export available, confirm a go-e
   `charging finished` status alone does not set Force Off.
4. At the Tesla charge limit, confirm Force Off and the existing hysteresis
   still operate.
