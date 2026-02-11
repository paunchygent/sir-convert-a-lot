---
type: spec
id: SPEC-docs-structure
title: Docs Structure Spec
status: active
created: 2026-02-11
updated: 2026-02-11
owners:
  - platform
tags:
  - docs-as-code
  - structure
links:
  - docs/_meta/docs-contract.yaml
  - .agents/rules/090-documentation-standards.mdc
---
# Docs Structure Spec

## Layout

- `docs/converters/`: API and CLI usage documentation.
- `docs/decisions/`: ADRs and architectural decisions.
- `docs/runbooks/`: Operational procedures and troubleshooting.
- `docs/backlog/`: planning and execution artifacts.
- `docs/_meta/`: docs-as-code contract metadata.
- `.agents/rules/`: operational rules and conventions.
- `.agents/work/session/`: session handoff + readme-first context.

## Invariants

- Contract docs and code must match.
- ADR updates are required for policy changes (auth, fallback, retention, contract semantics).
- Task lifecycle updates are required when state changes (`proposed -> in_progress -> completed`).
- `pdm run validate-docs` enforces frontmatter rules for `docs/` and `.agents/rules/`.
