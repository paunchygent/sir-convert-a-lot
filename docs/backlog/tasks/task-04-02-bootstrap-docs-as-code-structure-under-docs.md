---
id: 005-bootstrap-docs-as-code-structure-under-docs
title: Bootstrap docs-as-code structure under docs/
type: task
status: completed
priority: critical
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md
  - docs/\_meta/docs-contract.yaml
labels:
  - docs-as-code
  - contract
---

## Objective

Define and enforce canonical documentation taxonomy for this repository, including planning
hierarchy and frontmatter constraints.

## PR Scope

- Docs contract definition and enforcement tooling.
- Frontmatter normalization and validator hardening.

## Deliverables

- `docs/_meta/docs-contract.yaml` with strict validation rules.
- Contract-driven validator for `docs/` and `.agents/rules/`.
- Frontmatter normalization for existing docs and rules.

## Acceptance Criteria

1. `pdm run validate-docs` passes with zero violations.
1. Planning hierarchy supports `programme`, `epic`, `story`, and `task`.
1. Docs taxonomy includes runbooks, reference docs, ADRs, and PDRs.

## Checklist

- [x] Contract file created
- [x] Validator upgraded to contract-driven checks
- [x] Existing docs/rules fully normalized
