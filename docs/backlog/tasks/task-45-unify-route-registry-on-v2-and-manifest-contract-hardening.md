---
id: task-45-unify-route-registry-on-v2-and-manifest-contract-hardening
title: Unify route registry on v2 and manifest contract hardening
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - routing
  - manifest
  - contract
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Create one explicit route contract and manifest semantics that downstream GUI clients can reason about deterministically.

## PR Scope

- Refactor route registry to v2-only route taxonomy.
- Add explicit route metadata for CLI/API diagnostics (`source_format`, `target_format`, `pipeline_used`).
- Harden manifest schema so route/version semantics are explicit and stable.
- Tighten route-aware option validation to avoid implicit no-op flags.

## Deliverables

- [ ] v2-only route registry with typed metadata.
- [ ] Manifest schema extension and docs for deterministic GUI orchestration.
- [ ] Validation errors that clearly state route-option incompatibilities.

## Acceptance Criteria

- [ ] `convert-a-lot routes` and `--dry-run` show only v2 route graph.
- [ ] Manifest fields are sufficient to correlate jobs to route contract and artifact behavior.
- [ ] Route-option misuse produces deterministic, actionable errors.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
