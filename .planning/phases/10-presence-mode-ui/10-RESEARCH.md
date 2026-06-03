# Phase 10: Presence Mode UI — Research

**Researched:** 2026-05-31
**Domain:** Lit 3 / TypeScript frontend — conditional option rendering,
prop forwarding, label rename
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Every UI surface showing "HA", "HA home tracking", or similar
  replaces with **"Live tracking"**. Affected surfaces:
  - `<option>` label in the mode `<select>` (person-card.ts line 514)
  - Badge text in `_getBadgeInfo()` (person-card.ts line 442)
  - Hint paragraph below the select (person-card.ts lines 535-536)
  - The internal constant `PRESENCE_MODE_HA = "ha"` stays unchanged.

- **D-02:** Frontend-only check — no backend changes. `PersonsTab` computes
  `hasDeviceTrackers: boolean` per person by reading
  `hass.states[personId]?.attributes?.device_trackers`. Check:
  `(arr?.length ?? 0) > 0`.

- **D-03:** `PersonsTab` passes `hasDeviceTrackers` as a new boolean prop to
  `<climate-manager-person-card>`. `PersonCard` declares
  `@property({ type: Boolean }) hasDeviceTrackers = false;`.

- **D-04:** When `hasDeviceTrackers` is `false` (or person entity absent from
  `hass.states`), the "Live tracking" `<option>` is not rendered. Three other
  options remain (Scheduled, Force Present, Force Absent).

- **D-05:** If a person has `mode: "ha"` in config but `hasDeviceTrackers` is
  `false`, `PersonCard` renders an inline warning below the select:
  `"Live tracking requires a device tracker linked to this person in HA."`
  No automatic `setPersonConfig` call fires on render.

### Claude's Discretion

None specified — all implementation decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Backend `has_device_tracker` flag in status payload — not needed, frontend
  checks `hass.states` directly.
- Auto-migrate persons stuck on "ha" mode — decided against; user must switch
  manually.
- Multi-language support — deferred to v2.
- Even/odd week presence scheduling — already shipped in Phase 7-8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID    | Description | Research Support |
|-------|-------------|-----------------|
| UI-01 | Hide "HA" presence mode option in mode picker for persons whose HA
person entity has no linked device trackers (`attributes.device_trackers` is
empty or absent) | `hass.states[personId]?.attributes?.device_trackers`
already accessible in `PersonsTab`; conditional Lit `html` template guard
is the correct pattern |
| UI-02 | Rename "HA" presence mode to "Live tracking" everywhere it appears in
the panel | Three string literals to update in person-card.ts; internal
`PRESENCE_MODE_HA = "ha"` constant unchanged |
</phase_requirements>

## Summary

Phase 10 is a small, self-contained frontend-only change to `PersonsTab` and
`PersonCard`. No backend code, no WebSocket protocol changes, no Python
changes, and no data migration are required.

The work divides into two tightly coupled tasks: (1) rename the label string
"HA home tracking" to "Live tracking" in three places within `person-card.ts`,
and (2) conditionally hide the `<option>` element for that mode when the HA
`person.*` entity has no linked device trackers.

The `hass.states` object is already available in `PersonsTab` (it reads it for
person entity discovery at lines 91-94). The pattern for forwarding a new prop
to `PersonCard` is already established: `.ws`, `.panel`, `.status`, and
`.autoExpand` are all forwarded in the same `.prop=${value}` pattern. Adding
`.hasDeviceTrackers=${boolean}` follows the identical mechanism.

**Primary recommendation:** Two-task plan — (1) label rename in person-card.ts,
(2) `hasDeviceTrackers` prop computation in persons-tab.ts + conditional
option rendering + stuck-mode warning in person-card.ts.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Label rename | Browser / Client | — | Pure UI string change in Lit
template; no data layer involved |
| Device-tracker presence check | Browser / Client | — | Reads `hass.states`
attribute already in scope; no backend call needed |
| Prop forwarding | Browser / Client | — | Lit `@property` decorator pattern;
parent passes, child consumes |
| Stuck-mode warning | Browser / Client | — | Conditional inline render in Lit
template; no toast, no WS call |

## Standard Stack

### Core (already installed — no new packages)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Lit | `^3` (locked in package.json) | Web component framework | PersonCard
and PersonsTab both extend LitElement |
| TypeScript | `^5` | Type safety | `@property({ type: Boolean })` decorator
pattern already used |
| Vite | `^5` | Build | `make build` invokes `cd frontend && npm run build` |

**No new packages are required for this phase.**

### Installation

```bash
# No new packages — existing node_modules are sufficient
make build
```

## Package Legitimacy Audit

> No new packages are installed in this phase. Section not applicable.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
hass.states["person.*"]
        |
        | .attributes.device_trackers (array | undefined)
        v
PersonsTab.render()
  └── compute hasDeviceTrackers: boolean per personId
        |
        | .hasDeviceTrackers=${bool}  (Lit property binding)
        v
PersonCard
  ├── @property hasDeviceTrackers = false
  ├── _getBadgeInfo() → badge text "Live tracking" (was "HA home tracking")
  ├── <select>
  │     ├── <option>Scheduled</option>
  │     ├── ${hasDeviceTrackers
  │     │       ? html`<option value="ha">Live tracking</option>`
  │     │       : ""}           ← D-04: conditional render
  │     ├── <option>Force Present</option>
  │     └── <option>Force Absent</option>
  └── <p class="schedule-hint">
        ├── mode===ha && hasDeviceTrackers
        │     → "Presence mirrors Home Assistant home/away tracking."
        ├── mode===ha && !hasDeviceTrackers             ← D-05: warning
        │     → "Live tracking requires a device tracker…"
        └── (other modes unchanged)
```

### Recommended Project Structure

No new files required. Changes are surgical edits to:

```
frontend/src/
├── components/
│   ├── person-card.ts     ← label rename + hasDeviceTrackers prop +
│   │                          conditional option + stuck-mode warning
│   └── persons-tab.ts     ← compute hasDeviceTrackers, pass to card
```

### Pattern 1: Lit Boolean Property Declaration

**What:** `@property({ type: Boolean })` allows parent to bind
`.hasDeviceTrackers=${boolExpr}` and the child receives it as a typed
boolean (not a string attribute).
**When to use:** Any time a parent needs to pass a true/false flag to a child
custom element.

```typescript
// Source: Lit 3 @property decorator — established pattern in this codebase
@property({ type: Boolean }) hasDeviceTrackers = false;
```

Default value of `false` is the safe fallback — if the prop is never set (or
the entity is absent), the "Live tracking" option is hidden.

### Pattern 2: Conditional Option Rendering in Lit

**What:** Use a ternary inside `html` to conditionally include an `<option>`
element. The established pattern in this codebase (from HA 2026.x
compatibility notes) is conditional render — not disable.

```typescript
// Source: CONTEXT.md D-04 + established pattern in this codebase
${this.hasDeviceTrackers
  ? html`
      <option
        value=${PRESENCE_MODE_HA}
        ?selected=${currentMode === PRESENCE_MODE_HA}
      >
        Live tracking
      </option>`
  : ""}
```

Do NOT use `:disabled` on the option — hiding is the decided behavior.

### Pattern 3: hass.states Attribute Access

**What:** `hass.states` is typed as
`Record<string, { state: string; attributes: Record<string, unknown> }>`.
The `device_trackers` attribute is an array of entity ID strings (or absent).

```typescript
// Source: types.ts Hass interface (verified in codebase)
const trackers = this.hass?.states[personId]?.attributes
  ?.device_trackers as string[] | undefined;
const hasDeviceTrackers = (trackers?.length ?? 0) > 0;
```

Cast to `string[] | undefined` is necessary because `attributes` is typed as
`Record<string, unknown>`.

### Pattern 4: Stuck-Mode Warning — schedule-hint class

**What:** The existing `.schedule-hint` CSS class (from `shared-styles.ts`)
is the correct vehicle for the inline warning. It renders at 12px, secondary
color, with 6px top and 12px bottom margin. No new CSS is needed.

```typescript
// Source: shared-styles.ts scheduleHintStyles (verified in codebase)
// Add this case to the schedule-hint paragraph's ternary chain:
currentMode === PRESENCE_MODE_HA && !this.hasDeviceTrackers
  ? "Live tracking requires a device tracker linked to this person in HA."
  : currentMode === PRESENCE_MODE_HA
    ? "Presence mirrors Home Assistant home/away tracking."
    : // ... rest of existing cases
```

### Anti-Patterns to Avoid

- **Disabling instead of hiding:** The `<option disabled>` approach was
  explicitly rejected (D-04). Remove the element from the DOM entirely.
- **Auto-calling setPersonConfig on render:** D-05 forbids silent WS calls
  when stuck mode is detected. Show warning only; user acts manually.
- **Adding a backend `has_device_tracker` flag:** Deferred — frontend
  `hass.states` check is sufficient and avoids a WS round-trip.
- **Changing `PRESENCE_MODE_HA = "ha"`:** This constant drives config
  storage and WS payloads. It must not be renamed.
- **Using `ha-select`:** Broken in HA 2026.x. The codebase already uses
  native `<select>` — do not regress.
- **Using `ha-textfield`:** Not relevant here, but a project memory note
  confirms it renders nothing in HA 2026.x.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Conditional DOM | Custom show/hide toggle | Lit template ternary | Lit
handles DOM diffing correctly; toggling `display:none` keeps a selected-but-
hidden option in the form value |
| Warning display | Toast notification | `.schedule-hint` paragraph | D-05
specifies inline text, not toast; toast is for save success/error feedback |
| Device tracker count | Separate WS command | `hass.states` attribute read |
`hass.states` is already in scope in `PersonsTab`; no new infrastructure
needed |

**Key insight:** Conditional option rendering in native `<select>` must use
DOM removal (not `display:none` or `disabled`) to prevent the hidden option
from being selected as the current value when the select re-renders.

## Runtime State Inventory

> Greenfield-adjacent patch phase — no renames, no migrations. Skipping.

## Common Pitfalls

### Pitfall 1: Stuck Selected Value

**What goes wrong:** If a person currently has `mode: "ha"` and
`hasDeviceTrackers` becomes `false`, the `<select>` will have no matching
`<option>` for its current value. Browsers silently pick the first option
visually, but the DOM `.value` still returns `"ha"` — creating an invisible
inconsistency.

**Why it happens:** Native `<select>` does not auto-reset its value when the
selected option is removed from the DOM.

**How to avoid:** This is precisely what D-05's stuck-mode warning addresses.
The warning is shown INSTEAD of silently resetting; the user manually changes
the mode. The `_onModeChange` handler fires only on explicit user interaction.

**Warning signs:** If tests check `select.value` after removing the "ha"
option, they may see "ha" still returned even though the option is gone.
Verify behavior in tests by simulating an explicit change event.

### Pitfall 2: Missing `?selected` Binding on the Conditional Option

**What goes wrong:** If the conditional option is rendered (device trackers
present) but the `?selected` binding is missing, the select defaults to the
first option when the component re-renders — even if `currentMode === "ha"`.

**How to avoid:** Keep `?selected=${currentMode === PRESENCE_MODE_HA}` on the
conditionally rendered option, identical to the other options.

### Pitfall 3: Prop Type Mismatch

**What goes wrong:** Lit boolean properties set via `.hasDeviceTrackers=${0}`
or `.hasDeviceTrackers=${""}` evaluate to falsy in JS but Lit's `type: Boolean`
reflector can behave unexpectedly with string attributes vs. property bindings.

**How to avoid:** Always bind with the dot-prefix syntax
`.hasDeviceTrackers=${boolExpr}` (property binding), never as an HTML
attribute `hasdevicetrackers`. The `.` prefix ensures Lit skips attribute
reflection and sets the JS property directly.

### Pitfall 4: `hass.states` Cast

**What goes wrong:** `attributes` is typed as `Record<string, unknown>` in
`types.ts`. Accessing `.device_trackers` without a cast yields `unknown`,
and calling `.length` on `unknown` is a TypeScript error.

**How to avoid:** Cast explicitly:
```typescript
const trackers = this.hass?.states[personId]
  ?.attributes?.device_trackers as string[] | undefined;
const hasDeviceTrackers = (trackers?.length ?? 0) > 0;
```

## Code Examples

### Verified: persons-tab.ts hasDeviceTrackers computation

```typescript
// Source: types.ts Hass interface (hass.states shape confirmed)
// Compute inside render() before the sortedIds.map() call:
const hasDeviceTrackersMap = new Map<string, boolean>();
for (const personId of allPersonIds) {
  const trackers = this.hass?.states[personId]
    ?.attributes?.device_trackers as string[] | undefined;
  hasDeviceTrackersMap.set(personId, (trackers?.length ?? 0) > 0);
}
```

Then inside the `.map()`:
```typescript
<climate-manager-person-card
  .personId=${personId}
  .personName=${personName}
  .config=${personConfig}
  .roomChoices=${roomChoices}
  .ws=${this.ws}
  .panel=${this.panel}
  .status=${this.status}
  .autoExpand=${this.expandPersonId === personId}
  .hasDeviceTrackers=${hasDeviceTrackersMap.get(personId) ?? false}
></climate-manager-person-card>
```

### Verified: person-card.ts label rename locations

Three string literals to change (exact current values confirmed by reading
source):

| Location | Line | Current value | New value |
|----------|------|--------------|-----------|
| `_getBadgeInfo()` | 442 | `"HA home tracking"` | `"Live tracking"` |
| `<option>` label | 514 | `HA home tracking` (text node) | `Live tracking` |
| schedule-hint | 536 | `"Presence mirrors Home Assistant home/away tracking."` | unchanged (hint text for when device tracker IS present) |

Note: The hint text at line 536 is the "normal" hint for when mode is "ha"
AND trackers are present. Only the badge text (line 442) and option label
(line 514) say "HA home tracking" — those are the two rename targets.

### Verified: person-card.ts stuck-mode warning insertion

Insert a new branch BEFORE the existing `currentMode === PRESENCE_MODE_HA`
branch in the schedule-hint ternary (lines 531-537):

```typescript
<p class="schedule-hint">
  ${currentMode === PRESENCE_MODE_FORCE_PRESENT
    ? "Always considered present, regardless of schedule."
    : currentMode === PRESENCE_MODE_FORCE_ABSENT
      ? "Always absent. Rooms are not heated for presence."
      : currentMode === PRESENCE_MODE_HA && !this.hasDeviceTrackers
        ? "Live tracking requires a device tracker linked to this person in HA."
        : currentMode === PRESENCE_MODE_HA
          ? "Presence mirrors Home Assistant home/away tracking."
          : "Presence follows a weekly schedule."}
</p>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ha-select` | native `<select>` | HA 2026.x broke `ha-select` | All dropdowns use native select — do not regress |
| `ha-textfield` | native `<input>` | HA 2026.x broke `ha-textfield` | Not relevant for this phase |
| `paper-tab` / `ha-tabs` | CSS button tabs | HA 2026.x removed `ha-tabs` | PersonCard week-switcher already uses `.tab-btn` pattern |

## Assumptions Log

> All claims in this research were verified against the codebase source files
> or CONTEXT.md locked decisions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**If this table is empty:** All claims in this research were verified or cited
— no user confirmation needed.

## Open Questions

None — all implementation details are resolved by CONTEXT.md locked decisions
and verified codebase inspection.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend tests | ✓ | v25.9.0 | — |
| Python 3 | Backend tests | ✓ | 3.14.4 | — |
| make | Build/test | ✓ | system | — |
| Vite / npm | `make build` | ✓ (node_modules present) | vite ^5 | — |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:** none

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Node.js built-in test runner (`node:test`) |
| Config file | none — invoked directly |
| Quick run command | `node --test --experimental-strip-types frontend/src/components/week-parity.test.ts` |
| Full suite command | `make test` (Python) + `node --test --experimental-strip-types frontend/src/components/*.test.ts` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | "Live tracking" option hidden when no device trackers | unit | `node --test --experimental-strip-types frontend/src/components/person-card.test.ts` | ❌ Wave 0 |
| UI-01 | "Live tracking" option visible when device trackers present | unit | same | ❌ Wave 0 |
| UI-01 | Stuck-mode warning renders when mode=ha && !hasDeviceTrackers | unit | same | ❌ Wave 0 |
| UI-02 | Badge text is "Live tracking" when mode=ha | unit | same | ❌ Wave 0 |
| UI-02 | Option label is "Live tracking" | unit | same | ❌ Wave 0 |

**Note:** The existing `week-parity.test.ts` demonstrates the exact pattern:
`node --test --experimental-strip-types`. The new test file for PersonCard
should follow the same pattern — pure logic tests that do not require a
browser DOM (test `_getBadgeInfo()` and `hasDeviceTrackers` computation
directly as functions, or mock the Lit component minimally).

### Sampling Rate

- **Per task commit:** `node --test --experimental-strip-types frontend/src/components/person-card.test.ts`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `frontend/src/components/person-card.test.ts` — covers UI-01 and UI-02
  behavioral assertions (badge text, option visibility, stuck-mode warning)

*(Existing `week-parity.test.ts` is the reference implementation for test file
structure and invocation.)*

## Security Domain

> This phase makes no changes to authentication, session management, access
> control, input validation, or cryptography. All changes are UI label text
> and a conditional DOM render driven by read-only `hass.states` data.

ASVS categories V2-V6 do not apply to this phase.

## Sources

### Primary (HIGH confidence)

- `frontend/src/components/person-card.ts` — read in full; exact line numbers
  and string literals confirmed
- `frontend/src/components/persons-tab.ts` — read in full; `hass.states`
  access pattern confirmed at lines 91-94
- `frontend/src/types.ts` — `Hass` interface confirmed; `attributes:
  Record<string, unknown>` is the exact type
- `frontend/src/shared-styles.ts` — `scheduleHintStyles` confirmed; `.schedule-hint` class is the correct vehicle for the warning
- `.planning/phases/10-presence-mode-ui/10-CONTEXT.md` — all locked
  decisions verified against codebase

### Secondary (MEDIUM confidence)

- `frontend/src/components/week-parity.test.ts` — confirms test runner
  invocation pattern (`node --test --experimental-strip-types`)
- `frontend/package.json` — confirms Lit ^3, TypeScript ^5, no new deps
  needed

### Tertiary (LOW confidence)

None — all research findings are HIGH confidence from direct codebase
inspection.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — verified in package.json and existing source files
- Architecture: HIGH — locked decisions in CONTEXT.md match codebase patterns
- Pitfalls: HIGH — derived from direct source reading and Lit behavior
  knowledge
- Test plan: MEDIUM — test file does not exist yet; pattern confirmed from
  week-parity.test.ts

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (stable domain — Lit 3 and TypeScript 5 APIs
are stable)
