---
quick_id: 260529-d7e
slug: overview-all-persons-room-mode-off
status: complete
date: 2026-05-29
commit: 1a402cb
---

# Quick Task 260529-d7e: Overview all persons + room mode rename

**Overview tab — show all persons with presence status:**
- global-settings-tab.ts: replaced present-only list with all configured persons from `config.persons`; each person gets a colored dot (green = present, gray = absent) using a new `.person-dot.absent` CSS class
- Label changed from "Present persons:" to "Persons:"
- Fallback: "No persons configured" if config.persons is empty

**Room card — rename frost_protection display label to "Off":**
- room-card.ts: badge text `"Frost protection"` → `"Off"`
- room-card.ts: select option text `"Frost protection"` → `"Off"`
- Internal key `frost_protection` unchanged (backend compat preserved)
