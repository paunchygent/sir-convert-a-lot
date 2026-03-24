---
id: 'task-248-fix-hemma-live-verifier-weasyprint-probe-to-match-container-runtime'
title: 'Correct Hemma live verifier WeasyPrint probe to match container runtime'
type: 'task'
status: 'in_progress'
priority: 'high'
created: '2026-03-24'
last_updated: '2026-03-24'
related:
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions_helpers.py
labels:
  - hemma
  - devops
  - verification
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Fix the false-negative Hemma live-verification failure where the v2 smoke helper
probes WeasyPrint through `pdm run python` inside `sir_convert_a_lot_prod`
even though the deployed runtime image exposes `python` directly and does not
ship `pdm`.

## PR Scope

- update the runtime probe in
  `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions_helpers.py`
  to execute `python` directly inside the prod container;
- add regression coverage so Task 39 / Task 76 verification never reintroduces
  the incorrect `pdm` dependency in the running container;
- rerun the canonical deploy-and-verify gate on Hemma against the pushed fix.

Out of scope:

- changing the deployed service image contents to add `pdm`;
- weakening Task 76 failure behavior or downgrading verifier failures to
  warnings.

## Deliverables

- [ ] The WeasyPrint runtime probe matches the actual container contract and no
  longer shells through `pdm`.
- [ ] Regression tests cover the exact in-container command shape for the
  WeasyPrint probe.
- [ ] `pdm run hemma-deploy-and-verify ...` passes end-to-end on the pushed
  revision.

## Acceptance Criteria

- [ ] The Hemma v2 smoke helper reads the WeasyPrint version using direct
  `python` execution inside `sir_convert_a_lot_prod`.
- [ ] The helper test suite fails if `pdm` reappears in the in-container
  WeasyPrint probe command.
- [ ] The canonical deploy report for the fixed revision records a successful
  verification run instead of the previous false-negative failure.

## Validation Commands

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_verify_hemma_v2_conversions_helpers.py tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
