---
quick_id: 260529-c5d
slug: factorize-css-styles
status: complete
date: 2026-05-29
commit: 1ff0660
---

# Quick Task 260529-c5d: Factorize CSS styles

**Created `frontend/src/shared-styles.ts`** with four exported Lit CSSResult fragments:
- `chipStyles` — `.chips`, `.chip`, `.chip:hover`, `.chip ha-icon`, `.chip-remove`, `.chip-remove:hover`, `.chip-add`, `.chip-add:hover`, `.chip-add ha-icon`
- `sectionLabelStyles` — `.section-label` (base: margin-bottom: 8px)
- `selectStyles` — `.mode-select`, `.mode-select:focus`
- `expandIconStyles` — `.expand-icon`, `.expand-icon.expanded`

**Updated components** to use `static styles = [shared..., css`local`]`:
- `room-card.ts` — uses chipStyles, sectionLabelStyles, selectStyles, expandIconStyles; removed ~80 CSS lines
- `person-card.ts` — uses chipStyles, sectionLabelStyles, selectStyles, expandIconStyles; adds `margin-top: 12px` local override for section-label; removed ~80 CSS lines
- `zone-tab.ts` — uses chipStyles, sectionLabelStyles, selectStyles; `.section-divider` retains only `margin: 16px 0 8px` (element is always empty); removed ~70 CSS lines

**Result**: 408 lines removed from components, bundle -5 KB.
