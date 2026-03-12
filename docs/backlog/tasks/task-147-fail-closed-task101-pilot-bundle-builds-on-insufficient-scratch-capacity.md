---
id: 'task-147-fail-closed-task101-pilot-bundle-builds-on-insufficient-scratch-capacity'
title: 'Fail closed Task101 pilot-bundle builds on insufficient scratch capacity'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-144-harden-task-101-bundle-against-unreadable-frozen-freeze-summary.md
  - docs/backlog/tasks/task-145-repair-hemma-kernel-package-drift-and-disable-auto-applied-tailscale-updates.md
  - docs/backlog/tasks/task-146-normalize-frozen-qwen-pilot-root-permissions-for-bundle-reads.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels: []
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden the committed Task 101 pilot-bundle builder so it fails before writing
partial output when the selected target filesystem does not have enough free
space for the retained pilot audio plus deterministic bundle overhead.

## PR Scope

- Reproduce the current Hemma Task 101 bundle retry far enough to identify the
  next blocker after `T144` and `T146`.
- Add a committed capacity preflight to `task101_qwen_pilot_bundle.py` that
  estimates the retained bundle payload and compares it with free space on the
  target filesystem before any writes begin.
- Fail with an explicit `ENOSPC` operator error instead of leaving partial
  bundle trees on `/srv/scratch`.
- Record the verified Hemma storage evidence and the operator guidance for the
  next retry.

## Deliverables

- [x] Task 101 pilot-bundle build fails closed on insufficient target-fs free
  space.
- [x] Regression coverage added for the new preflight.
- [x] Runbook/task docs updated with the verified `2026-03-12` Hemma capacity
  finding.

## Acceptance Criteria

- [x] A too-full target filesystem triggers an explicit `ENOSPC` failure before
  `output_root` is created.
- [x] The error message tells the operator to free space or choose a different
  `--output-root`.
- [x] The docs state that the current live Hemma blocker is `/srv/scratch`
  exhaustion rather than unreadable freeze artifacts or the repaired host
  package-manager incident.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [x] `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`

## Outcome

`T147` closes the last ambiguous Task 101 rerun failure on Hemma from
`2026-03-12`.

- Verified the frozen pilot source root is about `17G` on `/srv/storage` and
  the selected Task 101 retained rows (`8445` train + `8` held-out eval) project
  to about `9-10G` of bundle payload on `/srv/scratch`.
- Verified the live Hemma retries no longer fail on the original unreadable
  freeze summary (`T144`) or on frozen-root permissions (`T146`).
- Captured the actual remaining blocker from the live detached retry:
  `OSError: [Errno 28] No space left on device`.
- The builder now checks target-fs capacity up front and tells the operator to
  reclaim scratch space or choose a different output root before retrying.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
