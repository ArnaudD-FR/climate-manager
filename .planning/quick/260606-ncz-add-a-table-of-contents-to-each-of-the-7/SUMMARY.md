---
quick_id: 260606-ncz
title: Add Table of Contents to use-case READMEs
status: complete
date: 2026-06-06
---

# Quick Task 260606-ncz: Add TOC to use-case READMEs — Summary

## What changed

Added a `## Table of Contents` section to all 7 use-case READMEs under
`docs/use-cases/*/README.md`, inserted after the persona intro and before the
first `## Configuration` heading. The root `README.md` already had a TOC and was
left untouched.

Each TOC lists the two `##` sections (`Configuration`, `What happens`) as
top-level bullets, with the `Configuration` subsections nested one level. This
mirrors the root README's bullet-link TOC style.

## Key decision: time-stamped subsections omitted from the TOC

The `## What happens` subsections (e.g. `When Emma is home (Wednesday 19:00)`)
contain colons. GitHub's anchor slugger and the repo's `markdownlint-cli2`
v0.40 (MD051) disagree on how to slugify a colon:

- GitHub renders `(Wednesday 19:00)` as `...-wednesday-1900`.
- markdownlint v0.40 only accepts `...-wednesday-19` (it truncates at the
  colon).

A GitHub-correct anchor therefore fails the enforced pre-commit `markdownlint`
hook, and a lint-passing anchor breaks the link on GitHub — irreconcilable.
Rather than weaken the MD051 rule project-wide or ship broken anchors, the
colon-free `Configuration` subsections are linked and `What happens` is listed
as a leaf. All linked fragments are valid on both GitHub and markdownlint.

## Verification

- `pre-commit run prettier --files docs/use-cases/*/README.md` — Passed
- `pre-commit run markdownlint-cli2 --files docs/use-cases/*/README.md` — Passed
  (MD051 validates every TOC fragment resolves to a real heading)

## Files

- `docs/use-cases/simple-schedule/README.md`
- `docs/use-cases/business-calendar/README.md`
- `docs/use-cases/predictive-preheat/README.md`
- `docs/use-cases/rotating-shift-worker/README.md`
- `docs/use-cases/shared-custody-odd-even-weeks/README.md`
- `docs/use-cases/student-mixed-schedule/README.md`
- `docs/use-cases/bathroom-comfort-zone/README.md`
