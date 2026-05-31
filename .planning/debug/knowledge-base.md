---
status: resolved
---

# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern
hypotheses at the start of new investigations.

---

## persons-tab-not-showing-new-persons — PersonsTab omits hass.states persons not yet in config
- **Date:** 2026-05-30
- **Error patterns:** persons tab, person entity, hass.states, config.persons, discovery, new person, missing person
- **Root cause:** PersonsTab.render() built allPersonIds from Object.keys(config.persons) only; new person.* entities present in hass.states but absent from config.persons were never displayed
- **Fix:** Union hass.states person.* keys with config.persons keys so all HA-known persons appear regardless of integration config state
- **Files changed:** frontend/src/components/persons-tab.ts
---
