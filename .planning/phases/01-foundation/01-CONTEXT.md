# Phase 1: Foundation - Context

**Gathered:** 2026-05-16 **Status:** Ready for planning

<domain>
## Phase Boundary

An installable HA custom integration that loads without errors, auto-discovers
climate entities and persons from the HA registries, persists sparse
configuration (only non-default values) across restarts, and can issue the
correct two-call TRV service sequence. No UI panel, no scheduling logic —
foundation only.

</domain>

<decisions>
## Implementation Decisions

### Project Scaffold

- **D-01:** Start from `ludeeus/integration_blueprint` as the structural
  reference — correct file layout, pytest scaffold. Strip GitHub Actions CI and
  anything not needed for local development.
- **D-02:** Flat repo layout — `custom_components/climate_manager/` at the repo
  root alongside `.planning/`, `specs.md`, and `frontend/` (future).
- **D-03:** No GitHub Actions CI in Phase 1 — no publishing planned; CI adds
  friction with no benefit yet.

### Config Flow

- **D-04:** Minimal config flow — single step, pre-filled integration name, user
  clicks Submit. All real configuration is in the panel (Phase 3).
- **D-05:** Single instance only — `async_setup` must reject a second
  installation attempt. One climate manager per HA instance.

### Dev Toolchain

- **D-06:** `Makefile` for deploy workflow — `make deploy` runs rsync to copy
  `custom_components/climate_manager/` to the HA host, then SSH-restarts HA with
  `ha core restart`.
- **D-07:** HA restart triggered via SSH (`ha core restart`) — works with HA OS
  / supervised.
- **D-08:** `pytest` from day one using `pytest-homeassistant-custom-component`
  — set up the test harness in Phase 1 even if only a smoke test (integration
  loads without errors). Incremental test addition in Phase 2 is easier from an
  existing scaffold.

### Storage Schema

- **D-09:** Define the **full schema** in Phase 1 — rooms, persons, global
  config, time programs, period temperatures. Phase 2 reads/writes to this
  schema without changes.
- **D-10:** Schema **version field** from day one: `{ "version": 1, ... }`.
  Enables safe migration if schema changes later.
- **D-11:** **Sparse storage** — only store values that differ from defaults. If
  a room uses the global time program → nothing stored for that room. If global
  mode is at its default → nothing stored. Storage is the delta from defaults,
  not the full state.

### Discovery Model

- **D-12:** **Rooms are auto-discovered**, not manually configured. On startup:
  query the entity registry for all `climate.*` entities → look up each entity's
  `area_id` → each HA area with at least one climate entity becomes a managed
  room. Areas with no climate entities are ignored.
- **D-13:** **Room ID = HA `area_id`** from the area registry. Stable,
  human-readable, already exists in HA. The user's HA area definitions are the
  source of truth for room identity.
- **D-14:** **Persons are auto-discovered** using the same pattern. Query the
  entity registry for all `person.*` entities → all become managed persons by
  default with default settings.
- **D-15:** **Person ID = `person.*` entity_id** (e.g., `person.john`). Stable
  identifier from the HA person registry.
- **D-16:** No explicit opt-in for rooms or persons — all discovered entities
  are managed. Non-default config is stored; default = nothing stored.

### UI Tab Ordering (scoped decision for Phase 3 but locked now)

- **D-17:** **Rooms tab** — rooms with non-default configuration (custom time
  program) listed first; unconfigured rooms (inheriting global) listed after.
- **D-18:** **Persons tab** — persons with any non-default setting listed first;
  fully-default persons listed after.

### Claude's Discretion

- Integration blueprint cleanup: which blueprint files to keep vs. remove is
  left to the planner/executor — keep what HA requires, strip CI and anything
  publishing-specific.
- Exact Makefile targets beyond `deploy`: additional targets (e.g., `make logs`,
  `make test`) are at the implementer's discretion.
- Storage file name: use standard `climate_manager` as the Store key (matches
  the domain).

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition

- `specs.md` — Full feature specification including definitions, period modes,
  time program structure, person presence modes, use cases
- `.planning/PROJECT.md` — Project context, key decisions (SSH deploy, no HACS
  publishing, heat mode only, sparse storage)
- `.planning/REQUIREMENTS.md` — 29 v1 requirements with REQ-IDs; Phase 1 scope:
  INFRA-01, INFRA-02, INFRA-04, ROOM-01, ROOM-02, ROOM-03

### Architecture & Stack

- `.planning/research/STACK.md` — Full technology stack: Python HA APIs,
  Lit/TS/Vite for frontend, two-layer storage pattern, climate entity service
  call sequence
- `.planning/research/ARCHITECTURE.md` — 5-layer architecture, component
  boundaries, data model, build order rationale
- `.planning/research/PITFALLS.md` — Critical pitfalls: blocking I/O (C5),
  HACS/HA structure (M1), ghost listeners on unload (M5)

### HA Developer References (external)

- HA Developer Docs: Config entries / Config flow / Options flow
- HA Developer Docs: `homeassistant.helpers.storage.Store`
- HA Developer Docs: Area registry (`homeassistant.helpers.area_registry`)
- HA Developer Docs: Entity registry (`homeassistant.helpers.entity_registry`)
- HA Developer Docs: Person domain / person registry
- `ludeeus/integration_blueprint` — scaffold reference (strip CI, keep
  structure)

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- None yet — greenfield project. No existing `custom_components/` directory.

### Established Patterns

- **Two-call TRV control** (from research): `climate.set_hvac_mode(heat)` →
  `climate.set_temperature(target)`. Never use auto mode. Both calls
  blocking=True.
- **Sparse storage pattern**: Store only deltas from defaults. Read defaults
  from constants; merge with stored overrides at runtime.
- **Discovery over configuration**: Use HA registries (area_registry,
  entity_registry, person registry) as the source of truth for what exists;
  storage only holds what was changed.

### Integration Points

- Phase 1 establishes the storage schema and discovery mechanism that Phase 2
  (scheduler + coordinator) will read at every evaluation cycle.
- The Makefile deploy target is the primary development loop for all subsequent
  phases.

</code_context>

<specifics>
## Specific Ideas

- **Deploy command:**
  `rsync -av custom_components/climate_manager/ user@ha-host:/config/custom_components/climate_manager/ && ssh user@ha-host "ha core restart"`
  — wrapped in `make deploy`.
- **Storage key:** `climate_manager` (matches integration domain).
- **Schema shape (draft):**
  ```json
  {
    "version": 1,
    "global_mode": "time_program",
    "period_temperatures": {
      "frost_protection": 7.0,
      "reduced": 18.0,
      "normal": 20.0,
      "comfort": 22.0
    },
    "global_time_program": { "weekday_groups": [] },
    "rooms": {
      "<area_id>": { "time_program": { "weekday_groups": [...] } }
    },
    "persons": {
      "person.<name>": { "mode": "present", "room_ids": ["<area_id>"], "schedule": { "weekday_groups": [] } }
    }
  }
  ```
  Only rooms/persons with non-default values appear in storage. If a room uses
  the global time program, it has no entry. If a person is at default
  (Automatic, empty schedule, no room associations), it has no entry.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-restart watcher** (e.g., watch for file changes and auto-deploy) — nice
  for rapid iteration but out of Phase 1 scope.
- **Frontend build step in Makefile** (`make build && make deploy`) — relevant
  in Phase 3 when the Lit panel exists.
- **`make logs` target** (tail HA logs via SSH) — convenience target, not needed
  for Phase 1 to succeed.

</deferred>

---

_Phase: 1-Foundation_ _Context gathered: 2026-05-16_
