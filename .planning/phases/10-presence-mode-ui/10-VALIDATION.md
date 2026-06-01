---
phase: 10
slug: presence-mode-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node.js built-in test runner (`node:test`) |
| **Config file** | none — invoked directly |
| **Quick run command** | `node --test --experimental-strip-types frontend/src/components/person-card.test.ts` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `node --test --experimental-strip-types frontend/src/components/person-card.test.ts`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | UI-01, UI-02 | — | N/A (UI-only) | unit | `node --test --experimental-strip-types frontend/src/components/person-card.test.ts` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | UI-02 | — | N/A (UI-only) | unit | `node --test --experimental-strip-types frontend/src/components/person-card.test.ts` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | UI-01 | — | N/A (UI-only) | unit | `node --test --experimental-strip-types frontend/src/components/person-card.test.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/components/person-card.test.ts` — stubs for UI-01 (option
  visibility, stuck-mode warning) and UI-02 (badge text, option label)
