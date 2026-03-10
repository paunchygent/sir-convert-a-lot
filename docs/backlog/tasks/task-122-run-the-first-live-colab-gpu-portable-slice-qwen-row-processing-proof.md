---
id: 'task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof'
title: 'Run the first live Colab GPU portable-slice Qwen row-processing proof'
type: 'task'
status: 'active'
priority: 'high'
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - preprocessing
  - notebook
  - proof
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first live Colab GPU-backed portable-slice proof for Qwen Swedish
row-processing without violating the Hemma-first row-selection contract or the
canonical Task 103 run-root artifact contract.

## PR Scope

- Use a fresh Hemma-issued bounded `source-selection` run root for the proof.
- Build one deterministic portable slice bundle from that run root.
- Run the notebook-backed Colab proof against a GPU runtime with:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`
- Keep the proof limited to `rixvox train` row-processing only.
- Do not merge Colab spool state into the live Hemma run as part of this task.
- Record a concrete evidence bundle showing that Colab emitted the same Task
  103 row-processing artifact shape as Hemma.

## Deliverables

- [ ] One fresh Hemma `source-selection` proof run root for Colab use only.
- [ ] One portable slice bundle issued from that run root.
- [ ] One Colab notebook flow that can be executed top-to-bottom in a normal
  Colab UI session.
- [ ] One live Colab row-processing run root with canonical Task 103 artifacts.
- [ ] One verification summary comparing the Colab run-root shape against the
  Hemma row-processing contract.

## Acceptance Criteria

- [ ] The proof uses a fresh bounded source-selection universe, not the live
  Hemma `10k` selection.
- [ ] The proof slice is deterministic and unique within that bounded universe.
- [ ] Colab stages only the required raw files for its slice.
- [ ] Colab runs canonical Task 103 row-processing through
  `selected-source-records`.
- [ ] The Colab run root contains at least:
  - `inventory/`
  - `audio_24k/`
  - `spool/rows/`
  - `run.json`
  - `status.json`
- [ ] The notebook remains orchestration only, not a second preprocessing
  implementation.
- [ ] The proof records the exact Colab worker mix:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
- [ ] Live Colab proof complete
