---
id: task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405
title: Debug the Task 101 pre-clip text-embedding gradient failure at step 1405
type: task
status: in_progress
priority: high
created: '2026-03-15'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/backlog/tasks/task-186-remediate-task-101-optimizer-boundary-corruption-and-deterministic-failure-replay.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/backlog/current.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - rca
  - gradients
  - diagnostics
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Use the bounded no-projection RCA checkpoints at optimizer steps `1401` and
`1406` to identify why the preserved Task 101 lane remains numerically
unstable, including:

- the original `1405` boundary that now no longer reproduces from the exact
  `1401` capture checkpoint
- the new continuation failure at optimizer step `1417`
- the text-embedding rows and upstream backward surfaces that first become
  non-finite when the lane re-enters instability

## PR Scope

- Add one committed RCA surface for bounded no-projection failure windows that
  can report, for a failing optimizer step such as `1405` or `1417`:
  - token ids used by each microbatch in the accumulated `801-804` window
  - text previews / decoded token context for the failing rows
  - the exact `text_embedding` row ids that first become non-finite
  - whether `input_text_embedding` gradients become non-finite before the
    parameter gradient does
  - whether the corruption is already present on an individual microbatch or
    only after accumulation across the full optimizer step
- Keep the new RCA logic bounded and reusable rather than embedding more ad
  hoc analysis inside the live training loop.
- Reuse the truthful no-projection lane and the new `pre_clip` guard surfaces
  instead of reopening the projection-enabled experiment or treating the
  `1406` continuation checkpoint as a new mainline checkpoint.
- Update operator docs with the new narrowing conclusion once the RCA artifact
  exists.

## Experiment Strategy

Use a two-tier debugging posture so we stop paying the full `1238 -> 1405`
replay cost for every hypothesis:

1. Mint one reusable near-boundary diagnostic state.
1. Reuse that state for many cheap micro-window experiments around the failing
   optimizer step.

The intended implementation shape is:

- Add one committed surface that can mint a reusable diagnostic state on the
  clean side of the known boundary with an automated step threshold rather than
  manual timing.
- Persist enough deterministic replay context that later experiments can run
  only the failing window rather than the whole lane:
  - checkpoint identity
  - optimizer step / train iteration boundaries
  - failing microbatch provenance rows
  - token ids / decoded text context for each microbatch
- Run bounded micro-window experiments from that state:
  - original `1405` accumulation window `801-804`
  - new `1417` accumulation window `849-852`
  - prefix windows inside the active failing window
  - single-row ablations or substitutions once the bad token rows are known
- Treat the reusable near-boundary state as the expensive artifact and each
  micro-window replay as the cheap iteration surface.

Hypotheses to test with that workflow:

- row-specific hypothesis:
  one or more token rows drive the first non-finite
  `text_embedding.weight.grad`
- upstream-backward hypothesis:
  `input_text_embedding` gradients go non-finite before the parameter gradient
- accumulation hypothesis:
  the bad gradient appears only after accumulation across a full optimizer
  step window such as `801-804` or `849-852`, not on any single microbatch
  alone
- stability-drift hypothesis:
  the exact `1401 -> 1406` replay staying finite while the bounded
  continuation fails at `1417` means the instability is not tied to one fixed
  deterministic step number and should be treated as a re-emerging numerical
  cliff, not a single permanently bad row
- token-context hypothesis:
  the failing rows correspond to a small token/context family that can be
  identified from decoded text and replayed cheaply

## Non-Goals

- Do not restart the projection-enabled training experiment.
- Do not broaden this task into LR sweeps or general hyperparameter search.
- Do not treat clipping as the active suspect unless new evidence contradicts
  the current `pre_clip` proof.

## Deliverables

- [ ] One committed plan surface exists for minting a reusable near-boundary
  diagnostic state with automated stop-by-step control rather than manual
  sleep-based timing.
- [ ] One machine-readable RCA artifact maps the first non-finite
  `text_embedding` gradient rows at the active failing optimizer step to token
  ids and human-readable text context from the failing microbatch window.
- [ ] One machine-readable RCA artifact records whether the first non-finite
  backward surface appears on `input_text_embedding` gradients before the
  parameter gradient itself.
- [ ] One bounded proof or deterministic replay shows whether the corruption is
  already present on a single microbatch or only after accumulation across the
  full optimizer step.
- [ ] One cheap replay workflow exists for rerunning only the failing
  micro-window or its prefixes from the reusable near-boundary state.
- [ ] Operator docs record the narrowed root-cause conclusion and the next
  remediation direction without demoting the preserved Task 101 lane.

## Acceptance Criteria

- [ ] A focused test proves the new RCA surface can emit token/row attribution
  without depending on live ad hoc inspection.
- [ ] A focused test proves the RCA surface can distinguish:
  - non-finite `input_text_embedding` gradient before parameter-gradient
    corruption
  - parameter-gradient corruption with still-finite forward activations
  - accumulation-only corruption versus single-microbatch corruption
- [ ] A focused test proves the near-boundary diagnostic state can be reused to
  run a bounded micro-window replay without re-running the full `1238 -> 1405`
  lane.
- [ ] One bounded Hemma or deterministic replay artifact for optimizer step
  `1405` or `1417` captures:
  - the failing microbatch ids / provenance rows
  - the first non-finite text-embedding row ids
  - the associated token ids / decoded text context
  - whether the first bad backward surface is pre-parameter or parameter-level
- [ ] The resulting operator conclusion is specific enough to choose the next
  remediation without another blind training retry.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_optimizer_guard.py tests/sir_convert_a_lot/ml/qwen/training/test_diagnostic_replay.py tests/sir_convert_a_lot/ml/qwen/training/test_train_step_runtime.py`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] One bounded Hemma or deterministic replay RCA proof persists the
  active token/row attribution artifact.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
