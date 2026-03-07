---
id: task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export
title: Remediate Task 81 OpenVoice benchmark root causes and evidence export
type: task
status: completed
priority: high
created: '2026-03-06'
last_updated: '2026-03-06'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-81-benchmark-openvoice-v2-swedish-probable-cloning-sidecar-on-hemma.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - remediation
  - root-cause
  - tts
  - sidecar
  - hemma
  - openvoice
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the root-cause blockers that still prevent `T81` from producing end-to-end validated
Hemma evidence, without widening scope beyond the OpenVoice sidecar benchmark lane.

## PR Scope

- Remediate only the failures that block `T81` acceptance:
  - the remaining setup-artifact collection gap after synthesize succeeds,
  - declared-and-now-satisfied Torch/Silero cache/runtime behavior that must stay true,
  - missing deterministic setup-artifact evidence after a corrected rerun,
  - the need to preserve atomic partial-vs-failed-vs-complete benchmark status.
- Keep all changes sidecar-only and benchmark-only:
  - do not touch the main Sir Convert-a-Lot service image,
  - do not weaken ADR-0007's normalized sidecar contract.
- Record the reasoning behind each implementation change so the next remediation step does not
  repeat the same mistakes.

## Root Cause Map

- Root cause 1: upstream helper coupling
  - `openvoice.se_extractor` hard-imports `faster-whisper` even when we only need the VAD path.
  - That pulled in `PyAV` and broke Hemma sidecar builds on Python `3.12`.
- Root cause 2: incomplete replacement dependency chain
  - after removing `faster-whisper`, the VAD path still required `torchaudio` and
    `onnxruntime` through `whisper-timestamped`.
  - This caused the first corrected rerun to fail inside `/synthesize` despite a healthy sidecar.
- Root cause 3: the evidence bundle is not atomic per rerun
  - this was true in the earlier evidence pack and blocked reliable review.
  - current `HEAD` has now disproved that failure mode by emitting one atomic partial bundle for
    `run_id=20260306T220740Z`.
- Root cause 4: the VAD runtime/cache surface is still under-declared
  - `whisper-timestamped` pulls Silero VAD through Torch Hub into container-local state unless we
    explicitly declare and persist that cache path.
  - this was true on the earlier rerun and is now fixed by removing `whisper-timestamped` from the
    active VAD path and loading Silero directly from the canonical Torch cache.
- Root cause 5: benchmark completion and machine-readable status are underspecified
  - this was true in the earlier harness and is now fixed on current `HEAD`.
  - the current report schema now distinguishes full success, partial evidence, and fatal
    benchmark failure in one machine-readable payload.
- Root cause 6: the current-head blocker has moved from synthesize into setup-artifact collection
  - the current rerun now reaches `/synthesize` successfully and writes `sample_sv.wav`,
  - but `processed_reference_dir`, `base_output_path`, and `converter_input_path` are still
    missing in the atomic report.
- Root cause 7: the benchmark still needs a deterministic artifact trail for the corrected setup
  - one final WAV alone is not enough to validate the corrected OpenVoice path.

## Reasoned Remediation Changes

- Replace the upstream reference-prep import with a committed local VAD-only helper.
  - Reason: we only need the OpenVoice-compatible VAD path, not the unsupported Whisper-splitting
    path that forces `faster-whisper` and `PyAV`.
- Add only the runtime dependencies required by the real VAD path on Hemma.
  - Reason: `torchaudio` and `onnxruntime` are the documented minimum for
    `whisper-timestamped` VAD; broader stacks increase fragility without helping this benchmark.
- Remove `whisper-timestamped` from the active reference-preprocessing path and use direct local
  Silero VAD loading from the canonical Torch cache.
  - Reason: the installed `whisper-timestamped==1.14.2` path still hardcodes
    `~/.cache/torch/hub/...`, so the clean fix is to stop depending on that path rather than
    wiring legacy cache expectations into the sidecar.
- Re-focus the remaining remediation on setup-artifact collection, not synthesis.
  - Reason: current `HEAD` now proves `/synthesize` succeeds, so the missing processed-reference
    and base/converter artifacts are the only remaining blocker before listening review.
- Declare the Torch/Silero cache surface under the canonical Hemma cache tree.
  - Reason: canonical cache reuse is not fully true while the runtime still resolves the Silero
    repo assertion through an undeclared default path.
- Keep the remediation sidecar-only.
  - Reason: the failures are specific to the OpenVoice benchmark image and harness, not the main
    production service.
- Make each rerun emit one atomic evidence bundle with one repo head and one timestamp family.
  - Reason: reviewers must be able to audit one benchmark attempt without mixing old reports and
    later failures.
- Add top-level benchmark/evidence status fields to the report payload.
  - Reason: partial-vs-failed-vs-complete state must be machine-readable, not only described in
    prose or a separate `failure.txt`.
- Re-prove the current export failure on current `HEAD` before changing the export path again.
  - Reason: current code and preserved failure text disagreed, so the next code change had to
    target a reproduced current defect rather than a stale assumption.
- Record the disproved export failure as a completed remediation step and move the remaining work
  to the synthesize-stage Torch Hub mismatch.
  - Reason: once current `HEAD` disproves the old blocker, keeping export as the headline problem
    would mislead the next fix.
- Preserve failed baselines rather than overwrite them.
  - Reason: remediation needs explicit before/after evidence, not moving targets.
- Preserve reference-input identity plus setup artifacts inside the deterministic evidence bundle.
  - Reason: the next reviewer must be able to verify which exact input and setup path produced one
    output without relying on unstored local state.

## Deliverables

- [x] Committed sidecar/harness remediation linked from `T81`.
- [x] Updated `T81` evidence path so one successful rerun emits:
  - one atomic `report.json`,
  - one atomic `report.md`,
  - one atomic `docker_logs.txt`,
  - one atomic benchmark status,
  - `report.json`,
  - `report.md`,
  - `docker_logs.txt`,
  - `artifacts/sample_sv.wav`,
  - processed-reference artifacts,
  - Swedish base artifacts before cloning,
  - reference-input identity evidence,
  - and no longer leaves `failure.txt` once the current setup-artifact blocker is cleared.
- [x] Task-level reasoning notes kept in sync with the implementation so reviewers can see why
  each change exists.

## Acceptance Criteria

- [x] The OpenVoice sidecar no longer depends on the unsupported `faster-whisper` / `PyAV`
  build path on Hemma Python `3.12`.
- [x] The VAD reference-prep path has the minimum runtime dependencies required to complete one
  cloning request on Hemma.
- [x] The benchmark records one machine-readable benchmark/evidence status for:
  - full success,
  - partial evidence,
  - fatal failure.
- [x] The benchmark declares and persists the Torch/Silero cache path under the canonical Hemma
  cache tree.
- [x] The current export failure is reproduced or disproved against current `HEAD` before any
  further export-path reasoning is treated as canonical.
- [x] Current `HEAD` disproves the old export failure as the active blocker.
- [x] The declared Torch/Silero cache path is also the runtime path used by the active VAD logic.
- [x] `T81` can complete end-to-end with one atomic evidence bundle containing the required setup
  artifacts and final report files.
- [x] The remediation task records the reasoning behind each implementation change, not just the
  resulting code diff.

## Closeout Notes

- The successful Hemma rerun on `61b263cab56118677dc47810b615daaf0adbe463` now proves:
  - one atomic complete evidence bundle (`run_id=20260306T224057Z`),
  - canonical Torch/Silero cache truth without legacy path wiring,
  - processed-reference, base-output, converter-input, and cloned artifacts all preserved.
- Remaining work is qualitative and belongs back in `T81`:
  - listening review of the corrected sample,
  - recommendation on whether OpenVoice remains the lead backend candidate.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
