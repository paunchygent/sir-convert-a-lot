---
id: 'task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover'
title: 'Add auth-aware public-edge access evidence for Sir Convert cutover'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/tasks/task-263-run-sir-convert-gateway-cutover-proof-and-security-review.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
labels:
  - gateway
  - public-edge
  - evidence
  - access-logs
  - cutover
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add an auth-aware, redacted public-edge evidence surface before the final Sir
Convert Gateway cutover so unknown direct public consumers can be classified
without exposing secrets or persisting raw request headers.

## PR Scope

- Define a safe nginx-proxy, app, or sidecar log format that records:
  - host;
  - method;
  - normalized route bucket;
  - status;
  - upstream target;
  - user-agent class;
  - request-id or correlation id when present;
  - API-key presence as a boolean only, never the key value.
- Keep IP addresses, API keys, cookies, bearer tokens, identity headers, query
  strings, and artifact/job identifiers out of durable artifacts.
- Capture a defined pre-cutover evidence window after Task 265 reserved public
  edge is live.
- Produce redacted route/status/API-key-presence counts for
  `convert.hule.education`.
- Feed the result into Task 263 final cutover proof and the caller inventory
  reference.

## Deliverables

- [ ] Safe log-format or collector plan.
- [ ] Redacted public-edge evidence artifact with route/status/API-key-presence
  counts.
- [ ] Inventory reference update classifying or blocking unknown public
  consumers.
- [ ] Proof that no secrets or raw identity material are persisted.

## Acceptance Criteria

- [ ] API-key presence is represented only as `present`, `absent`, or
  `unavailable`; key values are never logged.
- [ ] The evidence window is named with start/end timestamps.
- [ ] Unknown public consumers are either ruled out by evidence or remain an
  explicit Task 263 cutover blocker.
- [ ] The final cutover proof consumes this evidence before declaring
  `convert.hule.education` ready for Gateway-fronted live testing.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
