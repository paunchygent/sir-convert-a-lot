---
id: task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows
title: Reroute Qwen operator docs through the active surface matrix and demote legacy proof workflows
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - .codex/handoff.md
  - .codex/rules/096-qwen-experiment-governance.md
labels:
  - qwen
  - finetuning
  - governance
  - docs
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reroute the operator-facing Qwen docs through the Story 32 surface matrix so
the active workflow only shows the active surfaces, while historical Story
29/30 proof wrappers remain documented as legacy or deprecated references.

## PR Scope

- Update the runbook to show only active surfaces in the primary operator flow:
  - `qwen-historical-pilot-control`
  - `qwen-stability-lab`
  - governed `qwen-train launch/status` recovery proof after promotion
- Demote Story 29/30 proof wrappers from the primary flow:
  - `qwen-freshstart-proof`
  - `qwen-backward-lineage`
  - `qwen-fallback-proof`
  - `qwen-fallback-accumulation-proof`
- Update the Qwen finetuning skill, Epic 08 entrypoint, Story 31, and
  `current.md` to use the same matrix and lane vocabulary.
- Keep all existing CLI commands callable; this task is docs/status-only
  demotion, not command removal.

## Deliverables

- [x] The primary Qwen runbook flow contains only active surfaces.
- [x] The Qwen finetuning skill uses the same active surface matrix as the
  runbook and live ledger.
- [x] Epic 08, Story 31, and `current.md` now describe provenance,
  mechanism, and recovery explicitly.
- [x] Historical proof surfaces remain callable but are no longer described as
  next-step operational surfaces.

## Acceptance Criteria

- [x] An operator reading the runbook can decide which active surface to use
  without reading old Story 29/30 task history.
- [x] Story 31 explicitly reads as the mechanism lane, with `T219` as the next
  mechanism slice and `T217` as the blocked recovery lane.
- [x] `current.md` points future work to the active taxonomy instead of to a
  mixed proof stack.
- [x] The docs package does not rename or remove any CLI commands.

## Validation

- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Outcome

- Active operator guidance now routes through three questions:
  provenance, mechanism, or recovery.
- Story 29 and Story 30 wrappers remain historical artifacts rather than the
  active mental model.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
