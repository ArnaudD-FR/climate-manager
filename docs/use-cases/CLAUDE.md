# Use-case docs — Claude instructions

When building or editing use-case docs in this folder, follow the authoring
guide in [AGENT.md](./AGENT.md). Key rules: never hand-write `scenario.json`
status — author the user config + world + pinned time and let the real
coordinator compute it via `make use-case-data`; pin times in UTC; and write
READMEs in the panel's user-facing terminology only.

@AGENT.md
