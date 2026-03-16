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
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
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

Current narrowed RCA after the bounded `1406 -> 1418` replay:

- the `1417` failure is reproducible from the exact `1406` checkpoint
- the first bad backward surface is `input_text_embedding.grad` on train
  iteration `851`, before the sync-boundary `grad_norm` failure at `852`
- the failing `851` sample goes non-finite across `507` of `508` token
  positions; the only finite token position is the last one, which matches the
  train-step `inputs_embeds[:, :-1, :]` slice dropping the terminal token from
  the active forward path
- the resulting parameter-gradient corruption is not row-arbitrary: the `93`
  poisoned `text_embedding.weight` rows match the `93` unique token ids present
  in the failing `851` sample
- the strongest structural amplifier is the active codec-span text pad surface:
  the failing sample contains `375` repeats of token id `151671`, which is the
  repeated text-channel pad token written across the codec span by the current
  Qwen batch contract
- that codec-span text-pad surface is not a repo-local projection mistake; the
  public upstream Qwen `finetuning/dataset.py` uses the same
  `text_embedding_mask[: 8 + text_ids_len + codec_ids_len] = True` pattern, so
  the current risk surface is upstream-compatible and must be counteracted
  deliberately rather than dismissed as local drift

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
- codec-span pad amplification hypothesis:
  keeping the text-channel pad token active across the codec span amplifies the
  text-embedding backward path enough that long accumulated windows eventually
  push the whole active sequence non-finite

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
- [ ] One remediation order is recorded for the next bounded proof before any
  fresh training restart is attempted.

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
- [ ] The resulting remediation order explicitly distinguishes:
  - the primary structural countermeasure to test first on the `1406` replay
    window
  - the secondary accumulation/optimization ablations to test only if the
    primary countermeasure does not resolve the instability

## Current RCA Conclusion

What is now proven:

- the instability is not caused first by `clip_grad_norm_` or `optimizer.step()`
- the first bad backward event in the reproducible `1417` replay is on
  `input_text_embedding.grad` for microbatch `851`
- that bad microbatch poisons the accumulated `text_embedding.weight.grad`
  rows, and the following microbatch `852` inherits that poisoned parameter
  gradient even though its own `input_text_embedding.grad` remains finite
- the failure is sequence-level, not one-token local: nearly the entire active
  `851` token sequence goes non-finite in backward

What is now the leading structural cause:

- the training contract keeps the text embedding active across the codec span,
  where the text channel is filled with the repeated pad token
- on the failing `851` sample that means `375` repeated pad-token positions are
  still part of the active text-embedding path
- that repeated pad surface appears to be the dominant multiplier that turns a
  long accumulated window into a sequence-level backward blow-up

What should be tested before the next restart:

1. Primary countermeasure:
   narrow the active `text_embedding_mask` to the true text span only, or
   equivalently zero/detach the codec-span text-pad positions, then replay the
   bounded `1406 -> 1418` window again.
1. Secondary ablation:
   if the mask-only proof is not enough, reduce
   `gradient_accumulation_steps` for the same bounded replay window to
   determine how much of the remaining instability is accumulation pressure
   rather than structural pad amplification.
1. Tertiary mitigation:
   only after the first two proofs, consider narrower numeric mitigations such
   as a smaller text-embedding learning rate or row-specific sanitization for
   diagnostic purposes.

Story handoff:

- `T194` remains the canonical RCA source task for the reproducible
  `state-step-00001406 -> 1417` instability.
- Story 29 / `T195-T199` now owns the mitigation proof, fallback gate, and
  clean-restart decision built on this RCA.

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
