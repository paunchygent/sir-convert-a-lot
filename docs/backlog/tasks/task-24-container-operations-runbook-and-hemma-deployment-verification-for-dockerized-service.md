---
id: task-24-container-operations-runbook-and-hemma-deployment-verification-for-dockerized-service
title: Container operations runbook and Hemma deployment verification for dockerized service
type: task
status: proposed
priority: high
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-22-docker-compose-service-packaging-and-readiness-gated-startup.md
  - docs/backlog/tasks/task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - runbook
  - hemma
  - deployment
  - operations
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish and validate canonical container operations flow on Hemma (deploy, verify, restart,
recover) so operators can run the dockerized service safely with GPU-first guarantees.

## PR Scope

- Update runbook with canonical container lifecycle commands (deploy/update/rollback/restart).
- Codify verification flow that combines health, readiness, and GPU runtime checks.
- Add/extend script-backed checks for Hemma deployment correctness where needed.
- Validate end-to-end command flow against real Hemma topology and tunnel-first local checks.

Out of scope:

- service image/compose implementation internals (Task 22),
- core persistence behavior implementation (Task 23).

## Deliverables

- [ ] Runbook section for dockerized service operations on Hemma.
- [ ] Canonical command set for deploy/pull/restart/verify with no ad hoc shell transport.
- [ ] Verification evidence for readiness + GPU runtime + conversion smoke path.
- [ ] Backlog/context docs updated with final operational contract.

## Acceptance Criteria

- [ ] Operator can follow runbook only and reach healthy ready services on Hemma.
- [ ] Verification catches stale revision or profile/data-root mismatch deterministically.
- [ ] GPU-first invariant remains enforced under containerized startup/restart flow.
- [ ] Manual smoke conversion via tunnel is documented and evidenced.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
