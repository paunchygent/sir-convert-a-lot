---
id: story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts
title: Swedish multi-speaker corpus, preprocessing, and evaluation for Qwen3-TTS
type: story
status: proposed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md
  - docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md
  - docs/backlog/tasks/task-111-add-asr-backed-transcript-relabeling-with-provenance-for-qwen-corpus-candidates.md
  - docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md
  - docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md
  - docs/reference/ref-qwen3-tts-swedish-corpus-curation-policy.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-research-map-2026-03-08.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - swedish
  - corpus
  - preprocessing
  - evaluation
---

Implementation slice with acceptance-driven scope.

## Objective

Define the Swedish multi-speaker data, preprocessing, and evaluation path needed
to move from a technically possible `Qwen3-TTS` fine-tune to a credible
general-language-support result.

## Scope

- Curate the planned Swedish corpus mix:
  - `KBLab/rixvox` as the dominant hours source,
  - `google/fleurs` Swedish as short clean utterances and held-out evaluation,
  - `KTH/waxholm` as additional held-out Swedish speech and smoke data.
- Make transcript-quality and speaker-quality filtering explicit, especially for
  `rixvox`.
- Define one reviewable manifest/output shape that the official Qwen
  `prepare_data.py` flow can consume after Swedish preprocessing.
- Separate training data, dev data, held-out speaker data, and qualitative
  listening prompts.
- Publish the Hemma-versus-Colab comparison questions:
  - throughput,
  - checkpoint cadence,
  - runtime stability,
  - language quality,
  - held-out generalization.

## Tasks (Ordered)

1. `docs/backlog/tasks/task-105-build-qwen3-tts-swedish-finetuning-research-repomix-package.md`
1. `docs/backlog/tasks/task-102-curate-the-swedish-multi-speaker-corpus-for-qwen3-tts-language-expansion.md`
1. `docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md`
1. `docs/backlog/tasks/task-106-add-script-free-hugging-face-corpus-adapters-to-the-qwen-swedish-preprocessing-pipeline.md`
1. `docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md`
1. `docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md`
1. `docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md`
1. `docs/backlog/tasks/task-110-split-qwen-preprocessing-into-disk-backed-row-processing-and-finalization.md`
1. `docs/backlog/tasks/task-111-add-asr-backed-transcript-relabeling-with-provenance-for-qwen-corpus-candidates.md`
1. `docs/backlog/tasks/task-104-run-the-colab-h100-scaling-lane-and-publish-the-swedish-qwen3-tts-comparison.md`

## Acceptance Criteria

- [ ] Task 105 publishes the research map and repomix package that anchor the
  external evidence pass before the pilot subset is locked.
- [x] Task 102 defines the multi-speaker Swedish corpus policy and the first
  bounded training/dev/eval split.
- [x] Task 103 defines and implements the preprocessing/manifest pipeline
  needed for Swedish
  Qwen full-finetune runs.
- [x] Task 106 extends the first Task 103 slice to real `rixvox` / `fleurs` /
  labeled `waxholm` inputs through revision-pinned script-free adapters rather
  than deprecated dataset-script loading.
- [x] Task 107 proves the staged-public-corpus preprocessing bundle on Hemma
  and records the remaining `rixvox` blocker before `T101`.
- [ ] Task 108 resolves the `rixvox` audio-backed train-manifest blocker before
  the first bounded Hemma pilot.
- [x] Task 109 remediates the runtime-model drift so public-corpus
  preprocessing uses the selected Qwen container runtime rather than the Hemma
  host venv.
- [ ] Task 110 hardens the public-corpus lane into a disk-backed
  row-processing plus finalization pipeline before larger `rixvox` runs scale
  out.
- [ ] Task 111 defines a provenance-safe ASR relabeling lane without silently
  replacing source transcripts.
- [ ] Task 104 publishes the Colab H100 scaling lane and compares it against
  the Hemma pilot rather than treating it as an isolated notebook exercise.
- [ ] The story documents the difference between the official Qwen
  single-speaker training surface and this repo's planned multi-speaker Swedish
  language-expansion objective.

## Test Requirements

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] Corpus and preprocessing docs must name deterministic artifact locations
  under `build/verification/` or `build/reference/` before the story closes.

## Done Definition

The repo has one explicit Swedish multi-speaker training/evaluation plan for
Qwen `1.7B`, instead of only ad hoc notes about Swedish benchmarks or
single-speaker adaptation.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
