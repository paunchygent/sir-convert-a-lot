---
type: task
id: TASK-SIRCON-06-04-01
title: Remediate unauthenticated Sir Convert API failures and prod metadata exposure
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-06-04
task_kind: story
acceptance_criteria:
- '- [ ] No unauthenticated API request returns `500`.'
- '- [ ] Public production docs/OpenAPI/metrics are blocked or gated.'
- '- [ ] Detailed readiness metadata is no longer broadly public unless ADR-0009 explicitly keeps a reduced public status.'
- '- [ ] Standard security headers are present.'
retired_ids:
- task-258-fix-unauthenticated-sir-convert-api-failures-and-prod-metadata-exposure
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Fix the current security gap where unauthenticated public API probes return
`500` and production exposes docs, OpenAPI, metrics, and detailed health
metadata directly.

### PR Scope

- Make missing/invalid auth return deterministic `401` or `403`.
- Ensure auth failure is not blocked by stale job-store/runtime initialization
  errors.
- Disable or gate `/docs`, `/redoc`, `/openapi.json`, `/metrics`, and detailed
  readiness in production.
- Add security headers either in FastAPI middleware or nginx-proxy config.
- Add identity-verification regression tests for the Sir Convert profile,
  including wrong audience, invalid signature, unknown key id, API-key-only
  user-originated calls, cross-owner artifact reads, and service/operator
  self-signed context rejection.
- Add schema-compatibility regression tests proving accepted service/operator
  contexts validate through the canonical HuleEdu
  `InternalIdentityContextV1` v1 model and unknown top-level `sir_convert_*`
  fields fail closed.
- Add regression tests and public-edge smoke evidence.

### Deliverables

- [ ] Auth failure regression tests.
- [ ] Production docs/OpenAPI/metrics exposure tests.
- [ ] Live or local public-edge probe evidence.
- [ ] Runbook update for public/internal health and metrics lanes.

### Acceptance Criteria

- [ ] No unauthenticated API request returns `500`.
- [ ] Public production docs/OpenAPI/metrics are blocked or gated.
- [ ] Detailed readiness metadata is no longer broadly public unless ADR-0009
  explicitly keeps a reduced public status.
- [ ] Standard security headers are present.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
