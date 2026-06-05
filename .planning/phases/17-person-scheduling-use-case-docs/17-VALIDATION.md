---
phase: 17
slug: person-scheduling-use-case-docs
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Make targets + Playwright (docker) — no unit framework |
| **Config file** | `Makefile` (root) + per-use-case `Makefile`s |
| **Quick run command** | `make build` (rebuild panel.js, ~tsc + vite) |
| **Full suite command** | `make screenshots` (build → docker Playwright capture) |
| **Estimated runtime** | ~60–120 seconds (docker pull cached) |

---

## Sampling Rate

- **After every task commit:** Run `make build` (panel.js still compiles)
- **After every plan wave:** Run `make screenshots` (all scenario sets emit)
- **Before `/gsd-verify-work`:** `make screenshots` must exit 0 and every
  `docs/use-cases/<slug>/screenshots/` must contain its PNGs
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | DOC-01 | — / — | N/A (docs/tooling, no runtime) | integration | `test -n "$(grep -E 'OUTPUT_DIR\|HARNESS_PATH' docs/screenshot.js)"` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 2 | DOC-01 | — / — | N/A | integration | `make screenshots && ls docs/use-cases/*/screenshots/*.png` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Per-task rows are illustrative; the planner's PLAN.md `acceptance_criteria`
are the authoritative checks. This phase is validated by deterministic
filesystem + exit-code assertions, not a unit suite.*

---

## Wave 0 Requirements

- [ ] No unit framework install required — validation is `make screenshots`
  exit code + PNG presence assertions
- [ ] Docker available (existing `make screenshots` prerequisite) — Playwright
  capture runs in `mcr.microsoft.com/playwright` container

*Existing screenshot tooling covers all phase verification; only the
scenario-parameterisation extension (env vars on `docs/screenshot.js`) is new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Each scenario screenshot shows the intended person-card state (correct mode badge + schedule shape) | DOC-01 | Visual correctness can't be asserted from PNG bytes | Open each `docs/use-cases/<slug>/screenshots/*.png` and confirm the person card renders that persona's mode (scheduled/ha/calendar/even-odd) |
| Each README persona + config table matches its screenshots | DOC-01 | Editorial/visual coherence | Read each `README.md` against its `screenshots/` set |

---

## Validation Sign-Off

- [ ] All tasks have `<acceptance_criteria>` with command/filesystem assertions
  or Wave 0 dependencies
- [ ] Sampling continuity: `make screenshots` runs after each wave
- [ ] Wave 0 covers all MISSING references (none — tooling exists)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
