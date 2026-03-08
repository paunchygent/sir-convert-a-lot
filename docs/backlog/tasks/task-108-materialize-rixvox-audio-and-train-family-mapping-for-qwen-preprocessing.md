---
id: 'task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing'
title: 'Materialize RixVox audio and train-family mapping for Qwen preprocessing'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md
  - docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - rixvox
  - preprocessing
  - audio
  - swedish
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extend the committed Qwen Swedish preprocessing lane so `rixvox` moves from
metadata-only inventory into real audio-backed train-family manifests before
the first bounded Hemma pilot fine-tune.

## PR Scope

- Stage revision-pinned `rixvox` audio assets on Hemma's DATA-backed storage.
- Materialize real `source_audio_locator` values for admitted `rixvox` rows.
- Add the missing train-family mapping for admitted `rixvox` train rows:
  - `swedish_smoke_train`
  - `swedish_pilot_train`
  - `swedish_scaleup_train`
- Keep `fleurs` and labeled `waxholm` in control/eval roles only.
- Preserve the deterministic Task 103 artifact and report contract.

## Deliverables

- [ ] One committed `rixvox` audio materialization surface.
- [ ] One committed train-family mapping path for admitted `rixvox` train rows.
- [ ] One live Hemma evidence bundle that proves real `rixvox` audio-backed
      train manifests exist before `T101`.

## Acceptance Criteria

- [ ] `rixvox` audio is staged on Hemma without dataset-script loading.
- [ ] The preprocessing lane produces admitted audio-backed `rixvox` rows, not
      just inventory metadata.
- [ ] The canonical train-family manifests are non-empty for the first bounded
      Hemma pilot lane.
- [ ] The current `fleurs` and `waxholm` control/eval separation is preserved.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
