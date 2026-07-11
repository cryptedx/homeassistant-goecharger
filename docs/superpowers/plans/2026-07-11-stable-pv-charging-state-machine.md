# Stable PV Charging State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overlapping PV stop branches with a persistent state machine that reaches the live Tesla charge limit, targets 900 W grid export, and avoids rapid charging or phase toggles.

**Architecture:** Keep go-e as the only minute-by-minute actuator and Tesla Fleet as completion and charge-limit context. Native `input_select` and `timer` helpers hold start, stop, cooldown, and phase dwell state across automation runs; the existing guarded start-probe script remains the only off-to-on transition path. The main automation becomes `queued`, performs no long dwell delays, increases current slowly, and reduces current immediately when the export reserve is threatened.

**Tech Stack:** Home Assistant storage automations, native input-select and timer helpers, Tesla Fleet entities, GoAmpLocal `goecharger.set_api_key`, Home Assistant traces/history/config validation.

## Global Constraints

- Do not change `number.garage_model_3_premium_rwd_2026_ladelimit`.
- Do not intentionally import grid power; target 900 W export with a 600–1,200 W deadband.
- Keep the existing absolute go-e current limit and valid 6 A minimum.
- Keep `script.goe_pv_startprobe` as the guarded start mechanism.
- Back up every live object immediately before changing it.
- Do not touch unrelated repository changes in `README.md`, `tests/test_sensor_metadata.py`, or `docs/tesla-cable-unlock-analysis.md`.
- A go-e `charging finished, vehicle still connected` state is not authoritative Tesla completion.
- When valid, Tesla battery state and the live Tesla limit take precedence over a stale Tesla `complete` state.

---

### Task 1: Capture the failing baseline and impact surface

**Files:**
- Read: Home Assistant `automation.model_3_pv_uberschussladen`
- Read: Home Assistant `script.goe_pv_startprobe`
- Read: Home Assistant `automation.go_e_pv_startprobe_failsafe_nach_ha_start`
- Test: Home Assistant history and automation traces

**Interfaces:**
- Consumes: current automation/script hashes, all consumers of the existing helpers, 2026-07-11 history
- Produces: immutable pre-change evidence and an exact list of live objects that may be changed

- [ ] **Step 1: Search every consumer before restructuring**

Run configuration searches for each identifier below with full configuration bodies:

```text
automation.model_3_pv_uberschussladen
input_number.model_3_fahrbereit_soc
timer.goe_pv_startprobe_cooldown
input_boolean.goe_pv_startprobe_active
input_select.model_3_ladephase_ziel
script.goe_pv_startprobe
```

Expected: record every automation, script, helper, and dashboard consumer. Do not
delete or rename any existing entity in this implementation.

- [ ] **Step 2: Record optimistic-lock hashes**

Read the three live configs listed under **Files**. Expected current hashes from
the reviewed snapshot are:

```text
automation.model_3_pv_uberschussladen = c3aca813e6b7d031
script.goe_pv_startprobe = 2c08869933932e1a
automation.go_e_pv_startprobe_failsafe_nach_ha_start = 656e5b5201202c25
```

If any hash differs, use the newly read configuration as the source of truth and
review the plan against the changed sections before writing.

- [ ] **Step 3: Preserve the failing evidence**

Query history for 2026-07-11 05:00–10:20 Europe/Berlin. The expected RED case
is:

```text
PV mode remained selected.
Grid export exceeded 2,700 W for longer than three minutes.
Tesla battery state remained unknown until 09:54.
input_number.model_3_fahrbereit_soc remained 75.
go-e remained Force Off until manual Sofortladen at 09:51.
```

This is the failing behavioral test: unknown Tesla data must no longer route a
safe PV start into Force Off.

---

### Task 2: Create persistent state and dwell helpers

**Files:**
- Create: Home Assistant `input_select.model_3_pv_regelstatus`
- Create: Home Assistant `timer.model_3_pv_start_bestaetigung`
- Create: Home Assistant `timer.model_3_pv_stopp_bestaetigung`
- Create: Home Assistant `input_select.model_3_pv_phasen_kandidat`
- Create: Home Assistant `timer.model_3_pv_phasen_bestaetigung`
- Create: Home Assistant `timer.model_3_pv_phasen_sperre`
- Modify: Home Assistant `timer.goe_pv_startprobe_cooldown`

**Interfaces:**
- Consumes: native Home Assistant helper services
- Produces: restored state and timers used by Task 3

- [ ] **Step 1: Back up the existing cooldown helper**

Create an edit backup for `timer.goe_pv_startprobe_cooldown` before changing its
duration.

- [ ] **Step 2: Create the state helper**

Call the managed helper API with these exact fields and omit `initial` so Home
Assistant restores the last state:

```json
{
  "action": "create",
  "helper_type": "input_select",
  "helper_id": "model_3_pv_regelstatus",
  "name": "Model 3 PV-Regelstatus",
  "options": ["Warten", "Startprüfung", "Laden", "Stoppprüfung", "Pause", "Voll"],
  "icon": "mdi:state-machine"
}
```

- [ ] **Step 3: Create the start and stop confirmation timers**

```json
{
  "action": "create",
  "helper_type": "timer",
  "helper_id": "model_3_pv_start_bestaetigung",
  "name": "Model 3 PV Start Bestätigung",
  "duration": "00:03:00",
  "restore": true,
  "icon": "mdi:timer-play-outline"
}
```

```json
{
  "action": "create",
  "helper_type": "timer",
  "helper_id": "model_3_pv_stopp_bestaetigung",
  "name": "Model 3 PV Stopp Bestätigung",
  "duration": "00:00:30",
  "restore": true,
  "icon": "mdi:timer-stop-outline"
}
```

- [ ] **Step 4: Create the phase candidate and timers**

```json
{
  "action": "create",
  "helper_type": "input_select",
  "helper_id": "model_3_pv_phasen_kandidat",
  "name": "Model 3 PV Phasen Kandidat",
  "options": ["Keine", "1 Phase", "3 Phasen"],
  "icon": "mdi:transmission-tower"
}
```

```json
{
  "action": "create",
  "helper_type": "timer",
  "helper_id": "model_3_pv_phasen_bestaetigung",
  "name": "Model 3 PV Phasen Bestätigung",
  "duration": "00:05:00",
  "restore": true,
  "icon": "mdi:timer-check-outline"
}
```

```json
{
  "action": "create",
  "helper_type": "timer",
  "helper_id": "model_3_pv_phasen_sperre",
  "name": "Model 3 PV Phasen Sperre",
  "duration": "00:15:00",
  "restore": true,
  "icon": "mdi:timer-lock-outline"
}
```

- [ ] **Step 5: Change the existing probe cooldown to ten minutes**

Update `timer.goe_pv_startprobe_cooldown` to:

```json
{
  "action": "update",
  "helper_type": "timer",
  "helper_id": "goe_pv_startprobe_cooldown",
  "duration": "00:10:00",
  "restore": true
}
```

- [ ] **Step 6: Read back every helper**

Expected entity states and attributes:

```text
input_select.model_3_pv_regelstatus: one of the six declared options
timer.model_3_pv_start_bestaetigung: duration 00:03:00, restore true
timer.model_3_pv_stopp_bestaetigung: duration 00:00:30, restore true
input_select.model_3_pv_phasen_kandidat: one of Keine/1 Phase/3 Phasen
timer.model_3_pv_phasen_bestaetigung: duration 00:05:00, restore true
timer.model_3_pv_phasen_sperre: duration 00:15:00, restore true
timer.goe_pv_startprobe_cooldown: duration 00:10:00, restore true
```

---

### Task 3: Replace overlapping PV branches with the state machine

**Files:**
- Modify: Home Assistant `automation.model_3_pv_uberschussladen`
- Test: Home Assistant config validation, config readback, traces, states, and history

**Interfaces:**
- Consumes: helpers from Task 2, existing go-e and Tesla entities, `script.goe_pv_startprobe`
- Produces: one deterministic control path for waiting, starting, charging, stopping, cooldown, and completion

- [ ] **Step 1: Back up the live automation**

Create an edit backup for `automation.model_3_pv_uberschussladen`, then read the
automation again and use that read's `config_hash` for optimistic locking.

- [ ] **Step 2: Replace the trigger set**

Keep `mode_changed` and the one-minute tick. Add native state/event triggers for
the control boundaries:

```yaml
triggers:
  - trigger: state
    entity_id: input_select.model_3_lademodus
    id: mode_changed
  - trigger: time_pattern
    minutes: /1
    id: tick
  - trigger: state
    entity_id: binary_sensor.goecharger_go_e_charger_links_charging
    to: "on"
    id: charging_started
  - trigger: state
    entity_id: binary_sensor.goecharger_go_e_charger_links_car_connected
    to: "off"
    id: car_disconnected
  - trigger: state
    entity_id: sensor.garage_model_3_premium_rwd_2026_ladestatus
    id: tesla_status_changed
  - trigger: state
    entity_id: sensor.garage_model_3_premium_rwd_2026_batteriestand
    id: tesla_soc_changed
  - trigger: state
    entity_id: number.garage_model_3_premium_rwd_2026_ladelimit
    id: tesla_limit_changed
  - trigger: state
    entity_id: input_boolean.goe_pv_startprobe_active
    to: "off"
    id: startprobe_finished
  - trigger: state
    entity_id: sensor.haus_smart_meter_leistung
    to: unavailable
    for: "00:02:00"
    id: house_power_invalid
  - trigger: state
    entity_id: sensor.haus_smart_meter_leistung
    to: unknown
    for: "00:02:00"
    id: house_power_invalid
  - trigger: state
    entity_id: binary_sensor.goecharger_go_e_charger_links_error_present
    to: "on"
    id: charger_error
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.model_3_pv_start_bestaetigung
    id: start_confirmed
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.model_3_pv_stopp_bestaetigung
    id: stop_confirmed
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.model_3_pv_phasen_bestaetigung
    id: phase_confirmed
  - trigger: event
    event_type: timer.finished
    event_data:
      entity_id: timer.goe_pv_startprobe_cooldown
    id: cooldown_finished
```

- [ ] **Step 3: Replace the automation variables**

Use these exact state and power calculations:

```yaml
variables:
  reserve_w: 900
  deadband_low_w: 600
  deadband_high_w: 1200
  start_export_w: 2700
  phase_up_w: 5000
  phase_down_w: 4200
  min_a: 6
  net_valid: "{{ has_value('sensor.haus_smart_meter_leistung') }}"
  net_w: "{{ states('sensor.haus_smart_meter_leistung') | float(0) }}"
  export_w: "{{ 0 - (net_w | float(0)) }}"
  charger_power_w: "{{ (states('sensor.goecharger_go_e_charger_links_p_all') | float(0) * 1000) | round(0) }}"
  controllable_w: "{{ ((export_w | float(0)) + (charger_power_w | float(0)) - reserve_w) | round(0) }}"
  max_a: "{{ states('number.goecharger_go_e_charger_links_charger_absolute_max_current') | int(16) }}"
  current_a: "{{ states('number.goecharger_go_e_charger_links_charger_max_current') | int(6) }}"
  phase_target: "{{ states('input_select.model_3_ladephase_ziel') }}"
  watts_per_amp: "{{ 690 if phase_target == '3 Phasen' else 230 }}"
  reduction_a: "{{ (((deadband_low_w - export_w) / (watts_per_amp | float(230))) | round(0, 'ceil') | int) if export_w < deadband_low_w else 0 }}"
  requested_a: >-
    {% if not net_valid %}
      {{ current_a }}
    {% elif export_w > deadband_high_w %}
      {{ [max_a, current_a + 1] | min }}
    {% elif export_w < deadband_low_w %}
      {{ [min_a, current_a - reduction_a] | max }}
    {% else %}
      {{ current_a }}
    {% endif %}
  tesla_soc_valid: "{{ has_value('sensor.garage_model_3_premium_rwd_2026_batteriestand') }}"
  tesla_limit_valid: "{{ has_value('number.garage_model_3_premium_rwd_2026_ladelimit') }}"
  tesla_soc: "{{ states('sensor.garage_model_3_premium_rwd_2026_batteriestand') | float(0) }}"
  tesla_limit: "{{ states('number.garage_model_3_premium_rwd_2026_ladelimit') | float(0) }}"
  tesla_complete: >-
    {{ (tesla_soc_valid and tesla_limit_valid and tesla_soc >= tesla_limit)
       or ((not tesla_soc_valid or not tesla_limit_valid)
           and is_state('sensor.garage_model_3_premium_rwd_2026_ladestatus', 'complete')) }}
```

- [ ] **Step 4: Implement mode and safety precedence**

The top-level action order must be exactly:

```text
1. Aus: Force Off, phase Auto, cancel all new timers, state Warten.
2. Sofortladen: preserve the existing 3-phase/max-current behavior and cancel
   PV state-machine timers.
3. PV charger error or house power invalid for two minutes: Force Off, start
   the ten-minute cooldown, state Pause.
4. PV disconnected cable: Force Off, cancel all timers, state Warten.
5. PV authoritative Tesla completion: Force Off, cancel confirmation timers,
   state Voll.
6. Remaining PV events: process the state machine below.
```

Do not use go-e `charging finished, vehicle still connected` in item 5.
On `cooldown_finished`, change `Pause` to `Warten`; the next start must still
complete the full three-minute confirmation timer.

- [ ] **Step 5: Implement waiting and guarded start**

Use this state transition table:

```text
Warten + connected + no errors + export >= 2700 W + cooldown idle
  -> start timer.model_3_pv_start_bestaetigung; state Startprüfung

Startprüfung + export < 2700 W or disconnected/error/complete
  -> cancel start timer; state Warten (or Voll for completion)

start_confirmed + still eligible
  -> script.turn_on script.goe_pv_startprobe; remain Startprüfung

charging_started
  -> cancel start timer; state Laden

startprobe_finished + charging remains off
  -> state Pause; rely on timer.goe_pv_startprobe_cooldown started by the
     existing script; if it is unexpectedly idle, start it explicitly
```

Unknown Tesla SoC or limit is not a start-blocking condition.

- [ ] **Step 6: Implement running current control**

On every `tick` in `Laden` or `Stoppprüfung`:

```text
If net power is valid, write go-e amp=requested_a.
If requested_a > current_a, the increase is exactly 1 A maximum.
If requested_a < current_a, apply the full calculated reduction immediately.
Keep frc=2 while regulation continues.
```

At one phase and 6 A:

```text
net_w > 100 W and state Laden
  -> start timer.model_3_pv_stopp_bestaetigung; state Stoppprüfung

net_w <= 100 W and state Stoppprüfung
  -> cancel stop timer; state Laden

stop_confirmed + net_w > 100 W + one phase + 6 A
  -> frc=1; start timer.goe_pv_startprobe_cooldown; state Pause
```

- [ ] **Step 7: Implement phase hysteresis**

On each valid-power tick while state is `Laden`:

```text
1 Phase + controllable_w >= 5000 + phase lockout idle
  -> candidate 3 Phasen; start five-minute phase confirmation

3 Phasen + controllable_w < 4200 + phase lockout idle
  -> candidate 1 Phase; start five-minute phase confirmation

Candidate no longer matches current power
  -> cancel confirmation; candidate Keine

phase_confirmed + candidate still matches + phase lockout idle
  -> frc=1; wait 8 seconds; write psm (1 or 2); update phase target;
     wait 8 seconds; write amp=requested_a; frc=2; start 15-minute lockout;
     candidate Keine
```

A phase change must not start the ten-minute charging cooldown.

- [ ] **Step 8: Change execution mode and write with optimistic locking**

Set:

```yaml
mode: queued
max: 10
```

Write the complete automation through the managed config API using the hash
read immediately after the Task 3 backup.

- [ ] **Step 9: Validate and read back**

Run `ha_get_system_health(include="config_check")`. Expected:

```text
config_check: valid
```

Read the automation again and confirm all triggers, variables, state options,
timers, `mode: queued`, and `max: 10` survived round-trip validation. If
validation fails, restore the Task 3 automation backup before continuing.

---

### Task 4: Verify behavior and synchronize documentation

**Files:**
- Modify when mounted: `/Volumes/config/docs/home-assistant/model-3-pv-ueberschussladen.html`
- Test: Home Assistant states, traces, history, and current Tesla-complete state

**Interfaces:**
- Consumes: Task 3 live automation and helper states
- Produces: current-session safety proof plus a checklist for the next naturally available charging session

- [ ] **Step 1: Verify the current complete state remains safe**

With the Tesla currently at its valid live limit, trigger only a normal
automation evaluation and confirm:

```text
PV-Regelstatus = Voll
go-e Force state = Off
No start confirmation timer is active
No start probe runs
```

- [ ] **Step 2: Verify the historical failure is removed structurally**

Evaluate the new completion/start templates with this state matrix:

```text
SoC unknown, limit unknown, connected, export 5000 W, Tesla status stopped
  -> not complete; start eligible

SoC 75, limit 80, connected, export 5000 W, go-e finished
  -> not complete; start eligible

SoC 80, limit 80
  -> complete; Force Off

SoC 80, limit raised to 90, Tesla status still complete
  -> not complete; start eligibility restarts from the full three-minute dwell
```

- [ ] **Step 3: Inspect the first five post-change traces**

Expected: one deterministic branch per run, no alternating `frc=1`/`frc=2`
caused solely by go-e `charging finished`, and no errors.

- [ ] **Step 4: Synchronize the live explainer**

Check for
`/Volumes/config/docs/home-assistant/model-3-pv-ueberschussladen.html`. When the
mount is available, update its threshold, hysteresis, cooldown, phase-lockout,
unknown-Tesla-data, and completion sections to exactly match the approved spec.
If the mount is unavailable, report this single documentation follow-up without
claiming the documentation is synchronized.

- [ ] **Step 5: Verify the next natural charging session**

Without changing the Tesla limit or forcing a synthetic vehicle state, observe
the next session and confirm:

```text
Start only after three minutes at >=2700 W export.
Unknown Tesla data does not block the guarded start.
Current increases by <=1 A/min and may decrease by multiple A immediately.
The 600–1200 W export deadband causes no writes beyond the unchanged current.
Grid import >100 W at one phase/6 A must persist 30 seconds before stop.
Cooldown blocks restart for ten minutes.
Phase candidate persists five minutes and phase changes are 15 minutes apart.
Tesla reaches its live limit and then remains off.
```

- [ ] **Step 6: Commit only repository documentation produced by planning**

```bash
git add docs/superpowers/plans/2026-07-11-stable-pv-charging-state-machine.md
git commit -m "docs: plan stable PV charging state machine"
```
