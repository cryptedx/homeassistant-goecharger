# HACS None Manifest Failure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the HACS install failure `No manifest.json file found 'custom_components/None/manifest.json'` for `cryptedx/homeassistant-goecharger`.

**Architecture:** Treat the published repository as one boundary and the running Home Assistant/HACS state as the other. The GitHub tag `v0.27.2` already contains `custom_components/goecharger/manifest.json`, so the first fix path is to clear or refresh HACS' cached repository path state instead of adding more repository guesses. Only if a clean HACS state with a current HACS version still fails do we escalate to a HACS upstream bug or temporary manual install.

**Tech Stack:** Home Assistant, HACS, GitHub release tags, this repository's Python unittest suite.

---

## Current Evidence

- GitHub tree for `v0.27.2` contains:
  - `custom_components/goecharger`
  - `custom_components/goecharger/manifest.json`
- Current HACS source derives the integration remote path by taking the first directory below `custom_components`, then reading `<remote>/manifest.json`.
- The observed error path `custom_components/None/manifest.json` means the running HACS instance has either cached `content.path.remote = custom_components/None` or is running logic that failed to resolve the directory before manifest lookup.
- A repository-side `custom_components/None` mirror is not the first fix. It would hide the HACS state bug and risks hassfest/integration-structure fallout.

---

### Task 1: Capture Live HACS State

**Files:**
- Read-only on Home Assistant host: `/config/.storage/*`
- Read-only on Home Assistant host: `/config/home-assistant.log`
- No repository files modified.

- [ ] **Step 1: Capture HACS version from the UI**

Open Home Assistant:

```text
Settings -> Devices & services -> HACS -> Configure / Integration info
```

Record the installed HACS version in the task notes.

Expected: We know the exact HACS version before changing anything.

- [ ] **Step 2: Search HACS storage for the poisoned path**

Run on the Home Assistant host or inside the Home Assistant container:

```bash
grep -R "cryptedx/homeassistant-goecharger\|custom_components/None\|homeassistant-goecharger" /config/.storage /config/home-assistant.log
```

Expected if the cache is poisoned:

```text
...cryptedx/homeassistant-goecharger...
...custom_components/None...
```

Expected if the cache is not poisoned:

```text
No storage line contains custom_components/None for this repository.
```

- [ ] **Step 3: Preserve evidence**

Copy the relevant lines into the execution notes before making any change.

Expected: The notes contain the HACS version and whether `/config/.storage` contains `custom_components/None`.

---

### Task 2: Reset HACS Repository State Without Editing Storage

**Files:**
- Home Assistant UI-managed HACS state.
- No repository files modified.

- [ ] **Step 1: Remove the custom repository from HACS**

In Home Assistant:

```text
HACS -> three-dot menu -> Custom repositories
```

Remove:

```text
cryptedx/homeassistant-goecharger
```

Expected: The custom repository is no longer listed.

- [ ] **Step 2: Restart Home Assistant**

Use the UI restart:

```text
Developer tools -> YAML -> Restart Home Assistant
```

Expected: Home Assistant starts cleanly.

- [ ] **Step 3: Verify the stale path is gone**

Run on the Home Assistant host:

```bash
grep -R "cryptedx/homeassistant-goecharger\|custom_components/None" /config/.storage /config/home-assistant.log
```

Expected:

```text
No active HACS repository record for cryptedx/homeassistant-goecharger remains.
```

If this still shows `custom_components/None`, stop here and continue with Task 4.

---

### Task 3: Re-add and Install From a Clean HACS State

**Files:**
- Download target on Home Assistant host: `/config/custom_components/goecharger`
- No repository files modified.

- [ ] **Step 1: Add the repository fresh**

In Home Assistant:

```text
HACS -> three-dot menu -> Custom repositories
```

Add:

```text
Repository: cryptedx/homeassistant-goecharger
Category: Integration
```

Expected: HACS accepts the repository and shows `go-eCharger`.

- [ ] **Step 2: Download the current release**

Select:

```text
Version: v0.27.2
```

Expected: Download completes without `custom_components/None/manifest.json`.

- [ ] **Step 3: Verify installed files**

Run on the Home Assistant host:

```bash
test -f /config/custom_components/goecharger/manifest.json
grep '"domain": "goecharger"' /config/custom_components/goecharger/manifest.json
```

Expected:

```text
  "domain": "goecharger",
```

- [ ] **Step 4: Restart Home Assistant**

Restart Home Assistant from the UI.

Expected: The integration files are loaded from `/config/custom_components/goecharger`.

---

### Task 4: If the Stale Path Survives, Remove Only the Broken HACS Record

**Files:**
- Backup: `/config/.storage/hacs.repositories.backup-goecharger-none`
- Modify only if needed: `/config/.storage/hacs.repositories`

- [ ] **Step 1: Stop before manual storage edits**

Do not edit `.storage` while Home Assistant is running.

Expected: Home Assistant is stopped or a full configuration backup exists.

- [ ] **Step 2: Back up the HACS repositories file**

Run on the Home Assistant host:

```bash
cp /config/.storage/hacs.repositories /config/.storage/hacs.repositories.backup-goecharger-none
```

Expected: Backup file exists.

- [ ] **Step 3: Inspect the JSON shape before editing**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("/config/.storage/hacs.repositories")
data = json.loads(path.read_text(encoding="utf-8"))
print(type(data).__name__)
print(data.keys())
print(type(data.get("data")).__name__)
print(data.get("data"))
PY
```

Expected: The output shows where the `cryptedx/homeassistant-goecharger` record lives. If the structure is not obvious, stop and do not edit by hand.

- [ ] **Step 4: Remove only the go-eCharger record**

Use the exact structure discovered in Step 3. The edit must remove only entries whose full name is:

```text
cryptedx/homeassistant-goecharger
```

Expected: No other HACS repository data changes.

- [ ] **Step 5: Start Home Assistant and repeat Task 3**

Expected: HACS creates a fresh repository record and no longer references `custom_components/None`.

---

### Task 5: If a Clean State Still Fails, Update HACS and Retest

**Files:**
- HACS integration files managed by Home Assistant/HACS.
- No repository files modified.

- [ ] **Step 1: Update HACS**

Use HACS' own update flow or reinstall HACS from its current official installation method.

Expected: HACS reports the current available version after restart.

- [ ] **Step 2: Restart Home Assistant**

Expected: HACS loads with the updated version.

- [ ] **Step 3: Repeat Task 2 and Task 3**

Expected: A current HACS instance with clean repository state installs `v0.27.2`.

---

### Task 6: Repository Fallback Only If HACS Is Proven Broken

**Files:**
- No immediate repository change.
- Temporary manual install target: `/config/custom_components/goecharger`

- [ ] **Step 1: Confirm all prior gates failed**

Do not continue unless all are true:

```text
v0.27.2 GitHub tree contains custom_components/goecharger/manifest.json.
HACS repository state was removed and recreated.
HACS was updated and restarted.
The same custom_components/None/manifest.json error still occurs.
```

Expected: The failure is now isolated to HACS behavior, not this repository's release tree.

- [ ] **Step 2: Install manually as the temporary recovery path**

Run on the Home Assistant host:

```bash
cd /tmp
curl -L https://github.com/cryptedx/homeassistant-goecharger/archive/refs/tags/v0.27.2.tar.gz -o homeassistant-goecharger-v0.27.2.tar.gz
tar -xzf homeassistant-goecharger-v0.27.2.tar.gz
mkdir -p /config/custom_components
rm -rf /config/custom_components/goecharger
cp -R /tmp/homeassistant-goecharger-0.27.2/custom_components/goecharger /config/custom_components/goecharger
test -f /config/custom_components/goecharger/manifest.json
```

Expected: The integration exists at `/config/custom_components/goecharger/manifest.json`.

- [ ] **Step 3: File a HACS upstream issue with evidence**

Include:

```text
Repository: cryptedx/homeassistant-goecharger
Version: v0.27.2
Observed error: No manifest.json file found 'custom_components/None/manifest.json'
GitHub tree evidence: custom_components/goecharger/manifest.json exists in v0.27.2
HACS version:
Whether HACS storage contained custom_components/None:
```

Expected: Upstream has enough evidence to distinguish a HACS path/cache bug from a repository packaging bug.

---

## Verification Checklist

- [ ] HACS storage no longer contains `custom_components/None` for `cryptedx/homeassistant-goecharger`.
- [ ] HACS download of `v0.27.2` completes, or manual recovery installs the same release.
- [ ] `/config/custom_components/goecharger/manifest.json` exists.
- [ ] The manifest contains `"domain": "goecharger"`.
- [ ] Home Assistant was restarted after installation.
- [ ] This repository remains clean unless a later task explicitly changes docs or code.

---

## Explicitly Skipped

- Skipped adding `custom_components/None` to this repository. Add only if HACS maintainers confirm that a repository-side compatibility mirror is required.
- Skipped more release bumps. The published `v0.27.2` tag already contains the correct manifest path.
- Skipped changing `hacs.json` again without new evidence. Current HACS metadata is minimal and valid.
