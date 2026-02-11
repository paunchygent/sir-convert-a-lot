---
id: task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c
title: Establish Sir Convert-a-Lot Hemma deployment readiness and tunnel smoke evidence for Story 003c
type: task
status: proposed
priority: high
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md
  - docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md
  - docs/converters/internal_adapter_contract_v1.md
  - docs/reference/ref-story-003c-consumer-integration-handoff.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - ops
  - hemma
  - tunnel
  - story-003c
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Establish deployable Sir Convert-a-Lot service presence on Hemma and capture
successful tunnel smoke evidence on the expected service port.

## PR Scope

- Verify/repair canonical Hemma repo root for Sir Convert-a-Lot.
- Deploy or start Sir Convert-a-Lot service on expected local-only port.
- Execute tunnel smoke from local machine and capture health/submit evidence.
- Update Story 003c reference docs with successful operational evidence.

## Deliverables

- [ ] Confirmed remote repo path and service startup command evidence.
- [ ] Successful `curl` health response through local tunnel endpoint.
- [ ] One adapter submit/poll/result smoke transcript through tunnel.
- [ ] Updated Story 003c handoff/reference docs with success outputs.

## Acceptance Criteria

- [ ] Hemma service is reachable on agreed Sir Convert-a-Lot port.
- [ ] Local tunnel flow (`ssh -L ...`) works with deterministic command evidence.
- [ ] Adapter smoke (`submit -> poll -> result`) succeeds against Hemma-hosted service.
- [ ] Story 003c docs no longer have operational readiness caveat for Hemma smoke.

## Validation

- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
