---
id: task-89-implement-benchmark-only-espeak-ng-preprocessing-for-chatterbox-swedish-lanes
title: Implement benchmark-only eSpeak NG preprocessing for Chatterbox Swedish lanes
type: task
status: completed
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-88-research-espeak-ng-phoneme-support-for-swedish-chatterbox-integration.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
  - docs/reference/ref-espeak-ng-swedish-phoneme-integration-for-chatterbox.md
labels:
  - chatterbox
  - espeak-ng
  - phonemes
  - benchmark
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement one benchmark-only eSpeak preprocessing path for Swedish Chatterbox
lanes without changing the current Chatterbox sidecar contract.

This task does not solve the full remaining Chatterbox quality problem. The
current repo still lacks:

- sentence splitting
- prosodic-boundary detection
- chunk batching
- chunk stitching or cross-fade

Those capabilities are now treated as required follow-up work for
quality-focused long-form output, separate from the narrower eSpeak
preprocessing experiment.

## PR Scope

- Add one separate helper image under `containers/` for eSpeak-backed
  phonemization.
- Add one committed Task 89 experiment runner on Hemma that:
  - writes the original Swedish probe text to an input artifact,
  - generates one phonemized Swedish text artifact through the helper image,
  - runs one baseline Chatterbox lane,
  - runs one eSpeak-preprocessed Chatterbox lane,
  - writes deterministic experiment reports.
- Keep the actual Chatterbox sidecar contract unchanged:
  - no new public or internal sidecar fields,
  - no direct phoneme mode added to `/synthesize`.
- Add only the minimum Task 86 surface expansion needed to support this
  experiment cleanly:
  - file-backed `--probe-text-file` input.
- Add targeted tests for the helper, Hemma runner, and orchestrator.
- Keep the scope bounded to preprocessing only:
  - do not silently add segmentation, batching, or stitching behavior inside
    this task.

## Result

Task 89 is now complete with live Hemma evidence under:

- `build/verification/task-89-chatterbox-espeak-hemma/`

Produced artifacts include:

- baseline text-input lane:
  `build/verification/task-89-chatterbox-espeak-hemma/baseline/`
- eSpeak-preprocessed lane:
  `build/verification/task-89-chatterbox-espeak-hemma/espeak_sv/`
- original input text:
  `build/verification/task-89-chatterbox-espeak-hemma/inputs/probe_text_original.txt`
- eSpeak output text:
  `build/verification/task-89-chatterbox-espeak-hemma/inputs/probe_text_espeak_sv.txt`
- eSpeak metadata:
  `build/verification/task-89-chatterbox-espeak-hemma/inputs/espeak_metadata.json`

Observed outcome:

- the helper path works
- both Hemma lanes synthesize successfully
- baseline normal-text input is qualitatively superior to the eSpeak lane for
  Chatterbox in the current repo shape
- the experiment does not remove the need for a separate segmentation,
  batching, and stitching slice

## Decision

For Chatterbox specifically, the repo will keep the eSpeak helper path only as
future reusable benchmark infrastructure for other models.

It is no longer part of the active Chatterbox quality path because:

- the official Chatterbox multilingual surface in this repo remains text-based
- Task 89 did not improve the Chatterbox result
- the next active quality slice is normal-text segmentation, batching, and
  stitching under `T90`

## Deliverables

- [x] Separate helper image for eSpeak-backed phonemization.
- [x] Committed Hemma experiment runner plus local orchestrator.
- [x] Deterministic Task 89 evidence bundle comparing:
  - baseline text-input lane,
  - eSpeak-preprocessed lane.
- [x] Updated runbook notes describing how the experimental path works.
- [x] Explicit documentation that the current Chatterbox path still lacks the
  segmentation-and-stitching layer needed for maximal-quality long-form output.

## Acceptance Criteria

- [x] The current Chatterbox sidecar contract remains text-based.
- [x] eSpeak preprocessing runs outside the Chatterbox sidecar container.
- [x] Task 89 produces one phonemized Swedish text artifact before Chatterbox
  inference.
- [x] Task 89 runs at least these two comparable lanes with the same reference
  clip and same Swedish probe text source:
  - baseline text input
  - eSpeak-preprocessed text input
- [x] Each lane writes deterministic evidence under `build/verification/`.
- [x] The experiment can be run through committed command surfaces rather than
  ad hoc terminal commands.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
