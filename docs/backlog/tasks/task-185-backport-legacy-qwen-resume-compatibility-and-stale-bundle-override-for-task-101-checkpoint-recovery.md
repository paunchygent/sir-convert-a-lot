---
id: task-185-backport-legacy-qwen-resume-compatibility-and-stale-bundle-override-for-task-101-checkpoint-recovery
title: Backport legacy Qwen resume compatibility and stale bundle override for Task 101 checkpoint recovery
type: task
status: active
priority: high
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training.md
  - docs/backlog/tasks/task-183-control-checkpoint-cadence-and-retention-for-scheduled-task-101-qwen-training.md
  - docs/backlog/tasks/task-184-remediate-task-101-qwen-schedule-pointer-truth-schedule-path-fail-closed-validation-and-retention-3-checkpoint-proof-coverage.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - hemma
  - checkpoint-recovery
---

Task 185 is the compatibility-and-recovery follow-up for the shipped Task 101
scheduled-control posture. It exists to recover the most advanced preserved
legacy training lane truthfully after control-plane hardening exposed that
pre-schedule launch metadata can no longer be resumed without explicit
compatibility handling.

## Objective

Restore truthful recovery support for the preserved Task 101 legacy lane by:

- backfilling safe defaults when older launch metadata lacks current required
  settings fields
- allowing operators to override a stale bundle root at resume time
- failing closed when the effective replacement bundle is missing or malformed
- requiring a standalone held-out eval baseline for the original
  `1236` checkpoint before any future training relaunch decision
- suppressing stale pre-resume status/report artifacts while a resumed launch is
  still warming up on the reused run root
- rejecting impossible saved intra-epoch resume cursors instead of silently
  translating them into a different epoch/batch posture
- preferring the newer compatible `1238` durable checkpoint as the canonical
  next strict resume target once the diagnostic recovery probe has produced it
- proving the behavior with regression tests before the Hemma retry

## PR Scope

- Backward-compatible launch metadata loading for legacy detached Qwen runs.
- Resume CLI support for overriding `pilot_bundle_root`.
- Standalone eval-before-resume operator posture for legacy checkpoint
  recovery.
- Fail-closed preflight validation of the effective bundle root before detached
  relaunch.
- Detached status inspection truthfulness for resumed running launches that
  reuse a prior run root.
- In-container trainer fail-closed validation for incompatible durable
  checkpoint resume cursors.
- Focused test coverage for legacy launch recovery and stale-bundle rejection.
- Docs/status updates for the recovery slice.

## Observed Behavior

Good behavior confirmed on `2026-03-15`:

- The legacy `1236`-step checkpoint can now be launched again without manual
  launch JSON edits.
- The resume CLI can redirect the run to a live replacement bundle root under
  `/srv/scratch/.../direct-encode-chunk64-span1`.
- The resumed container restored the trainer state and wrote a new durable
  checkpoint at optimizer step `1238`.
- Standalone held-out eval against the original `1236` checkpoint completed on
  the replacement eval manifest with `eval_loss=6.440637648105621` across
  `8` eval batches.
- After the Hemma pull of the stale-artifact inspection fix, the stopped
  resumed launch no longer surfaces the old failed `report.json`.

Bad or unsafe behavior observed on the same recovery attempt:

- The reused run root initially surfaced a stale failed `report.json` from the
  earlier broken resume attempt, which could mislead operators during active
  monitoring.
- The saved durable checkpoint cursor carried `next_step_in_epoch=1236` while
  the replacement bundle reported `dataloader_length=128`. The trainer did not
  fail closed, so the resumed run temporarily passed through a strange
  partial-epoch posture before normalizing at the next durable save.
- The resumed run was relaunched before capturing a clean standalone held-out
  eval baseline for the `1236` checkpoint, leaving operators without a proper
  pre-resume reference point.

## Remediating Actions

- Keep the stale-artifact filtering fix in detached status inspection and pull
  it to Hemma only after the active resumed container is fully stopped.
- Add a trainer-side compatibility guard that refuses any resume whose saved
  `next_step_in_epoch` exceeds the current dataloader length.
- Run `qwen-train eval` against the `1236` checkpoint before any next detached
  training relaunch decision.
- Treat the short `1236 -> 1238` recovery attempt as diagnostic evidence, not
  as trustworthy acceptance or throughput evidence.
- Do not let a preserved legacy launch silently carry forward stale
  checkpoint/eval/retention posture when operators are intentionally promoting
  that lane onto the current scheduled contract.
- Use the newer durable checkpoint `state-step-00001238` as the canonical next
  strict resume target instead of rolling back to `1236`.
- Track live recovery and future train/eval progress in
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
  rather than in skill-doc operational notes.

## Deliverables

- [x] Legacy detached launch metadata can be loaded even when
  `throughput_profile_label` is absent.
- [x] `qwen-train resume` accepts `--pilot-bundle-root` and applies it to the
  resumed launch settings.
- [x] Resume fails before launch when the effective bundle root is missing or
  incomplete.
- [x] Resumed running launches do not surface stale pre-resume `status.json` or
  `report.json` payloads as if they described the current container.
- [x] Regression tests cover both successful override-based recovery and
  fail-closed stale-bundle behavior.
- [x] A bounded Hemma diagnostic resume probe is retried against the
  `1236`-step checkpoint after local verification passes.
- [x] The trainer rejects impossible saved resume cursors for the current
  bundle length.
- [x] A standalone held-out eval baseline is recorded for the `1236`
  checkpoint before the next training relaunch.
- [ ] `qwen-train resume` can override checkpoint/eval cadence and retention
  when a preserved legacy lane must be promoted onto the current scheduled
  contract.
- [ ] The canonical next relaunch targets the compatible `1238` durable
  checkpoint rather than reusing the incompatible legacy cursor from `1236`.
- [x] Live recovery progress is tracked in a dedicated reference document.

## Acceptance Criteria

- [x] The preserved legacy lane can be recovered without manual launch JSON
  editing.
- [ ] Operators receive a clear bundle-integrity or missing-path failure before
  any detached container launch if the bundle override is wrong.
- [ ] Detached status/report inspection does not contradict the active resumed
  container with pre-resume artifacts from the reused run root.
- [ ] The trainer fails closed when a saved durable checkpoint cursor is
  impossible for the current bundle length.
- [x] Operators have a clean standalone eval baseline for the checkpoint being
  considered for relaunch.
- [ ] Operators can promote a preserved legacy lane onto the current
  `500/100/3` control posture without editing launch JSON by hand.
- [ ] The canonical next relaunch uses the newer compatible `1238` checkpoint
  instead of resetting to `1236`.
- [ ] The compatibility fallback does not change current canonical launch
  defaults for new runs.
- [ ] Focused Qwen training orchestration tests pass with the new compatibility
  coverage.

## Checklist

- [ ] Implementation complete
- [x] Validation complete
- [x] Hemma resume retried
- [x] Standalone eval baseline captured
- [x] Docs updated
- [ ] Strict `1238` relaunch complete
