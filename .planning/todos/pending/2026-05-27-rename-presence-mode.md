---
created: 2026-05-27T00:00:00.000Z
title: Rename time_program_presences mode to a clearer identifier
area: general
files:
  - custom_components/climate_manager/const.py:24
---

## Problem

The global mode `time_program_presences` (const.py:24) is not self-explanatory.
It means: "run the weekly time program, but reduce heating for rooms whose associated
persons are all absent." This is a nuanced behaviour that the current name does not
convey — it sounds like a generic "presence mode" rather than a presence-modulated
time program.

Current mode identifiers:
- `off`
- `time_program`
- `time_program_presences`  ← unclear

The string is stored in config (HA Store), sent over WebSocket, and displayed in the
panel UI — so a rename touches backend, frontend, and migration.

## Solution

Candidate names (for discussion):

| Candidate | Meaning conveyed |
|-----------|-----------------|
| `time_program_presences` | current — ambiguous |
| `time_program_presence_aware` | schedule runs but adapts to who is home |
| `schedule_with_presence` | plain English, but long |
| `smart_schedule` | friendly, but too vague |
| `presence_schedule` | concise — "a schedule driven by presence" |
| `adaptive_schedule` | general, doesn't mention presence |

Recommended: `presence_schedule` — short, explicitly ties schedule to presence,
distinct from `time_program`. Open for review before committing.

**Migration concern**: the mode string is persisted in HA Store JSON. A rename
requires a one-time migration in `async_migrate_entry` or a Store migration
function to rewrite `"global_mode": "time_program_presences"` →
`"global_mode": "<new_name>"` on integration load. This is a breaking config
change → **major or minor version bump depending on whether migration is automatic**.
If migration is automatic and seamless, minor bump is acceptable.
