---
id: task-188-refactor-host-qwen-cli-control-plane-use-cases-out-of-qwen-train-py
title: Refactor host Qwen CLI control-plane use cases out of qwen_train.py
type: task
status: completed
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - architecture
  - cli
  - control-plane
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reduce `qwen_train.py` to a true composition root so parser wiring and command
dispatch stay in the CLI layer while validation, path-policy enforcement, and
command use cases move into bounded domain modules.

## PR Scope

- Create a bounded `control_plane/` package for Qwen training host-side use
  cases and shared policy.
- Move command-family logic out of `qwen_train.py` into dedicated use-case
  modules.
- Keep public `qwen-train` command names and flags stable.
- Keep bundle validation, path policy, and detached-runtime invocation out of
  the CLI entrypoint file.

## Deliverables

- [x] `qwen_train.py` is reduced to parser wiring, command registry, and
  `main(argv)`.
- [x] Shared defaults and parser-building live outside the CLI entrypoint.
- [x] Launch, resume, eval, diagnose, schedule, status, and stop behavior are
  owned by dedicated control-plane use-case modules.
- [x] Scratch-root path-policy enforcement and bundle-contract validation are
  shared domain services rather than inline CLI helpers.

## Acceptance Criteria

- [x] `qwen_train.py` is at or below the Story 28 cap and no longer owns
  domain validation or orchestration logic.
- [x] The control-plane package exposes one bounded module per command family.
- [x] Existing `qwen-train` command behavior remains stable from the operator
  perspective, including `diagnose-non-finite`.
- [x] Focused tests cover the extracted command use cases without growing the
  CLI entrypoint test surface into another god file.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
