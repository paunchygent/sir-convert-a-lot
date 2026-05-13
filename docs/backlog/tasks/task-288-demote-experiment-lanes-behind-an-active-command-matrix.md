---
id: task-288-demote-experiment-lanes-behind-an-active-command-matrix
title: Demote experiment lanes behind an active command matrix
type: task
status: proposed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows.md
  - .codex/rules/096-qwen-experiment-governance.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - experiments
  - qwen
  - command-surface
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make experiment and research lanes visibly subordinate to production conversion
surfaces by publishing one active command matrix and demoting legacy/deprecated
proof commands behind explicit legacy or docs-only surfaces.

## PR Scope

- Classify production conversion, OCR benchmark, Qwen, and sidecar commands as
  active, legacy-readonly, deprecated, or docs-only according to the active
  governance vocabulary.
- Keep Qwen and sidecar work available, but stop presenting old proof commands
  as peers of production conversion commands in the flat PDM script surface.
- Move legacy/deprecated proof commands behind a clearly named legacy namespace
  or a docs-only runbook section, preserving evidence and operator history.
- Align `.codex/rules/096-qwen-experiment-governance.md`, the Qwen runbook,
  `pyproject.toml` script exposure, and generated docs/index surfaces.
- Do not delete governed benchmark evidence, model artifacts, or historical
  reports as part of this task.

## Deliverables

- [ ] Active command matrix covering production conversion, DigiExam migration,
  OCR benchmark, Qwen, and sidecar lanes.
- [ ] Legacy/deprecated command list with explicit status and owner.
- [ ] PDM script exposure updated so deprecated proof commands are not shown as
  active production entrypoints.
- [ ] Runbook/rule/docs updates that point operators to the matrix instead of
  scattered flat script discovery.

## Acceptance Criteria

- [ ] No production conversion command is hidden or renamed without a
  compatibility decision.
- [ ] Deprecated Qwen proof commands such as `qwen-t197-proof` and
  `qwen-t198-proof` are no longer presented as active commands.
- [ ] Active command docs agree with Rule 096's status vocabulary or update that
  rule in the same governed diff.
- [ ] Validation includes docs gates plus focused script/help checks for any
  PDM command names changed or demoted.
- [ ] The close-out names any commands intentionally left flat and why.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
