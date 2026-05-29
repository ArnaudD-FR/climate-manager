---
slug: 260529-g8p
status: complete
date: 2026-05-29
commit: e0eea90
---

# Summary: Add EditorConfig with 80-char line width

## What was done

Added `.editorconfig` at project root declaring 80-char `max_line_length` for
Python, TypeScript, and Markdown. Configured ruff and prettier to enforce it,
then ran both formatters on the full codebase.

## Changes

- `.editorconfig` — root EditorConfig with per-extension settings
- `.prettierrc` — printWidth:80, tabWidth:2, trailingComma:all
- `pyproject.toml` — added `[tool.ruff]` with `line-length = 80`
- `frontend/package.json` — prettier added as devDependency
- 9 Python files reformatted by `ruff format`
- 13 TypeScript files reformatted by `prettier`
- `README.md`, `specs.md` reformatted by prettier
- Manual fixes for remaining code-level violations (inline comments, JSDoc,
  string literals) that formatters cannot auto-wrap

## Residual violations (7, unavoidable)

All in Lit HTML template literals — `style="..."` and `<span style="...">${}`
attribute expressions that cannot be broken without extracting to CSS classes.
These are a known Lit limitation without `prettier-plugin-lit`.
