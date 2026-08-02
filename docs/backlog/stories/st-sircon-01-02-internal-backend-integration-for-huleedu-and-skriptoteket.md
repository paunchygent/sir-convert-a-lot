---
type: story
id: ST-SIRCON-01-02
title: Internal backend integration for HuleEdu and Skriptoteket
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-01
links:
  decisions: []
acceptance_criteria:
- Both HuleEdu and Skriptoteket integration docs reference the same canonical v1 contract.
- Both systems can submit and retrieve conversion jobs through the same endpoint set
  and auth model.
- Correlation IDs are propagated from caller to conversion logs and metadata.
- Integration wrappers in consumer repos are thin adapters only, with no business-logic
  forks.
- Local tunnel-based development workflow is documented with troubleshooting basics.
- HuleEdu adoption is validated on real demanding scientific-paper PDFs with evidence
  that operation requires no per-document logic forks.
retired_ids:
- 003c-huledu-skriptoteket-internal-integration-story
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

### Objective

Provide one shared internal conversion backend contract that both HuleEdu and Skriptoteket can consume without per-repo forks or ad hoc converter orchestration.

### Scope

- Define and verify integration profiles for both systems.
- Ensure shared auth, idempotency, correlation, and error handling behavior.
- Preserve simple local dev flow via internal tunnel/HTTP.

### Acceptance Criteria

1. Both HuleEdu and Skriptoteket integration docs reference the same canonical v1 contract.
1. Both systems can submit and retrieve conversion jobs through the same endpoint set and auth model.
1. Correlation IDs are propagated from caller to conversion logs/metadata.
1. Integration wrappers in consumer repos are thin adapters only (no business logic forks).
1. Local tunnel-based development workflow is documented with troubleshooting basics.
1. HuleEdu adoption is validated on real, demanding scientific-paper PDFs with evidence that the flow is easy to operate without per-document logic forks.

### Test Requirements

- Integration contract tests from HuleEdu integration adapter.
- Integration contract tests from Skriptoteket integration adapter.
- End-to-end test: local dev machine -> tunnel -> Hemma -> output retrieval.
- Error propagation tests: auth failure, validation failure, timeout/failure states.
- HuleEdu demanding scientific-paper workload validation run with summarized results and failure taxonomy.

### Done Definition

- Cross-repo integration tests pass against the same contract.
- No consumer-specific schema drift exists in wrappers/docs.
- HuleEdu adoption evidence on demanding scientific-paper workload is recorded and linked.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
