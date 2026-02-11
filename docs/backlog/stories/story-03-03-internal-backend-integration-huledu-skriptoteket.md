---
id: 003c-huledu-skriptoteket-internal-integration-story
title: Internal backend integration for HuleEdu and Skriptoteket
type: story
status: in_progress
priority: high
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/internal_adapter_contract_v1.md
  - docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md
  - docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md
  - docs/reference/ref-story-003c-consumer-integration-handoff.md
labels:
  - integration
  - huledu
  - skriptoteket
  - internal-api
---

## Objective

Provide one shared internal conversion backend contract that both HuleEdu and Skriptoteket can consume without per-repo forks or ad hoc converter orchestration.

## Scope

- Define and verify integration profiles for both systems.
- Ensure shared auth, idempotency, correlation, and error handling behavior.
- Preserve simple local dev flow via internal tunnel/HTTP.

## Acceptance Criteria

1. Both HuleEdu and Skriptoteket integration docs reference the same canonical v1 contract.
1. Both systems can submit and retrieve conversion jobs through the same endpoint set and auth model.
1. Correlation IDs are propagated from caller to conversion logs/metadata.
1. Integration wrappers in consumer repos are thin adapters only (no business logic forks).
1. Local tunnel-based development workflow is documented with troubleshooting basics.

## Test Requirements

- Integration contract tests from HuleEdu integration adapter.
- Integration contract tests from Skriptoteket integration adapter.
- End-to-end test: local dev machine -> tunnel -> Hemma -> output retrieval.
- Error propagation tests: auth failure, validation failure, timeout/failure states.

## Done Definition

- Cross-repo integration tests pass against the same contract.
- No consumer-specific schema drift exists in wrappers/docs.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
