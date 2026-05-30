---
quick_id: 260528-tvl
slug: zone-color-palette
description: Reserve 5 colors for zones; each zone (default + custom) gets a deterministic color from the palette
date: 2026-05-28
files_modified:
  - frontend/src/types.ts
  - frontend/src/components/room-card.ts
  - frontend/src/main.ts
---

# Quick Task 260528-tvl: Zone Color Palette

Reserve 5 distinct colors for zones. The Default Zone always gets color 0 (violet, already used
in room badge CSS). Custom zones get a deterministic color based on a hash of their UUID, cycling
through all 5 palette colors. This means up to 5 custom zones each have a unique color; beyond 5
the palette wraps.

## Color palette (5 colors)

| Index | Color  | Hex     | BG (12% alpha)              | Border (25% alpha)            |
|-------|--------|---------|-----------------------------|-----------------------------|
| 0     | Violet | #7c3aed | rgba(124, 58, 237, 0.12)    | rgba(124, 58, 237, 0.25)    |
| 1     | Teal   | #0d9488 | rgba(13, 148, 136, 0.12)    | rgba(13, 148, 136, 0.25)    |
| 2     | Amber  | #d97706 | rgba(217, 119, 6, 0.12)     | rgba(217, 119, 6, 0.25)     |
| 3     | Sky    | #0284c7 | rgba(2, 132, 199, 0.12)     | rgba(2, 132, 199, 0.25)     |
| 4     | Rose   | #be123c | rgba(190, 18, 60, 0.12)     | rgba(190, 18, 60, 0.25)     |

## Task 1: Add ZONE_COLORS palette and getZoneColor() to types.ts

Add after existing exports:
- `ZONE_COLORS`: readonly array of 5 `{background, color, border}` objects
- `getZoneColor(zoneId: string | undefined)`: returns the color entry for the given zone ID
  - `undefined` or `"default"` → ZONE_COLORS[0] (violet)
  - custom zone UUID → deterministic hash mod 5 → ZONE_COLORS[hash % 5]

Hash algorithm: djb2-lite — `hash = (hash * 31 + charCode) >>> 0` over all chars.

## Task 2: Apply dynamic color to zone badge in room-card.ts

- Import `getZoneColor` from `../types.js`
- Replace hardcoded badge colors in `.zone-badge` CSS with just structural styles (no background/color/border)
- Add `_zoneBadgeStyle()` private method that returns an inline style string
- Change badge span to use `.style=${this._zoneBadgeStyle()}`

## Task 3: Add colored dot to zone tab buttons in main.ts

- Import `getZoneColor` from `./types.js`
- Add `.zone-dot` CSS (8px circle, inline-block, vertical-align middle, margin-right 6px)
- Prepend a `<span class="zone-dot" style="background:...color...">` to each zone tab button label
  (only when NOT in inline-editing mode, to avoid disrupting the input layout)
- Default Zone tab uses `getZoneColor("default").color`; custom zones use `getZoneColor(zoneId).color`
