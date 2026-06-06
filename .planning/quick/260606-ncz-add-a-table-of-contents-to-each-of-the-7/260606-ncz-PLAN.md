---
quick_id: 260606-ncz
title: Add Table of Contents to use-case READMEs
status: in-progress
---

# Quick Task 260606-ncz: Add TOC to use-case READMEs

## Goal

Add a `## Table of Contents` section to each of the 7 use-case READMEs under
`docs/use-cases/*/README.md`, matching the root README's TOC style (a
`## Table of Contents` heading followed by a bullet list of anchor links). The
root `README.md` already has one and is left untouched.

## Approach

- Insert the TOC block after the persona intro paragraphs and before the first
  `## Configuration` heading in each file.
- Two-level list: `##` sections as top-level bullets, `###` subsections nested
  one level. (`####` odd/even-week items left out for cross-file consistency.)
- GitHub anchor slugs: lowercase, punctuation stripped, spaces to hyphens.
- Frontend-only terminology is preserved (no backend keys introduced).

## Files

- `docs/use-cases/simple-schedule/README.md`
- `docs/use-cases/business-calendar/README.md`
- `docs/use-cases/predictive-preheat/README.md`
- `docs/use-cases/rotating-shift-worker/README.md`
- `docs/use-cases/shared-custody-odd-even-weeks/README.md`
- `docs/use-cases/student-mixed-schedule/README.md`
- `docs/use-cases/bathroom-comfort-zone/README.md`

## Verify

- `pre-commit run markdownlint-cli2 --files <each README>` passes.
- Each anchor link resolves to a real heading in the same file.
