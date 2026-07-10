# Tesla PV Charge Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep PV charging active below the live Tesla charge limit and retain the restart hysteresis only after actual completion.

**Architecture:** Patch the live Home Assistant automation in place. Its existing charger-first surplus calculation, phase control, grid-import stop, and PV-start probe remain untouched. Completion becomes a Tesla-derived condition: `complete` or battery SoC greater than or equal to the Tesla charge-limit entity.

**Tech Stack:** Home Assistant automation storage API, Tesla Fleet entities, GoAmpLocal `goecharger.set_api_key` service.

## Global Constraints

- Do not change the Model 3 charge limit; read `number.garage_model_3_premium_rwd_2026_ladelimit` live.
- Do not alter current/phase calculation, PV thresholds, grid-import protection, or the start-probe script.
- Create an automation backup before any mutation and require `config_check: valid` before behavioral verification.
- Preserve unrelated workspace changes and stage only this plan document for its documentation commit.

---

### Task 1: Change the live completion gate

**Files:**
- Modify: Home Assistant `automation.model_3_pv_uberschussladen` (live storage automation)
- Test: Home Assistant `config_check` and automation trace `automation.model_3_pv_uberschussladen`

**Interfaces:**
- Consumes: `sensor.garage_model_3_premium_rwd_2026_batteriestand`, `sensor.garage_model_3_premium_rwd_2026_ladestatus`, `number.garage_model_3_premium_rwd_2026_ladelimit`, `input_number.model_3_fahrbereit_soc`
- Produces: Force Off only after Tesla completion; a live SoC below the Tesla limit can reach existing PV-start logic.

- [ ] **Step 1: Capture the failing live condition**

Run a read-only state and trace query. Expected failure evidence at 75% with an 80% Tesla limit is:

```text
go-e status = charging finished, vehicle still connected
Tesla SoC = 75
Tesla charge limit = 80
Force state = Off
```

- [ ] **Step 2: Back up and read the exact current automation**

Run `ha_manage_backup` for `automation.model_3_pv_uberschussladen`, then `ha_config_get_automation`. Record the returned `config_hash` so the transform is applied to the inspected version only.

- [ ] **Step 3: Apply the minimal transform**

Add this variable alongside the existing Tesla variables:

```yaml
tesla_charge_limit: "{{ states('number.garage_model_3_premium_rwd_2026_ladelimit') | float(100) }}"
tesla_complete: "{{ is_state('sensor.garage_model_3_premium_rwd_2026_ladestatus', 'complete') or (tesla_soc | float(0)) >= (tesla_charge_limit | float(100)) }}"
```

Replace both finished-stop `or` conditions so they use:

```yaml
- condition: template
  value_template: "{{ tesla_complete | bool }}"
```

instead of the go-e `charging finished, vehicle still connected` state. The branch that records `input_number.model_3_fahrbereit_soc` and writes `frc=1` must therefore run only when `tesla_complete` is true. The later hysteresis branch must also require `tesla_complete`; this prevents a previously stored 75% reference from blocking a restart below an 80% limit.

- [ ] **Step 4: Validate the live configuration**

Run Home Assistant `config_check`. Expected result:

```text
valid
```

If it is not valid, restore the backup and stop without testing the behavior.

- [ ] **Step 5: Verify the repaired below-limit case**

Read the next automation traces and relevant go-e/Tesla states. With 75% SoC, 80% limit, connected cable, and surplus, the trace must not send `goecharger.set_api_key` with `key: frc, value: 1` because of go-e's finished status. It may run the existing start probe and then set `frc=2` to permit charging.

- [ ] **Step 6: Verify actual completion remains safe**

At a Tesla `complete` state or SoC at or above the Tesla limit, confirm the trace records the completion SoC and sends `frc=1`. This is the only path that should activate the existing five-percentage-point restart hysteresis.

- [ ] **Step 7: Commit the plan documentation**

```bash
git add docs/superpowers/plans/2026-07-10-tesla-pv-charge-limit.md
git commit -m "docs: plan Tesla PV charge-limit fix"
```
