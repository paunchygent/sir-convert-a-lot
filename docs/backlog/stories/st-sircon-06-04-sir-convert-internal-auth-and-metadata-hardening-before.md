---
type: story
id: ST-SIRCON-06-04
title: Sir Convert internal auth and metadata hardening before cutover
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
epic: EPIC-SIRCON-06
links:
  decisions: []
acceptance_criteria:
- Missing or invalid auth never returns `500`.
- Public docs/OpenAPI/metrics are disabled or gated in production.
- Detailed readiness metadata is internal-only or intentionally reduced.
- Sir Convert rejects unsigned public user identity headers.
- '`InternalIdentityContextV1` verification and Sir Convert route authorization are
  tested.'
- The existing service API key is treated as transport only, not as global job/artifact
  ownership.
retired_ids:
- story-36-sir-convert-internal-auth-and-metadata-hardening-before-cutover
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

Implementation slice with acceptance-driven scope.

### Objective

Make Sir Convert safe to keep running during and after the Gateway cutover by
fixing unauthenticated failure behavior, reducing production metadata exposure,
and defining internal caller identity.

### Scope

- Return deterministic `401` or `403` responses for missing/invalid credentials.
- Prevent stale durable job data from turning unauthorized requests into `500`
  responses.
- Disable or gate public docs/OpenAPI/metrics/detailed readiness in production.
- Add security headers at app or proxy layer.
- Define and implement Sir Convert's internal identity verification contract.
- Persist context-derived job ownership and enforce it on status, result,
  artifact, partial, checkpoint, resume, cancel, template, SSE, and webhook
  access.

### Acceptance Criteria

- [ ] Missing or invalid auth never returns `500`.
- [ ] Public docs/OpenAPI/metrics are disabled or gated in production.
- [ ] Detailed readiness metadata is internal-only or intentionally reduced.
- [ ] Sir Convert rejects unsigned public user identity headers.
- [ ] `InternalIdentityContextV1` verification and Sir Convert route
  authorization are tested.
- [ ] The existing service API key is treated as transport only, not as global
  job/artifact ownership.

### Test Requirements

- [ ] Focused HTTP auth/error tests.
- [ ] Production-profile app tests for docs/OpenAPI/metrics exposure.
- [ ] Live or local public-edge probes proving unauthenticated deny behavior.
- [ ] `pdm run docs-validate`

### Done Definition

Done when Sir Convert can remain available internally while external
unauthorized traffic fails cleanly and reveals no unnecessary metadata.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
