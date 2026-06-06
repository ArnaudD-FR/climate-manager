---
quick_id: 260529-h5i
slug: add-screenshots-amend-readme
status: complete
date: 2026-05-29
commit: f220dc7
---

# Summary

Staged and amended the README commit (was 209dd18, now f220dc7) to include:

- 6 PNG screenshots (overview, rooms, persons, zone, zone-upstairs,
  global-settings)
- docs/test-harness.html — mock HA panel harness
- docs/screenshot.js — Playwright screenshot script
- docs/package.json + package-lock.json — pins playwright@1.49.0
- Makefile — `screenshots: build` target
- README.md — zone-upstairs section + `make screenshots` doc entry
