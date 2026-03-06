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
  - broken dependency paths in the actual OpenVoice reference-prep runtime,
  - incomplete VAD runtime dependencies on Hemma,
  - benchmark evidence-export failures after successful synthesis.
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
- Root cause 3: evidence export is still coupled to a fragile host/container ownership boundary
  - the benchmark now synthesizes successfully and writes `report.json` plus `report.md`, but the
    setup-artifact export step can still fail with a host permission error while copying
    `base_sv.wav`.
  - That means the run produces partial evidence, but still records `failure.txt` and does not yet
    preserve the processed-reference and base-audio setup trail reliably enough for closeout.
- Root cause 4: benchmark completion and debug byproducts were conflated
  - a synthesized WAV is not enough to treat `T81` as validated evidence.
  - The run must complete with `report.json`, `report.md`, sidecar logs, and the setup artifacts.

## Reasoned Remediation Changes

- Replace the upstream reference-prep import with a committed local VAD-only helper.
  - Reason: we only need the OpenVoice-compatible VAD path, not the unsupported Whisper-splitting
    path that forces `faster-whisper` and `PyAV`.
- Add only the runtime dependencies required by the real VAD path on Hemma.
  - Reason: `torchaudio` and `onnxruntime` are the documented minimum for
    `whisper-timestamped` VAD; broader stacks increase fragility without helping this benchmark.
- Keep the remediation sidecar-only.
  - Reason: the failures are specific to the OpenVoice benchmark image and harness, not the main
    production service.
- Redesign debug artifact export so it does not depend on a fragile host/container ownership path
  into the repo worktree.
  - Reason: synthesis now succeeds and reporting now works, so the remaining blocker is narrow.
    The export path for processed-reference plus base-audio evidence must be as robust as the
    synth path or the benchmark cannot close cleanly.
- Preserve failed baselines rather than overwrite them.
  - Reason: remediation needs explicit before/after evidence, not moving targets.

## Deliverables

- [ ] Committed sidecar/harness remediation linked from `T81`.
- [ ] Updated `T81` evidence path so one successful rerun emits:
  - `report.json`,
  - `report.md`,
  - `docker_logs.txt`,
  - `artifacts/sample_sv.wav`,
  - processed-reference artifacts,
  - Swedish base artifacts before cloning,
  - and no longer leaves `failure.txt` for the corrected export path.
- [ ] Task-level reasoning notes kept in sync with the implementation so reviewers can see why
  each change exists.

## Acceptance Criteria

- [ ] The OpenVoice sidecar no longer depends on the unsupported `faster-whisper` / `PyAV`
  build path on Hemma Python `3.12`.
- [ ] The VAD reference-prep path has the minimum runtime dependencies required to complete one
  cloning request on Hemma.
- [ ] The benchmark no longer fails after successful synthesis because of artifact-export or
  ownership issues.
- [ ] `T81` can complete end-to-end with the required evidence artifacts and final report files,
  without a residual artifact-export failure.
- [ ] The remediation task records the reasoning behind each implementation change, not just the
  resulting code diff.

## Immediate Execution Order

1. Record the live post-synthesis export failure precisely in `T81`, including the fact that the
   run now writes `report.json` and `report.md` before failing.
1. Replace the fragile debug-artifact export path with one that is compatible with Hemma's Docker
   runtime and host permissions.
1. Rerun `T81` without rebuilding the sidecar image unless the image itself changed.
1. Close this remediation task only after `T81` emits full setup evidence and no longer leaves a
   residual export failure behind.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
