---
slug: 260529-g8p
title: Add EditorConfig with 80-char line length and reformat source files
date: 2026-05-29
status: in-progress
---

# Add EditorConfig with 80-char line length

## Goal

Add `.editorconfig` that declares 80-char line length for Python, TypeScript,
and Markdown. Configure ruff and prettier to enforce it. Reformat all existing
source files to comply.

## Tasks

### T1 — Create `.editorconfig`

Create `.editorconfig` at project root with:
- Global defaults: UTF-8, LF, trailing newline, trim trailing whitespace
- Python (*.py): 4-space indent, max_line_length = 80
- TypeScript/JS (*.ts, *.js): 2-space indent, max_line_length = 80
- Markdown (*.md): 2-space indent, max_line_length = 80, no trim trailing WS
- JSON (*.json): 2-space indent
- YAML (*.yaml, *.yml): 2-space indent
- Makefile: tab indent

### T2 — Configure ruff for Python

Add `[tool.ruff]` and `[tool.ruff.format]` sections to `pyproject.toml`:
- line-length = 80
- Run `ruff format custom_components/` to reformat Python files

### T3 — Add prettier for TypeScript + Markdown

Create `.prettierrc` at project root:
- printWidth: 80
- tabWidth: 2
- singleQuote: false
- trailingComma: "all"

Install prettier as dev dependency in `frontend/`:
  `npm install --save-dev prettier` (in frontend/)

Run `npx prettier --write frontend/src/**/*.ts` to reformat TypeScript.

Also run prettier on root markdown: `npx prettier --write README.md specs.md`

### T4 — Commit

Single atomic commit: "chore: add EditorConfig, configure 80-char line width, reformat sources"
