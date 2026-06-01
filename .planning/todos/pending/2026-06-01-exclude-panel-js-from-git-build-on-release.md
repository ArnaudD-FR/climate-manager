---
created: 2026-06-01T00:00:00.000Z
title: Exclude panel.js from git, generate it on release
area: tooling
files:
  - custom_components/climate_manager/www/panel.js
  - .gitignore
  - Makefile
---

## Problem

`custom_components/climate_manager/www/panel.js` is a Vite build artifact
committed to git. This causes noisy diffs on every build, inflates repo
history, and creates inconsistency (the committed bundle may not match
the source if someone forgets to rebuild). The file should be generated,
not stored.

## Solution

1. Add `custom_components/climate_manager/www/panel.js` to `.gitignore`
2. Remove it from git tracking (`git rm --cached`)
3. Update the `Makefile` release/archive target so that `panel.js` is
   built and included in the distribution archive (e.g. a `make release`
   or `make archive` target that runs `make build` then packages
   `custom_components/` + the freshly built `www/panel.js` into a zip)
4. Update `docs/screenshot.js` if it assumes `panel.js` is pre-built
   (currently calls `make screenshots` which already runs `make build`
   first — so this is fine)
5. Update HACS / manual installation docs to note that HACS users get
   the built artifact from the release archive, not from the raw repo
