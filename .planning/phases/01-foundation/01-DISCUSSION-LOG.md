# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 1-Foundation
**Areas discussed:** Project scaffold, Config flow scope, Dev toolchain, Storage schema

---

## Project Scaffold

| Option | Description | Selected |
|--------|-------------|----------|
| Use integration_blueprint | Clone ludeeus/integration_blueprint — correct layout, pytest setup, hassfest CI action | ✓ |
| Build from scratch | Write manifest.json, __init__.py, config_flow.py manually | |

**User's choice:** Use integration_blueprint
**Notes:** Strip CI actions; keep file structure and pytest scaffold only.

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: custom_components/ at root | custom_components/climate_manager/ at repo root | ✓ |
| Src layout: src/custom_components/ | Non-standard for HA integrations | |

| Option | Description | Selected |
|--------|-------------|----------|
| Defer CI | No publishing planned — CI adds friction | ✓ |
| Set up CI now | Add hassfest + pytest workflow | |

---

## Config Flow Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal — just confirm | Single step, pre-filled name, click Submit | ✓ |
| Capture HA host info | Ask for hostname/IP for deploy script | |
| You decide | Keep it as simple as HA requires | |

| Option | Description | Selected |
|--------|-------------|----------|
| Single instance only | One climate manager per HA | ✓ |
| Allow multiple | Permit multiple instances | |

---

## Dev Toolchain

| Option | Description | Selected |
|--------|-------------|----------|
| Makefile | make deploy — rsync + SSH restart | ✓ |
| Shell script | scripts/deploy.sh | |
| You decide | Pick whichever is simpler | |

| Option | Description | Selected |
|--------|-------------|----------|
| SSH — ha core restart | SSH into HA host and run ha core restart | ✓ |
| HA REST API | POST /api/services/homeassistant/restart | |
| Manual restart | Deploy only, user restarts manually | |

| Option | Description | Selected |
|--------|-------------|----------|
| pytest from day one | Set up test harness in Phase 1 | ✓ |
| Defer tests | Add tests in Phase 2 | |

---

## Storage Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Full schema now | Define rooms, persons, global config in Phase 1 | ✓ |
| Minimal — rooms only | Extend schema in Phase 2 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — version field | { "version": 1, ... } | ✓ |
| Skip for now | Add versioning only when needed | |

**Room ID question:** User rejected UUID and slugified name options. Clarified that HA has an Area Registry with stable `area_id` values — use those as room IDs.

**Notes (freeform):**
- Auto-discovery model clarified during discussion: integration discovers all `climate.*` entities → groups by `area_id` → manages those areas automatically. Nothing manually configured.
- Sparse storage: only store values that differ from defaults. Default state = nothing in storage.
- Same pattern for persons: auto-discover all `person.*` entities, use `person.*` entity_id as person ID.
- UI ordering: rooms/persons with non-default config listed first in their respective tabs.

---

## Claude's Discretion

- Integration blueprint cleanup: which files to keep vs. strip
- Additional Makefile targets beyond `make deploy`
- Storage file name (decided: `climate_manager`, matches domain)

## Deferred Ideas

- Auto-restart file watcher for rapid dev iteration — out of Phase 1 scope
- `make build` frontend step — relevant in Phase 3 when Lit panel exists
- `make logs` SSH log tailing — convenience, not Phase 1 critical
