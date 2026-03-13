---
id: task-155-refactor-qwen-checkpoint-and-task-101-pilot-god-files-into-srp-modules
title: Refactor Qwen checkpoint and Task 101 pilot god files into SRP modules
type: task
status: completed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-115-add-fault-tolerant-resumable-qwen-training-checkpoints-on-hemma.md
  - docs/backlog/tasks/task-153-retain-only-bounded-durable-qwen-training-checkpoints-and-guard-scratch-capacity-on-hemma.md
  - docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md
labels:
  - qwen
  - finetuning
  - refactor
  - checkpoints
  - srp
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Reduce the active Qwen training and Task 101 pilot god files back toward
repo-aligned SRP boundaries by extracting durable-checkpoint policy/persistence
from the patched trainer entrypoint, detached-launch metadata/path/status logic
from the pilot launcher, and the remaining runtime/probe helper logic from the
Task 101 execution surfaces, without changing runtime behavior.

## Why This Exists

`T154` repaired correctness regressions but deliberately left several oversized
or mixed-responsibility modules in place:

- `scripts/devops/qwen_finetuning_patches/sft_12hz.py` still mixes training
  orchestration, export behavior, durable-checkpoint policy, scratch-capacity
  guards, retention, resume cursor logic, and artifact writes in one module
- `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py` still
  mixes CLI parsing, launch/resume/stop orchestration, path conventions,
  metadata I/O, status rendering, and payload validation in one module
- `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py` still mixes
  data contracts, launch-id/path helpers, Docker command construction, detached
  launch orchestration, artifact loading, and Docker inspect parsing
- `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py` still mixes
  CLI parsing, environment/runtime introspection, report assembly, status
  payload assembly, and artifact writing inline

That state is still out of alignment with `RULE-010` / `RULE-070` and with the
story-level refactoring goal.

## PR Scope

- Extract the durable-checkpoint data model, path helpers, disk-space guard,
  metadata validation, pointer writes, and retention cleanup into one dedicated
  Qwen checkpoint module that the patched trainer imports.
- Keep exported model-checkpoint behavior inside the trainer entrypoint unless a
  separate clean module boundary becomes obvious during implementation.
- Extract Task 101 detached-pilot metadata parsing, path helpers, artifact
  writers, latest-pointer resolution, resume-checkpoint validation, and status
  markdown rendering into one dedicated module that the launcher imports.
- Extract Task 101 runtime data contracts and artifact/parsing helpers into
  dedicated modules so the runtime surface is primarily Docker command and
  detached-run orchestration.
- Extract Task 101 probe report/status payload assembly and JSON artifact
  helpers into one dedicated module so the probe remains focused on executing
  the inner training run.
- Preserve all current CLI flags, JSON artifact shapes, status markdown shape,
  resume compatibility defaults, and durable-checkpoint semantics.
- Update focused tests to prove the refactor did not change the external
  contracts.

## Non-Goals

- Do not redesign the training objective, checkpoint policy, or detached-launch
  workflow.
- Do not broaden this slice into dataloader/runtime optimization work owned by
  `T118`.
- Do not change operator-facing commands, artifact names, or checkpoint
  retention defaults.

## Deliverables

- [x] `sft_12hz.py` reduced to training/export orchestration with
  durable-checkpoint behavior moved into a dedicated module.
- [x] `run_task101_hemma_qwen_pilot.py` reduced to CLI/orchestration with
  metadata/path/status behavior moved into a dedicated module.
- [x] `task101_qwen_pilot_runtime.py` reduced to runtime orchestration with
  data-contract and artifact/parsing helpers moved into dedicated modules.
- [x] `task101_qwen_pilot_probe.py` reduced to inner-run orchestration with
  report/status payload assembly moved into a dedicated module.
- [x] Focused tests proving contract parity after the extraction.
- [x] Story/current-session docs updated to reflect the full SRP refactor
  slice.

## Acceptance Criteria

- [x] The new checkpoint module owns the durable-checkpoint metadata model,
  path conventions, free-space guard, save/validate/prune flow, and resume
  cursor logic currently embedded in `sft_12hz.py`.
- [x] The detached Task 101 metadata module owns launch/status/stop/latest
  artifact paths, JSON parsing helpers, latest-launch resolution,
  latest-checkpoint resolution, resume-path validation, and markdown rendering
  currently embedded in `run_task101_hemma_qwen_pilot.py`.
- [x] The new Task 101 runtime helper modules own the detached-run data
  contracts and the JSON/artifact/Docker-inspect parsing logic currently
  embedded in `task101_qwen_pilot_runtime.py`.
- [x] The new Task 101 probe helper module owns the status/report payload
  assembly and JSON artifact writing logic currently embedded in
  `task101_qwen_pilot_probe.py`.
- [x] `scripts/devops/qwen_finetuning_patches/sft_12hz.py`,
  `scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`,
  `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py`, and
  `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py` are all more
  orchestration-focused than before this task.
- [x] Focused tests still pass without changing the external Task 101 or Qwen
  checkpoint artifact contracts.
- [x] `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
  focused pytest, and docs validations pass.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_training_resume.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
