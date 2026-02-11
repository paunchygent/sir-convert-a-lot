---
id: '004-standalone-repo-bootstrap-and-governance-setup'
title: 'Standalone repo bootstrap and governance setup'
type: 'story'
status: 'in_progress'
priority: 'critical'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md'
  - 'docs/backlog/tasks/task-04-02-bootstrap-docs-as-code-structure-under-docs.md'
  - 'docs/backlog/tasks/task-04-03-migrate-canonical-converter-code-and-quality-gates.md'
  - 'docs/backlog/tasks/task-04-04-prepare-docker-hemma-service-foundation.md'
labels:
  - 'story'
  - 'bootstrap'
  - 'governance'
---
# Standalone repo bootstrap and governance setup

## Objective

Establish `sir-convert-a-lot` as a fully independent repository with canonical docs-as-code,
quality gates, and operational runbooks aligned with your Skriptoteket/HuleEdu standards.

## Scope

- Repo structure and docs taxonomy enforcement.
- Rules and AGENTS baseline.
- Canonical script wrappers and quality scripts.
- Initial DevOps skill + runbook for Hemma/GPU operations.

## Acceptance Criteria

1. All docs and rules are frontmatter-validated by contract.
2. AGENTS.md includes canonical standards for docs, testing, PDM, Docker v2, PostgreSQL, and Hemma.
3. New setup tasks (005-007) are linked and track execution state.
4. Runbook and skill exist for repo-specific Hemma/GPU operations.

## Test Requirements

- `pdm run validate-docs` passes for docs/rules frontmatter contract.
- `pdm run validate-tasks` passes for backlog template and hierarchy rules.
- Quality gates pass on code and script updates.

## Done Definition

- Acceptance criteria met.
- Validation and quality gates green.
- Setup story/task docs and session handoff updated.

## Checklist

- [x] Story created and linked to setup tasks
- [ ] All acceptance criteria met
- [ ] Story marked completed
