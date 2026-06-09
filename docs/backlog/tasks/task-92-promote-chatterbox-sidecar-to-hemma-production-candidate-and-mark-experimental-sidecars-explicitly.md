---
id: task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly
title: Promote Chatterbox sidecar to Hemma production candidate and mark experimental sidecars explicitly
type: task
status: in_progress
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-91-implement-speech-aware-chatterbox-stitching-and-tail-cleanup-on-hemma.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
labels:
  - tts
  - chatterbox
  - production-candidate
  - experimental
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Promote the Chatterbox sidecar to the repo's explicit Hemma production
candidate for TTS work while marking the other TTS-related containers as
experimental benchmark or helper surfaces that must not be deployed as Hemma
production services.

## PR Scope

- Mark `containers/tts-sidecar-chatterbox/` as the current Hemma
  production-candidate sidecar surface.
- Mark `containers/tts-sidecar-openvoice/`, `containers/tts-sidecar-f5/`, and
  `containers/textprep-espeak-phonemizer/` as experiment-only surfaces.
- Update repo docs so the production-vs-experimental boundary is explicit in:
  - backlog planning,
  - Hemma operations guidance,
  - Chatterbox tuning guidance,
  - container-local metadata or documentation.
- Keep the main service boundary unchanged:
  - TTS still stays sidecar-only,
  - no in-process runtime move into the main Sir Convert-a-Lot service.

## Deliverables

- [x] Task doc that records the production-candidate decision boundary.
- [x] Container-local documentation for lifecycle and deployability.
- [x] Explicit metadata or comments in each TTS-related Dockerfile.
- [x] Runbook updates that state:
  - Chatterbox is the current Hemma production candidate,
  - benchmark/helper containers are not Hemma production deploy targets.

## Acceptance Criteria

- [x] The repo has one explicit Hemma production-candidate TTS container.
- [x] The experiment containers are clearly marked as non-deployable for Hemma
  production service work.
- [x] Story 22 and Epic 07 planning now point to Chatterbox as the active
  production-candidate sidecar path.
- [x] Hemma operations docs no longer leave the Chatterbox-vs-experimental
  deployment boundary implicit.

## Implementation Notes

The current repo decision is:

- `containers/tts-sidecar-chatterbox/` is the only current Hemma
  production-candidate TTS sidecar image in this repo
- `containers/tts-sidecar-openvoice/` remains benchmark-only
- `containers/tts-sidecar-f5/` remains benchmark-only
- `containers/textprep-espeak-phonemizer/` remains helper-only

This task does not claim that the public v2 `md -> wav` delivery path is fully
finished. It only makes the internal sidecar lifecycle boundary explicit so the
repo stops treating all TTS images as equally deployable.

## Validation

- `pdm run pytest-root tests/sir_convert_a_lot/test_chatterbox_speech_aware_stitching_experiment.py tests/sir_convert_a_lot/test_tts_sidecar_chatterbox_segmented_generation.py`
- `pdm run typecheck-all`
- `pdm run validate-tasks`
- `pdm run validate-docs`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
