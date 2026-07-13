# Stable Tesla PV Charging State Machine

## Goal

Charge the connected Tesla to its live vehicle charge limit using PV surplus,
without intentional grid import and without repeated start/stop or phase
switching cycles.

## Observed Failure

On 2026-07-11, stable PV export was already sufficient for one-phase charging
from approximately 06:40. The automation did not start because Tesla Fleet
reported an unknown battery state while `input_number.model_3_fahrbereit_soc`
still contained 75 percent. The current hysteresis branch interprets an unknown
Tesla state as a stop condition and executes before the guarded start probe.
Manual `Sofortladen` at 09:51 cleared the block, after which the vehicle charged
from 75 to its configured 80 percent limit.

## Control Model

The automation shall use explicit control states instead of overlapping stop
branches:

1. `waiting`: The vehicle is connected, but stable start surplus is not yet
   available.
2. `charging`: The charger is enabled and current is regulated against the
   export reserve.
3. `stop_pending`: The charger is already at one phase and 6 A, and grid import
   has remained above the stop threshold.
4. `cooldown`: Charging is off and cannot restart until the cooldown expires.
5. `complete`: Tesla has reached its live charge limit. Tesla's `complete`
   status is used only when both the current SoC and live limit are unavailable.

Persistent Home Assistant helpers or timers shall hold state across automation
restarts. A new trigger must not cancel or accidentally reset dwell periods.

## Start Rules

- `PV-Überschuss` mode must be selected.
- The vehicle and cable must be connected and the charger must have no error.
- Start only after grid export is at least 2,700 W continuously for three
  minutes. Any relevant power measurement below that threshold immediately
  cancels and restarts the confirmation.
- Do not start during the ten-minute cooldown.
- An unknown Tesla battery state must not block the guarded start. Starting the
  charger is allowed to wake the vehicle so Tesla Fleet can refresh its battery
  state and live charge limit.
- Do not start when a valid battery state is greater than or equal to the valid
  live Tesla charge limit. A stale Tesla `complete` status must not block a
  start when valid SoC is below a newly raised live limit.

## Running Regulation

- Keep go-e as the actuator. Tesla provides completion, battery state, and
  charge-limit context only.
- Target 900 W of grid export. Grid import is never an operating target.
- Treat 600 to 1,200 W export as a no-change deadband around the 900 W target.
- Increase requested current by no more than 1 A per minute and only when export
  exceeds 1,200 W.
- Reduce requested current when export falls below 600 W.
- Reduce current immediately by the number of amperes required to recover the
  reserve; downward regulation is not limited to 1 A per minute.
- Keep the valid go-e current range and existing absolute-current limit.

## Stop and Restart Rules

- At one phase and 6 A, stop when grid import remains above 100 W for 30
  seconds. Isolated measurement spikes must not stop charging.
- After a PV-insufficiency stop, enter a ten-minute cooldown.
- After cooldown, require the complete three-minute 2,700 W start condition
  again. A previous surplus period must not be counted retroactively.
- A go-e `charging finished, vehicle still connected` state alone must not mark
  the Tesla complete or record a completion state of charge.
- A valid Tesla SoC at or above the live Tesla charge limit is authoritative
  completion. Tesla `complete` is a fallback only while both SoC and limit data
  are unavailable.
- When the Tesla charge limit increases while the controller is `complete`, it
  must leave `complete` immediately and return to `waiting`; it may start only
  after the normal three-minute PV-surplus confirmation. A limit decrease that
  places SoC at or above the new limit must enter `complete` and force charging
  off.

## Phase Switching

- Use separate upshift and downshift thresholds so one threshold cannot cause
  oscillation in both directions.
- Calculate controllable charging power as current charger power plus grid
  export minus the 900 W reserve.
- Permit an upshift to three phases only when controllable charging power is at
  least 5,000 W continuously for five minutes.
- Permit a downshift to one phase when controllable charging power is below
  4,200 W continuously for five minutes.
- Enforce at least 15 minutes between phase changes.
- A phase change may briefly pause charging as required by go-e, but it must not
  be treated as a PV stop or start a ten-minute cooldown.

## Missing or Invalid Data

- Invalid house-power data must fail safe by preventing current increases. If
  it remains invalid for two minutes while charging, stop and enter cooldown.
- Invalid Tesla battery or charge-limit data must not block an otherwise safe
  PV start. The automation must continue charger-first regulation until Tesla
  data becomes valid.
- Once Tesla data is valid, the live vehicle charge limit must be honored.
- Charger errors must force charging off independently of PV hysteresis.

## Verification

1. Back up the live automation and all helpers/scripts changed by the work.
2. Reproduce the current failure with valid surplus, remembered 75 percent, and
   unknown Tesla battery state; verify the existing logic remains off.
3. Run Home Assistant configuration validation after the change.
4. Verify the same scenario enters guarded start instead of Force Off.
5. Observe multiple regulation intervals to prove current increases slowly,
   decreases quickly, and does not intentionally cross into grid import.
6. Verify a short cloud or load spike does not stop charging.
7. Verify import above 100 W for 30 seconds at one phase and 6 A stops charging,
   starts the ten-minute cooldown, and cannot immediately restart.
8. After that cooldown, verify a fresh uninterrupted three-minute export period
   starts charging again, even when go-e still reports `charging finished,
   vehicle still connected`.
9. Verify Tesla reaches its live charge limit and then enters `complete` without
   further start probes.
10. Raise the Tesla limit from 80 to 90 percent after `complete`; verify the
   controller returns to `waiting`, ignores a stale Tesla `complete` status
   while SoC is below 90 percent, and restarts only after three minutes of
   sufficient PV export.
11. Verify phase switching respects both five-minute dwell times and the
   15-minute phase-change lockout.
12. Keep the Home Assistant charging explainer synchronized with the final live
   thresholds and behavior.
