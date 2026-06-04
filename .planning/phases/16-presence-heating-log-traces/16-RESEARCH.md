# Phase 16: Presence & Heating Log Traces - Research

**Researched:** 2026-06-04
**Domain:** Python domain-model refactor + structured logging (HA integration)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Name resolution — strip domain/prefix from all `<name>` fields in
  log lines. `person.alice` → `alice`; `area_kitchen` → `kitchen`;
  `zone_main` → `main`. No config display-name lookup at log time.

- **D-02:** `EvalContext` dataclass created once per `async_evaluate` call.
  Replaces `_prefetch_calendars` pass. Fields: `now`, `hass`,
  `period_temperatures`, `_calendar_cache`, `_presence_cache`. Calendar events
  fetched on demand via `ctx.calendar_events(entity_id)`.

- **D-03:** Zone state log captures both period AND mode.
  Format: `state=<old_period>[<old_mode>]→<new_period>[<new_mode>]`.

- **D-04:** `zone.py` — `ZoneMode` plain base class (not ABC). Unimplemented
  overloads use `assert False`. `ZoneMode.__init__` takes
  `weakref.ref[Zone]`. No config on ZoneMode — reads `zone.*` at call time.
  Concrete subclasses: `ZoneModeOff`, `ZoneModeTimeProgram`,
  `ZoneModeProgramPresences`.

- **D-05:** `person.py` — `PersonMode` plain base class (not ABC). Same
  weakref pattern. Concrete subclasses: `PersonModeScheduled`,
  `PersonModeHA`, `PersonModeCalendar`, `PersonModeForcePresent`,
  `PersonModeForceAbsent`.

- **D-06:** `room.py` — `Room` plain class (no state machine). Owns TRV
  groups, preheat state, calibration state. `Room.apply_setpoint(period,
  temp, ctx)` pushes to all TRVGroup instances.

- **D-07:** `trv.py` extended with `TRVGroup`. One `TRVGroup` = one logical
  push unit assembled at init from `matter_mappings`. No platform branching at
  push time. `TRV.push_temperature(temp, *, room_name, zone_name, slot, ctx)`
  owns anti-flap guard and DEBUG log.

- **D-08:** Five modules: `eval_context.py` (or inline in coordinator),
  `zone.py`, `person.py`, `room.py`, `trv.py`. Presence log `reason=<source>`
  is mode name only: `scheduled`, `ha`, `calendar`, `force_present`,
  `force_absent`.

- **D-09:** `coordinator.async_evaluate()` refactored to:
  `ctx = EvalContext(...)`, zone loop, preheat/calibration per-room pass.
  Zone log `reason=<why>`: trigger + detail, e.g.
  `reason=time_program:normal→22:00`.

- **D-10:** Anti-spam driven by domain object state — no separate log-state
  dict. Zone: `_current_mode`/`_current_period`. Person: `_last_home`. TRV:
  `last_pushed`.

- **D-11:** TRV heating DEBUG log fires only when `last_pushed != desired_temp`.
  Startup push fires (intentional).

### Claude's Discretion

None stated in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

- Multi-language support
- Boiler demand control
- Per-zone boiler declaration
- Full state machine for WS API handlers
- Frontend changes
- WebSocket API contract changes
- New heating logic
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID     | Description                                                                 | Research Support                                                                                             |
|--------|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| OBS-01 | Structured INFO log on presence transitions and zone state changes; DEBUG on each TRV set_temperature call; no duplicate lines for repeated identical states | Python `logging` module per-module loggers; anti-spam via domain object state fields; log format strings locked in CONTEXT.md |
</phase_requirements>

---

## Summary

Phase 16 is a structural refactor of `coordinator.py` into five focused domain
modules (`eval_context.py`, `zone.py`, `person.py`, `room.py`, `trv.py`),
with the primary observable output being three families of structured log
lines. The heating logic itself does not change — only the code organisation
and the addition of logging at well-defined state transition points.

The refactor is additive in the sense that no existing test contracts are
broken: the WS API payloads, storage schema, and TRV push behaviour remain
identical. All tests that currently mock `coordinator.*` internals (dict
access) will need updating to mock domain object methods, but the test
scenarios (push-on-change, anti-flap, mode-off, zone evaluation) are fully
preserved.

The most important risk is ensuring the domain objects are wired together
correctly at coordinator `__init__` time — any mismatch in the weakref chain
or `TRVGroup` assembly produces a runtime `AssertionError` rather than a
silent failure (by design).

**Primary recommendation:** Build the five modules in dependency order
(`eval_context.py` → `trv.py` → `room.py` → `person.py` → `zone.py` →
coordinator refactor), writing unit tests for each module before integrating,
then replace the coordinator internals in a single final wave.

---

## Architectural Responsibility Map

| Capability                       | Primary Tier       | Secondary Tier | Rationale                                                       |
|----------------------------------|--------------------|----------------|-----------------------------------------------------------------|
| Presence evaluation              | `person.py`        | `coordinator`  | PersonMode subclasses own presence resolution per mode          |
| Zone heating state              | `zone.py`          | `coordinator`  | ZoneMode subclasses own period evaluation and state tracking     |
| TRV temperature push            | `trv.py`           | `room.py`      | TRV owns anti-flap guard, push call, and DEBUG log              |
| Per-cycle shared cache           | `eval_context.py`  | —              | EvalContext is created once per cycle and passed down           |
| Preheat / calibration state     | `room.py`          | `coordinator`  | Room owns both state dicts migrated from coordinator            |
| Log emission (presence INFO)    | `person.py`        | —              | Person.evaluate() logs on `_last_home` flip                     |
| Log emission (zone INFO)        | `zone.py` / `ZoneMode` | —          | ZoneMode.evaluate() logs on `_current_period` change            |
| Log emission (heating DEBUG)    | `trv.py`           | —              | TRV.push_temperature logs only when setpoint changes            |
| Coordinator orchestration        | `coordinator.py`   | —              | Instantiates and delegates; no domain logic remains             |

---

## Standard Stack

No new packages are introduced by this phase. All tools are from the Python
standard library or HA core.

### Core
| Library              | Version   | Purpose                          | Why Standard         |
|----------------------|-----------|----------------------------------|----------------------|
| `logging`            | stdlib    | Per-module logger (`_LOGGER`)    | Established pattern  |
| `dataclasses`        | stdlib    | `EvalContext` dataclass          | Already used in `__init__.py` |
| `weakref`            | stdlib    | `ZoneMode`/`PersonMode` → owner  | Avoids reference cycles |
| `from __future__ import annotations` | stdlib | Forward references in all new modules | Established pattern in coordinator |

### No External Packages

This phase installs nothing from npm, PyPI, or any external registry.
The `## Package Legitimacy Audit` section is omitted — no packages to audit.

---

## Architecture Patterns

### System Architecture Diagram

```
async_evaluate() called every 60s
        │
        ▼
EvalContext(now, hass, period_temperatures)
        │
        ├──► for zone in zones:
        │         Zone.evaluate(ctx)
        │              │
        │              ▼
        │         ZoneMode.evaluate(ctx)     [ZoneModeOff | ZoneModeTimeProgram | ZoneModeProgramPresences]
        │              │
        │              │  ZoneModeProgramPresences only:
        │              ├──► Person.evaluate(ctx)  → checks ctx._presence_cache
        │              │        │                    → PersonMode.is_present(ctx)
        │              │        └──► logs INFO: "presence | person=<name> home=<bool> reason=<source>"
        │              │
        │              ├──► [zone period change detected]
        │              │        └──► logs INFO: "zone | zone=<name> state=<old>→<new> reason=<why>"
        │              │
        │              └──► Room.apply_setpoint(period, temp, ctx)
        │                        │
        │                        └──► TRVGroup.push(temp, slot, ctx)
        │                                  │
        │                                  └──► TRV.push_temperature(temp, ...)
        │                                            │  [anti-flap: last_pushed == temp → skip]
        │                                            └──► logs DEBUG: "heating | room=<name> temp=<T>°C zone=<zone> slot=<slot>"
        │
        ├──► for room in rooms:
        │         room.compute_preheat(ctx)
        │         room.calibrate_trvs(ctx)
        │
        └──► fire DOMAIN_status_update event
```

### Recommended Project Structure

```
custom_components/climate_manager/
├── eval_context.py    # EvalContext dataclass — per-cycle shared cache
├── zone.py            # Zone + ZoneMode + concrete subclasses
├── person.py          # Person + PersonMode + concrete subclasses
├── room.py            # Room (preheat, calibration, apply_setpoint)
├── trv.py             # TRV + TRVGroup (extended from existing trv.py)
├── coordinator.py     # Refactored: instantiates domain objects, delegates
├── const.py           # Unchanged
├── schedule.py        # Unchanged (called from PersonMode subclasses)
├── storage.py         # Unchanged
└── websocket.py       # Unchanged (WS handlers call zone.change_mode / person.change_mode)
```

### Pattern 1: Per-Module Logger

Every new module opens with:

```python
# Source: existing coordinator.py / schedule.py pattern
_LOGGER = logging.getLogger(__name__)
```

Each module gets its own logger namespace
(`climate_manager.zone`, `climate_manager.person`, etc.), allowing HA log
filtering per module.

### Pattern 2: EvalContext Dataclass

```python
# Source: D-02 from 16-CONTEXT.md (ASSUMED — new pattern, no prior code)
from dataclasses import dataclass, field
from datetime import datetime
from homeassistant.core import HomeAssistant

@dataclass
class EvalContext:
    now: datetime
    hass: HomeAssistant
    period_temperatures: dict[str, float]
    _calendar_cache: dict[str, list] = field(default_factory=dict)
    _presence_cache: dict[str, bool] = field(default_factory=dict)

    async def calendar_events(self, entity_id: str) -> list:
        if entity_id not in self._calendar_cache:
            # fetch via hass.services.async_call("calendar", "get_events", ...)
            ...
        return self._calendar_cache[entity_id]
```

### Pattern 3: WeakRef-backed Mode Classes

```python
# Source: D-04/D-05 from 16-CONTEXT.md
import weakref

class ZoneMode:
    def __init__(self, zone: "Zone") -> None:
        self._zone_ref: weakref.ref["Zone"] = weakref.ref(zone)

    @property
    def zone(self) -> "Zone":
        z = self._zone_ref()
        assert z is not None, "Zone has been garbage-collected"
        return z

    def evaluate(self, ctx: EvalContext) -> None:
        assert False, f"{type(self).__name__}.evaluate() not implemented"
```

### Pattern 4: Structured Log Format

The three log formats are contracts — they must be matched exactly:

```python
# Source: ROADMAP.md Phase 16 success criteria / 16-CONTEXT.md specifics

# INFO — person presence flip (in person.py)
_LOGGER.info(
    "presence | person=%s home=%s reason=%s",
    person_name,   # short suffix only — "alice" not "person.alice"
    home,          # bool
    reason,        # "scheduled" | "ha" | "calendar" | "force_present" | "force_absent"
)

# INFO — zone state change (in zone.py or ZoneMode subclass)
_LOGGER.info(
    "zone | zone=%s state=%s→%s reason=%s",
    zone_name,     # short suffix — "main" not "zone_main"
    old_state,     # "<period>[<mode>]" e.g. "frost[time_program]"
    new_state,     # "<period>[<mode>]" e.g. "normal[time_program]"
    reason,        # "time_program:normal→22:00" | "user:time_program→off" | etc.
)

# DEBUG — TRV setpoint push (in trv.py TRV.push_temperature)
_LOGGER.debug(
    "heating | room=%s temp=%s°C zone=%s slot=%s",
    room_name,     # short suffix — "kitchen" not "area_kitchen"
    temp,          # float
    zone_name,     # short suffix
    slot,          # period name e.g. "normal" | "comfort"
)
```

### Pattern 5: Anti-spam via Domain State

No separate log-state tracking dict. Each domain object owns its last-state
fields:

```python
# Zone (zone.py): log fires when _current_period or _current_mode changes
if (period, mode_name) != (self._current_period, self._current_mode_name):
    # log INFO
    self._current_period = period
    self._current_mode_name = mode_name

# Person (person.py): log fires when _last_home flips
result = self._mode.is_present(ctx)
if result != self._last_home:
    # log INFO
self._last_home = result

# TRV (trv.py): log fires only when last_pushed != desired_temp
if last is not None and last == desired_temp:
    return  # no push, no log
# ... push ...
_LOGGER.debug(...)
self.last_pushed = desired_temp
```

### Pattern 6: TRVGroup Assembly at Init

`TRVGroup` is assembled once at coordinator `__init__` from `matter_mappings`
config. The platform-branching logic currently in `_push_temperatures` moves
into the assembly step, not into push time. At push time `TRVGroup.push`
iterates its pre-computed TRV list with no conditionals.

### Anti-Patterns to Avoid

- **Calling `zone.evaluate()` from coordinator per-room loop:** Zone.evaluate
  dispatches to all its rooms internally. The coordinator loop is per-zone,
  not per-room.
- **Storing config on ZoneMode or PersonMode:** Config lives on `Zone`/`Person`
  and is read through the weakref at call time. Modes are stateless except for
  the owner weakref.
- **Introducing ABC:** Both `ZoneMode` and `PersonMode` use `assert False`
  rather than `NotImplementedError` or `@abstractmethod`. The CONTEXT.md is
  explicit about this — ABC machinery is not used.
- **Logging inside `Zone.update_config()`:** This is a plain config setter for
  WS config changes, not a state transition. No log.
- **Duplicate presence evaluation for multi-zone persons:** `Person.evaluate`
  must check `ctx._presence_cache` first. Without this, a person assigned to
  rooms in two different zones evaluates twice with potentially different
  results if state changes mid-cycle.

---

## Don't Hand-Roll

| Problem                   | Don't Build                        | Use Instead                                 | Why                                                          |
|---------------------------|------------------------------------|---------------------------------------------|--------------------------------------------------------------|
| Structured log format     | Custom log formatter / handler     | `_LOGGER.info("zone \| zone=%s ...", ...)` | Standard Python logging with format string is sufficient     |
| Per-cycle calendar cache  | Thread-local / global dict         | `EvalContext._calendar_cache`               | Already in coordinator; just moves into the context object   |
| Weak reference management | Manual `None` checks on every call | `weakref.ref` + assert in property          | `weakref` stdlib is purpose-built for this pattern           |
| Anti-flap state           | Separate `_log_state` dict        | Domain object fields (`_last_home`, etc.)   | Domain objects already own the relevant state                |

**Key insight:** All "infrastructure" for this phase already exists in the
coordinator — this phase moves and restructures code, adding three log lines
per transition. No new algorithms are introduced.

---

## Runtime State Inventory

This is a refactor phase, not a rename phase. The coordinator's in-memory dicts
are replaced by domain objects at init time, but the persistent storage schema
(Store, preheat_store, ConfigEntry) is unchanged.

| Category       | Items Found                                                              | Action Required                                      |
|----------------|--------------------------------------------------------------------------|------------------------------------------------------|
| Stored data    | `ClimateManagerStore` (v2 schema) + `preheat_store` — schema unchanged  | None — domain objects read same dict format          |
| Live service config | WS API commands unchanged — same payloads                          | None                                                 |
| OS-registered state | No OS-level registrations                                          | None                                                 |
| Secrets/env vars | No secrets reference integration-internal names                       | None                                                 |
| Build artifacts | No compiled artifacts for the Python backend                           | None                                                 |

**Nothing found requiring data migration** — the storage schema is a
read-only input to domain objects; the objects are reconstructed from it on
every `async_setup_entry`.

---

## Common Pitfalls

### Pitfall 1: Weak Reference GC Before First Use

**What goes wrong:** If `Zone` or `Person` is collected before a `ZoneMode`
method runs, the `assert z is not None` fires.

**Why it happens:** The coordinator holds the only strong reference. If the
coordinator dict goes out of scope or is replaced before domain objects are
used, the weakref becomes dead.

**How to avoid:** Ensure `self._zones` and `self._persons` dicts on the
coordinator are the single source of strong references. Never store domain
objects in temporary locals and then assign modes that live longer.

**Warning signs:** `AssertionError: Zone has been garbage-collected` in logs.

### Pitfall 2: EvalContext Calendar Fetch Timing

**What goes wrong:** `PersonModeCalendar.is_present(ctx)` calls
`ctx.calendar_events(entity_id)` which is `async`. If the method is called
from a synchronous context, the `await` is missed.

**Why it happens:** `is_present` is declared `async` in the CONTEXT.md design,
but callers (ZoneMode.evaluate → Person.evaluate → PersonMode.is_present)
must all be async.

**How to avoid:** Declare all `evaluate` and `is_present` methods `async`.
The `async_evaluate` call chain is already fully async in the coordinator.

**Warning signs:** `RuntimeWarning: coroutine was never awaited`.

### Pitfall 3: Zone Log State Initialisation

**What goes wrong:** On coordinator startup the `_current_period` and
`_current_mode_name` fields on `Zone` are `None`. The first evaluation always
logs (correct). But if the initial state is logged with `old_state=None` the
format string produces `None[None]→normal[time_program]` — ugly but harmless.

**Why it happens:** No prior state on first tick.

**How to avoid:** Handle `None` initial state explicitly in the zone log line
— either skip logging on the very first evaluation or represent the initial
`old_state` as a sentinel like `startup`.

**Warning signs:** `zone | zone=home state=None[None]→frost[time_program]` in
log output.

### Pitfall 4: TRVGroup Assembly — Matter Entity Dedup

**What goes wrong:** Without the `matter_entity_set` frozenset (currently in
`_push_temperatures`), a Matter entity that is already covered by a tado_x
mapping gets pushed twice — once as the tado_x mapping target, once as an
independent entity.

**Why it happens:** The entity list for a room contains both the tado_x entity
and the mapped Matter entity IDs.

**How to avoid:** The `matter_entity_set` dedup logic from
`_push_temperatures` (coordinator.py:526–529) must move verbatim into
`TRVGroup` assembly at init time. When assembling groups, skip any Matter
entity that already appears in a tado_x group's entity list.

**Warning signs:** Double `set_temperature` calls for the same physical TRV
in test output.

### Pitfall 5: `_last_pushed` dict Migration

**What goes wrong:** `_last_pushed` currently lives on the coordinator. After
refactor, `last_pushed` lives on each `TRV` object. If the coordinator still
references `self._last_pushed`, two sources of truth exist.

**Why it happens:** Coordinator and TRV both have the anti-flap guard logic
during the transition.

**How to avoid:** Remove `self._last_pushed` from coordinator entirely once
TRV objects own it. Any coordinator code referencing `_last_pushed` is dead
code after the refactor.

**Warning signs:** `AttributeError: ClimateManagerCoordinator has no
attribute '_last_pushed'` only if the old dict is referenced after removal.

### Pitfall 6: Person Presence Cache Key Collision

**What goes wrong:** `ctx._presence_cache` is keyed by `person_id` (the full
`person.*` entity_id string). If code uses the short name (suffix after
stripping `person.`) as the key, a person assigned to two zones evaluates
twice.

**Why it happens:** Name stripping for log display (D-01) vs. cache key must
use different representations.

**How to avoid:** Always key the presence cache by full `person_id`. Only
strip the prefix when constructing the log line `person=<name>` field.

### Pitfall 7: Test Mocking Strategy

**What goes wrong:** Existing coordinator tests mock `coordinator._last_pushed`
and `coordinator._compute_present_persons` directly. After the refactor these
internal methods no longer exist — tests that patch them will silently pass
without exercising the new code paths.

**Why it happens:** Tests were written against the monolithic coordinator.

**How to avoid:** Update affected tests to mock at the domain object boundary.
E.g., replace `coordinator._last_pushed[eid] = X` with
`trv_obj.last_pushed = X`. The test scenarios are unchanged; only the mock
target changes.

---

## Code Examples

Verified patterns from existing codebase:

### Name Stripping Helper (D-01)

```python
# Source: existing coordinator.py:1438 uses .removeprefix() for the same purpose
def _short_name(entity_id: str) -> str:
    """Strip domain/prefix for log display."""
    # person.alice → alice
    # area_kitchen → kitchen (strip area_ prefix)
    # zone_main → main (strip zone_ prefix)
    if "." in entity_id:
        return entity_id.split(".", 1)[1]
    # strip area_ / zone_ prefixes for area_id and zone_id
    for prefix in ("area_", "zone_"):
        if entity_id.startswith(prefix):
            return entity_id[len(prefix):]
    return entity_id
```

### Existing Anti-Flap Guard (moves into TRV.push_temperature)

```python
# Source: coordinator.py:1627-1668 (_push_if_changed) — verbatim move
last = self.last_pushed  # was: self._last_pushed.get(entity_id)
if isinstance(last, str):
    last = None
if last is not None and last == desired_temp:
    return
if last is not None:
    reported = state.attributes.get("temperature")
    if reported is not None and float(reported) != last:
        return  # manual override hold
# push
await set_trv_temperature(self._hass, entity_id, desired_temp)
self.last_pushed = desired_temp  # was: self._last_pushed[entity_id] = desired_temp
```

### Presence Mode String Mapping (D-08 reason field)

```python
# Source: const.py PRESENCE_* constants
_MODE_TO_REASON: dict[str, str] = {
    "scheduled":     "scheduled",
    "ha":            "ha",
    "calendar":      "calendar",
    "force_present": "force_present",
    "force_absent":  "force_absent",
}
```

---

## State of the Art

| Old Approach                         | Current Approach (Phase 16)             | When Changed | Impact                                              |
|--------------------------------------|-----------------------------------------|--------------|-----------------------------------------------------|
| Presence logic in coordinator methods | `PersonMode` subclasses in `person.py` | Phase 16     | Independently testable, single responsibility       |
| Zone eval inline in coordinator      | `ZoneMode.evaluate(ctx)` in `zone.py`  | Phase 16     | Zone period change detection lives where state does |
| `_push_if_changed` on coordinator    | `TRV.push_temperature` in `trv.py`     | Phase 16     | Anti-flap and log co-located                        |
| `_calendar_cache` dict on coordinator | `EvalContext._calendar_cache`          | Phase 16     | Cache lifetime tied to single evaluation cycle      |
| Preheat dicts on coordinator          | Preheat state on `Room`               | Phase 16     | Room is the natural owner of per-room state         |

**No deprecated HA APIs are introduced or removed by this phase.**

---

## Assumptions Log

| # | Claim                                                                     | Section              | Risk if Wrong                                              |
|---|---------------------------------------------------------------------------|----------------------|------------------------------------------------------------|
| A1 | `_short_name` helper strips `area_` prefix to get human-readable room name | Code Examples        | Log lines would show `area_kitchen` instead of `kitchen`; low risk since format is internal |
| A2 | Zone log `old_state` on startup should use sentinel string rather than `None[None]` | Common Pitfalls | Low — cosmetic log output only; not a correctness issue |
| A3 | `PersonMode.is_present` and all `evaluate` methods must be declared `async` to support `PersonModeCalendar` | Architecture | If any mode is sync, calendar fetch via `await` fails at runtime |

---

## Open Questions

1. **Startup zone log — sentinel vs. silent skip**
   - What we know: On first `async_evaluate` call, `_current_period` on Zone
     is `None`. The log would emit `state=None[None]→frost[time_program]`.
   - What's unclear: Whether `None[None]` is acceptable in HA logs or should
     be replaced by `"startup"` sentinel or log suppressed on first tick.
   - Recommendation: Suppress the zone log on the very first evaluation
     (when `_current_period is None`). This is cleaner than `"startup"` and
     avoids polluting logs on every HA restart.

2. **`eval_context.py` as separate file vs. inline in coordinator**
   - What we know: CONTEXT.md says "in its own `eval_context.py` or at the
     top of `coordinator.py`".
   - What's unclear: Whether inline definition creates circular import risk
     when `zone.py`/`person.py` import from `coordinator.py`.
   - Recommendation: Separate `eval_context.py` file. This avoids the import
     cycle entirely (`zone.py` imports from `eval_context.py`, not
     `coordinator.py`).

3. **Coordinator `_last_pushed` cleanup**
   - What we know: `_last_pushed` must be fully removed from coordinator once
     TRV objects own it.
   - What's unclear: Whether any non-push code paths still reference
     `_last_pushed` after the refactor (e.g., MODE_OFF sentinel `"off"`).
   - Recommendation: Grep for `_last_pushed` at the start of the coordinator
     refactor wave; all references must be replaced by `trv.last_pushed`.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is a pure Python backend refactor. No external
tools, services, CLIs, or new packages are required beyond the existing
`pytest-homeassistant-custom-component` test harness already installed.

---

## Validation Architecture

### Test Framework

| Property         | Value                                                          |
|------------------|----------------------------------------------------------------|
| Framework        | pytest + pytest-homeassistant-custom-component (installed)     |
| Config file      | `pytest.ini` / `pyproject.toml` (existing)                    |
| Quick run command | `make test`                                                   |
| Full suite command | `make test`                                                  |

**Baseline:** 249 tests pass as of this research date.

### Phase Requirements → Test Map

| Req ID | Behavior                                                         | Test Type  | Automated Command                                   | File Exists?      |
|--------|------------------------------------------------------------------|------------|-----------------------------------------------------|-------------------|
| OBS-01 | INFO log emitted on person presence flip                         | unit       | `make test` (new test in test_person.py)            | No — Wave 0 gap   |
| OBS-01 | INFO log emitted on zone state change                           | unit       | `make test` (new test in test_zone.py)              | No — Wave 0 gap   |
| OBS-01 | DEBUG log emitted on TRV push (when setpoint changes)           | unit       | `make test` (new test in test_trv.py)               | No — Wave 0 gap   |
| OBS-01 | No duplicate log on repeated identical state                    | unit       | `make test` (anti-spam tests in test_person/zone/trv) | No — Wave 0 gap |
| OBS-01 | Full integration: async_evaluate produces correct log output    | integration | `make test` (new test in test_coordinator.py)       | Partial           |

### Sampling Rate

- **Per task commit:** `make test`
- **Per wave merge:** `make test` (full suite, 249+ tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_eval_context.py` — covers EvalContext calendar cache
  (on-demand fetch, deduplicated across callers)
- [ ] `tests/test_zone.py` — covers Zone/ZoneMode state machine, INFO log
  emission on period change, anti-spam (no duplicate on same period)
- [ ] `tests/test_person.py` — covers Person/PersonMode presence evaluation,
  INFO log emission on `_last_home` flip, presence cache dedup
- [ ] `tests/test_room_domain.py` — covers Room.apply_setpoint, preheat/
  calibration state delegation (note: `test_preheat.py` already covers the
  coordinator preheat path; domain test covers the Room object directly)
- [ ] Extended `tests/test_trv.py` — covers TRVGroup assembly, anti-flap
  guard on `TRV.push_temperature`, DEBUG log emission, startup push fires
- [ ] Updated `tests/test_coordinator.py` — update mocks from dict-access to
  domain object methods; no new scenarios, just mock target changes

*(Existing `test_preheat.py`, `test_schedule.py`, `test_calendar.py` need
no structural changes — they test coordinator-level behaviour and
schedule/calendar pure functions that are unchanged.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category       | Applies | Standard Control                                    |
|---------------------|---------|-----------------------------------------------------|
| V2 Authentication   | no      | No auth logic changed                               |
| V3 Session Management | no    | No session logic changed                            |
| V4 Access Control   | no      | WS API unchanged                                    |
| V5 Input Validation | yes     | `entity_id` calendar validation already in EvalContext.calendar_events (inherited from coordinator._prefetch_calendars T-11-03) |
| V6 Cryptography     | no      | No crypto                                           |

**Inherited security controls:** The `calendar.*` entity_id prefix check from
T-11-03 moves into `EvalContext.calendar_events` — the validation boundary
shifts but the rule is preserved.

**Log injection risk:** Log lines contain user-controlled values (entity IDs,
zone names). Python's `%s` formatting does not prevent log injection, but HA
logs are local files; this is not an exploitable attack surface. No change
needed.

---

## Sources

### Primary (HIGH confidence)

- Existing `coordinator.py` (lines 1627–1668) — `_push_if_changed` verbatim
  move pattern [VERIFIED: codebase read]
- Existing `coordinator.py` (lines 1316–1377) — `_compute_present_persons`
  → PersonMode subclass mapping [VERIFIED: codebase read]
- `const.py` — PRESENCE_* constant string values (`"scheduled"`, `"ha"`,
  `"calendar"`, `"force_present"`, `"force_absent"`) [VERIFIED: codebase read]
- `__init__.py` — existing `@dataclass` usage confirms pattern is established
  [VERIFIED: codebase read]
- `16-CONTEXT.md` — all design decisions D-01..D-11 [VERIFIED: codebase read]
- Python stdlib `weakref` module — confirmed available (Python 3.14.4 on
  target machine) [VERIFIED: runtime check]

### Secondary (MEDIUM confidence)

- ROADMAP.md Phase 16 success criteria — exact log format strings
  [CITED: .planning/ROADMAP.md]
- REQUIREMENTS.md OBS-01 — anti-spam and log level requirements
  [CITED: .planning/REQUIREMENTS.md]

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new packages; all tools verified in codebase
- Architecture: HIGH — domain design locked in CONTEXT.md D-01..D-11
- Code patterns: HIGH — verbatim from existing coordinator.py
- Pitfalls: MEDIUM — derived from reading the existing code; A2/A3 remain
  assumptions about edge behaviour

**Research date:** 2026-06-04
**Valid until:** 2026-07-04 (stable domain; no fast-moving dependencies)
