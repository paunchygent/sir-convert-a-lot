---
id: task-84-remediate-task-81-openvoice-benchmark-root-causes-and-evidence-export
title: Remediate Task 81 OpenVoice benchmark root causes and evidence export
type: task
status: in_progress
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
  - mixed and non-atomic evidence bundles that blur current run truth,
  - undeclared Torch/Silero cache/runtime dependencies on Hemma,
  - stale export-root-cause assumptions not yet re-proven on current `HEAD`,
  - missing machine-readable benchmark status for partial-vs-failed-vs-complete runs,
  - missing deterministic setup-artifact and reference-input evidence.
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
  - the checked-in `report.json` and `report.md` are from an earlier successful synthesis run,
    while `failure.txt` and `docker_logs.txt` reflect a later rerun that failed during setup-
    artifact export.
  - That means the current bundle is not a deterministic statement of one benchmark attempt.
- Root cause 4: the VAD runtime/cache surface is still under-declared
  - `whisper-timestamped` pulls Silero VAD through Torch Hub into container-local state unless we
    explicitly declare and persist that cache path.
  - This means current cache-reuse claims overstate how complete the canonical cache discipline is.
- Root cause 5: benchmark completion and machine-readable status are underspecified
  - a synthesized WAV is not enough to treat `T81` as validated evidence,
  - and the current report schema does not distinguish full success, partial evidence, or fatal
    benchmark failure in one machine-readable payload.
- Root cause 6: current export diagnosis is stale until re-proven on current `HEAD`
  - current source already routes debug-artifact extraction through a temporary host directory,
    while the preserved failure text points to direct writes into the repo artifact path.
  - That mismatch means the next export remediation must begin by proving the current failure
    against current code rather than assuming the old symptom still holds.

## Reasoned Remediation Changes

- Replace the upstream reference-prep import with a committed local VAD-only helper.
  - Reason: we only need the OpenVoice-compatible VAD path, not the unsupported Whisper-splitting
    path that forces `faster-whisper` and `PyAV`.
- Add only the runtime dependencies required by the real VAD path on Hemma.
  - Reason: `torchaudio` and `onnxruntime` are the documented minimum for
    `whisper-timestamped` VAD; broader stacks increase fragility without helping this benchmark.
- Declare the Torch/Silero cache surface under the canonical Hemma cache tree.
  - Reason: canonical cache reuse is not fully true while Silero VAD still downloads into
    undeclared container-local state.
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
  - Reason: current code and preserved failure text disagree, so the next code change must target
    a reproduced current defect rather than a stale assumption.
- Preserve failed baselines rather than overwrite them.
  - Reason: remediation needs explicit before/after evidence, not moving targets.
- Preserve reference-input identity plus setup artifacts inside the deterministic evidence bundle.
  - Reason: the next reviewer must be able to verify which exact input and setup path produced one
    output without relying on unstored local state.

## Deliverables

- [ ] Committed sidecar/harness remediation linked from `T81`.
- [ ] Updated `T81` evidence path so one successful rerun emits:
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
  - and no longer leaves `failure.txt` for the corrected export path.
- [ ] Task-level reasoning notes kept in sync with the implementation so reviewers can see why
  each change exists.

## Acceptance Criteria

- [ ] The OpenVoice sidecar no longer depends on the unsupported `faster-whisper` / `PyAV`
  build path on Hemma Python `3.12`.
- [ ] The VAD reference-prep path has the minimum runtime dependencies required to complete one
  cloning request on Hemma.
- [ ] The benchmark records one machine-readable benchmark/evidence status for:
  - full success,
  - partial evidence,
  - fatal failure.
- [ ] The benchmark declares and persists the Torch/Silero cache path under the canonical Hemma
  cache tree.
- [ ] The current export failure is reproduced or disproved against current `HEAD` before any
  further export-path reasoning is treated as canonical.
- [ ] `T81` can complete end-to-end with one atomic evidence bundle containing the required setup
  artifacts and final report files.
- [ ] The remediation task records the reasoning behind each implementation change, not just the
  resulting code diff.

## Immediate Execution Order

1. Correct `T81` so it describes the mixed evidence bundle honestly rather than treating it as one
   deterministic rerun.
1. Add machine-readable benchmark/evidence status plus declared Torch/Silero cache reporting.
1. Preserve reference-input identity and setup-artifact evidence in one deterministic output tree.
1. Reproduce or disprove the current export failure on current `HEAD` before altering export logic.
1. Close this remediation task only after `T81` emits one atomic evidence bundle for one rerun.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
