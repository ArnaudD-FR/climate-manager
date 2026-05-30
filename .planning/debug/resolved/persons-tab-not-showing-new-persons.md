---
status: resolved
trigger: "Persons tab does not show new person.* entities added in Home Assistant"
created: 2026-05-30T00:00:00Z
updated: 2026-05-30T00:00:00Z
---

## Current Focus

hypothesis: persons-tab builds its list from config.persons (integration-stored
  config) only, never consulting hass.states for person.* entities — so new
  person entities added in HA are invisible until the backend explicitly learns
  about them
test: read persons-tab render() to confirm allPersonIds source
expecting: allPersonIds = Object.keys(this.config?.persons ?? {}) with no
  hass.states fallback
next_action: apply union fix — merge config.persons keys with
  Object.keys(hass.states).filter(k => k.startsWith('person.'))

## Symptoms

expected: Persons tab shows ALL person.* entities from hass.states, even those
  not yet configured in the integration
actual: Persons tab only shows persons that already have an entry in
  config.persons (the get_config WebSocket response)
errors: no runtime error — silent omission of unconfigured person entities
reproduction: add a new person.* entity in HA; open the Climate Manager panel;
  the new person does not appear in the Persons tab
started: always — by design the tab read config.persons only

## Eliminated

- hypothesis: reactivity issue — panel does not update when hass changes
  evidence: hass is a @property on both ClimateManagerPanel and PersonsTab, so
    Lit re-renders on hass change; the issue is the data source, not reactivity
  timestamp: 2026-05-30T00:00:00Z

- hypothesis: WebSocket subscription does not include person state
  evidence: persons list comes from config (get_config), not from
    subscribe_status — the bug is in the list-building logic, not the WS layer
  timestamp: 2026-05-30T00:00:00Z

## Evidence

- timestamp: 2026-05-30T00:00:00Z
  checked: frontend/src/components/persons-tab.ts render() lines 88-89
  found: |
    const persons = this.config?.persons ?? {};
    const allPersonIds = Object.keys(persons);
  implication: list is built exclusively from integration config; hass.states is
    never consulted for person.* entities

- timestamp: 2026-05-30T00:00:00Z
  checked: frontend/src/components/rooms-tab.ts render() lines 78-83
  found: |
    const statusRooms = (this.status?.rooms_status ?? []).filter(
      (r) => r.has_trv !== false,
    );
    const allRoomIds = new Set([...statusRooms.map((r) => r.area_id)]);
  implication: rooms tab already uses status (backend-discovered rooms), not
    config.rooms — so rooms are not affected by the same bug pattern; rooms are
    discovered correctly via the backend coordinator

- timestamp: 2026-05-30T00:00:00Z
  checked: frontend/src/types.ts Hass interface
  found: hass.states is typed as Record<string, {state, attributes}>
  implication: hass.states is available in PersonsTab (it receives hass as a
    @property); fix can read Object.keys(this.hass?.states ?? {}) and filter for
    'person.' prefix

## Resolution

root_cause: |
  PersonsTab.render() builds allPersonIds solely from
  `Object.keys(this.config?.persons ?? {})`. The config.persons map is only
  populated for persons the user has previously configured in the integration.
  New person.* entities added in Home Assistant are present in hass.states but
  never in config.persons, so they are permanently invisible in the Persons tab
  until manually added to the integration config.

fix: |
  In PersonsTab.render(), replace:
    const persons = this.config?.persons ?? {};
    const allPersonIds = Object.keys(persons);
  with a union that merges hass.states person.* keys with config.persons keys:
    const persons = this.config?.persons ?? {};
    const hassPersonIds = Object.keys(this.hass?.states ?? {}).filter(
      (k) => k.startsWith("person."),
    );
    const allPersonIds = [
      ...new Set([...hassPersonIds, ...Object.keys(persons)]),
    ];
  This ensures every known person.* entity appears, whether or not they have
  existing config. The personConfig lookup already falls back to {} for unknown
  persons (line 112: `const personConfig = persons[personId] ?? {};`).

verification: |
  make build passed (vite, 31 modules, 152.89 kB output).
  make deploy deployed to homeassistant.local and restarted HA core.
  Fix confirmed correct: allPersonIds is now the union of hass.states person.*
  keys and config.persons keys. PersonConfig lookup falls back to {} for
  unconfigured persons (pre-existing line 112 guard).
files_changed:
  - frontend/src/components/persons-tab.ts
