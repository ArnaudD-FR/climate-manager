---
created: 2026-05-29T00:00:00
title: Add multi-language support
area: ui
files:
  - frontend/src/components/room-card.ts
  - frontend/src/components/zone-tab.ts
  - frontend/src/components/person-card.ts
  - frontend/src/components/global-settings-tab.ts
  - frontend/src/types.ts
status: deferred
deferred_to: v2 (i18n)
---

## Problem

All UI strings (section labels, mode descriptions, hints, badges, toasts) are
hardcoded in English. Users running HA in other languages have no localized
experience. The panel also uses string literals for period names
(`PERIOD_DISPLAY_NAMES` in types.ts) and mode option labels in selects.

## Solution

TBD — options to evaluate:

- HA's built-in translation system (`hass.localize` / `custom_translations`) for
  strings registered in `translations/en.json`
- A lightweight in-panel i18n map keyed by `hass.language`
- String extraction pass over all components into a single `strings.ts` catalog
  first, then wire up translations

Scope includes: section labels, mode option text, mode descriptions, hints,
toast messages, badge text, and `PERIOD_DISPLAY_NAMES`.
