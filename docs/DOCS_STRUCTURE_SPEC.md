---
type: spec
id: SPEC-docs-structure
title: Docs Structure Spec
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - docs-as-code
  - structure
links:
  - docs/\_meta/docs-contract.yaml
  - .codex/rules/090-documentation-standards.md
---

## Layout

- `docs/converters/`: API and CLI usage documentation.
- `docs/decisions/`: ADRs and architectural decisions.
- `docs/runbooks/`: Operational procedures and troubleshooting.
- `docs/backlog/`: planning and execution artifacts.
- `docs/_meta/`: docs-as-code contract metadata.
- `.codex/rules/`: operational rules and conventions.
- `.codex/handoff.md`: volatile session handoff.
- `.codex/long-term-memory/`: durable session-history entries.

## Invariants

- Contract docs and code must match.
- ADR updates are required for policy changes (auth, fallback, retention, contract semantics).
- Task lifecycle updates are required when state changes (`proposed -> in_progress -> completed`).
- `pdm run docs-validate` enforces backlog, docs, and `.codex/rules/` contracts.
- `pdm run skills-validate` enforces repo-local `.codex/skills/` metadata.
- `pdm run handoff-validate` enforces `.codex/handoff.md` and `.codex/long-term-memory/` topology.
