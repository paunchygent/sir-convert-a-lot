---
id: story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy
title: Consolidate Qwen experiment governance and surface taxonomy
type: story
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/backlog/tasks/task-222-define-the-qwen-experiment-taxonomy-surface-status-matrix-and-short-freeze-rule.md
  - docs/backlog/tasks/task-223-publish-the-canonical-qwen-experiment-spec-and-single-ledger-update-contract.md
  - docs/backlog/tasks/task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - .codex/rules/096-qwen-experiment-governance.md
labels:
  - qwen
  - finetuning
  - governance
  - experiments
  - taxonomy
---

Implementation slice with acceptance-driven scope.

## Objective

Consolidate the Qwen Qwen experiment program behind one explicit
governance model so operators stop mixing historical-control, mechanism, and
recovery answers across non-equivalent runs.

This story is the short docs/control-plane consolidation slice that:

- defines one experiment taxonomy,
- defines one canonical experiment spec and single live result ledger,
- marks old proof surfaces as historical rather than operational,
- and freezes new launches while the governance package lands, except for the
  already-running `T221` provenance control.

## Scope

- Define the three experiment classes and the one-question-per-run rule:
  - `provenance`
  - `mechanism`
  - `recovery`
- Publish one active surface matrix with explicit statuses:
  - `active`
  - `legacy-readonly`
  - `deprecated`
- Keep the existing CLI surfaces callable in this slice; do not rename or
  remove commands.
- Reuse
  `docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md`
  as the single live result ledger.
- Add one normative experiment-spec contract that future active runs must
  record before causal claims are made.
- Reroute Story 31, the runbook, the Qwen skill, and `current.md` through the
  new matrix so future work no longer treats Story 29/30 proof wrappers as the
  active mental model.

## Acceptance Criteria

- [x] Story 32 records the three experiment classes:
  `provenance`, `mechanism`, and `recovery`.
- [x] Story 32 records the one-question-per-run rule and the promotion ladder:
  local gate -> short bounded fresh-start run -> longer governed proof.
- [x] The package marks:
  - `qwen-historical-pilot-control` as `provenance` / `active`
  - `qwen-stability-lab` as `mechanism` / `active`
  - the governed `qwen-train launch/status` proof lane as
    `recovery` / `active but blocked until promotion`
  - `qwen-freshstart-proof` and
    `qwen-backward-lineage` as `legacy-readonly`
  - `qwen-fallback-proof` and `qwen-fallback-accumulation-proof` as `deprecated` for new work
- [x] The Task 101 progress reference is explicitly documented as the single
  live result ledger for active Qwen experiment work.
- [x] The runbook, skill, Story 31, Epic 08, and `current.md` all point to
  the same active-lane interpretation.
- [x] No new Story 31 variant or recovery proof launch is introduced while the
  governance package lands; the already-running `T221` surface remains allowed
  to resolve as provenance evidence.

## Test Requirements

- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] An operator can decide whether a question is provenance, mechanism, or
  recovery from one table without reconstructing old task history.
- [x] The primary Qwen runbook flow contains only active surfaces.
- [x] Legacy Story 29/30 proof wrappers remain callable but are no longer
  presented as next-step operational surfaces.

## Done Definition

Done when the repo has one explicit experiment taxonomy, one canonical
experiment-spec contract, one single live result ledger, one active surface
matrix, and one synchronized operator-facing documentation set that routes
future Qwen work through provenance, mechanism, and recovery instead of
through overlapping proof wrappers.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-222-define-the-qwen-experiment-taxonomy-surface-status-matrix-and-short-freeze-rule.md`
1. `docs/backlog/tasks/task-223-publish-the-canonical-qwen-experiment-spec-and-single-ledger-update-contract.md`
1. `docs/backlog/tasks/task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows.md`

## Outcome

- Story 32 now defines the governing experiment taxonomy for Epic 08:
  `provenance`, `mechanism`, and `recovery`.
- `T221` remains the active provenance control surface and is explicitly
  separated from the Story 31 mechanism lane.
- Story 31 now reads as a mechanism story:
  `T219` is now recorded as negative bounded evidence, `T228` is the next
  bounded mechanism slice, and `T217` remains the blocked recovery lane until
  promotion.
- The Task 101 progress reference is now the single live ledger for future
  active runs, with an explicit experiment-spec contract and per-run entry
  template.
- Historical Story 29 and Story 30 proof wrappers remain callable for
  reference and reproduction only, not as active next-step surfaces.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
