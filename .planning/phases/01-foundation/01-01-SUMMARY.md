---
phase: 01-foundation
plan: "01"
subsystem: integration-scaffold
tags: [manifest, constants, schema, makefile, dev-toolchain]
dependency_graph:
  requires: []
  provides: [DOMAIN, STORAGE_KEY, STORAGE_VERSION, DEFAULT_CONFIG, PLATFORMS, manifest.json, Makefile, dev-venv]
  affects: [02-config-flow, 03-storage, all-phase-1-plans]
tech_stack:
  added:
    - pytest-homeassistant-custom-component 0.13.195 (test harness)
    - Python 3.12.13 (uv-managed dev venv)
  patterns:
    - sparse-storage-schema (DEFAULT_CONFIG with empty rooms/persons dicts)
    - manifest-single-config-entry (HA-level single-instance gate)
key_files:
  created:
    - custom_components/climate_manager/manifest.json
    - custom_components/climate_manager/hacs.json
    - custom_components/climate_manager/__init__.py
    - custom_components/climate_manager/const.py
    - Makefile
    - pyproject.toml
    - .gitignore
  modified: []
decisions:
  - "Flat layout: custom_components/climate_manager/ at repo root alongside .planning/ (D-02)"
  - "single_config_entry: true in manifest.json for HA-level single-instance gate (D-05, Pitfall 5)"
  - "Sparse DEFAULT_CONFIG: rooms={}, persons={} — only non-default values stored (D-11)"
  - "Period mode constants as strings (frost_protection, reduced, normal, comfort) for JSON-safe serialization"
  - "pyproject.toml version field added to satisfy uv/PEP 621 requirement (auto-fix, Rule 3)"
metrics:
  duration: "~12 minutes"
  completed_date: "2026-05-16"
  tasks_completed: 3
  files_created: 7
  files_modified: 0
---

# Phase 1 Plan 01: Integration Scaffold Summary

**One-liner:** HACS-compatible HA integration skeleton with manifest, full v1 storage schema constants, Makefile rsync/SSH deploy loop, and Python 3.12 dev venv.

## What Was Built

A complete loadable (but not yet wired) Home Assistant custom integration scaffold for the Climate Manager. This establishes the contracts that all subsequent plans in Phase 1 depend on: DOMAIN, STORAGE_KEY, STORAGE_VERSION, DEFAULT_CONFIG, PLATFORMS, and the dev toolchain.

## Commits

| Task | Description | Hash |
|------|-------------|------|
| Task 1 | Integration directory: manifest.json, hacs.json, __init__.py | b5c6d31 |
| Task 2 | const.py with full v1 schema and defaults | 852097d |
| Task 3 | Makefile, pyproject.toml, .gitignore, dev venv | bb423c7 |

## Files Created

| File | Purpose |
|------|---------|
| `custom_components/climate_manager/manifest.json` | HACS-quality HA integration manifest (single_config_entry, config_flow, local_push, no PyPI deps) |
| `custom_components/climate_manager/hacs.json` | HACS name declaration — no zip_release (publishing out of scope for v1) |
| `custom_components/climate_manager/__init__.py` | Integration entry point placeholder with PLATFORMS = [] |
| `custom_components/climate_manager/const.py` | All domain constants + full v1 storage schema (DEFAULT_CONFIG) |
| `Makefile` | deploy (rsync + ssh ha core restart), test (.venv/bin/python -m pytest), logs targets |
| `pyproject.toml` | asyncio_mode=auto for pytest, requires-python >=3.12 |
| `.gitignore` | Excludes .venv/, __pycache__/, *.pyc, .pytest_cache/ |

## Verification Results

All plan verification commands passed:
- `manifest.json` parsed as valid JSON with required fields asserted
- `const.py` imports standalone (no HA dependency); `json.dumps(DEFAULT_CONFIG)` succeeds
- `make -n deploy` prints the expected `rsync --delete` + `ssh ha core restart` sequence
- `.venv/bin/python -c "import pytest_homeassistant_custom_component"` succeeds

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] pyproject.toml missing version field**
- **Found during:** Task 3 (uv venv creation)
- **Issue:** uv emitted a warning: `pyproject.toml is using the [project] table, but the required project.version field is neither set nor present in the project.dynamic list`. This is a PEP 621 compliance issue that would surface as a warning on every uv operation.
- **Fix:** Added `version = "1.0.0"` to the `[project]` table in pyproject.toml.
- **Files modified:** `pyproject.toml`
- **Commit:** bb423c7

## Known Stubs

None — this is a scaffold plan. `PLATFORMS = []` and `DEFAULT_CONFIG` with empty dicts are intentional sparse-start states, not stubs. Plan 02 (config flow) and plan 03 (storage + setup_entry) will wire the integration logic.

## Threat Surface

T-01-01 mitigation applied: Makefile deploy target uses `HA_COMPONENT_DIR = /config/custom_components/climate_manager` — rsync `--delete` is scoped to the integration subdirectory only, not the parent `/config` directory.

No new threat surface beyond what the plan's `<threat_model>` captured.

## Self-Check: PASSED

- `custom_components/climate_manager/manifest.json` — FOUND
- `custom_components/climate_manager/hacs.json` — FOUND
- `custom_components/climate_manager/__init__.py` — FOUND
- `custom_components/climate_manager/const.py` — FOUND
- `Makefile` — FOUND
- `pyproject.toml` — FOUND
- `.gitignore` — FOUND
- Commit b5c6d31 — FOUND
- Commit 852097d — FOUND
- Commit bb423c7 — FOUND
