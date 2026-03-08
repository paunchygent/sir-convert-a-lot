---
id: task-98-add-qwen-english-reference-clone-lane-to-hemma-benchmark
title: Add Qwen English reference clone lane to Hemma benchmark
type: task
status: completed
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-07-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/stories/story-22-hemma-sidecar-tts-audio-artifact-delivery.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - qwen
  - tts
  - benchmark
  - english
  - cloning
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extend the canonical Task 79 Hemma Qwen benchmark so it can exercise the
official Qwen3-TTS Base cloning path with an English reference clip, exact
reference transcript evidence, and bounded style instructions through the same
OpenAI-compatible `/v1/audio/speech` surface already proven on Hemma.

## PR Scope

- Keep the existing Task 79 sidecar benchmark as the single Qwen benchmark
  surface on Hemma.
- Add Base-task request support using the official Qwen/vLLM request fields:
  - `task_type=Base`
  - `ref_audio`
  - `ref_text`
  - `instructions`
- Add deterministic file-backed benchmark inputs for:
  - probe text
  - style instructions
  - reference transcript
  - prepared reference audio clip
- Record request-evidence metadata in the Task 79 report so clone runs are
  auditable after the fact.
- Prove one live English reference-clone run on Hemma and sync the evidence
  bundle back locally.

## Deliverables

- [x] Extended `benchmark:task-79` command surface for Qwen Base voice cloning.
- [x] Deterministic request-input evidence under one Task 98 output root.
- [x] Live Hemma English clone artifact generated from the approved reference
  clip plus the requested style instructions.
- [x] Runbook/task documentation updated to describe the Qwen Base clone lane.

## Acceptance Criteria

- [x] The benchmark supports both the existing CustomVoice lane and the new
  Base clone lane without ad hoc scripts.
- [x] Base clone runs require and record reference-audio plus reference
  transcript evidence.
- [x] The report records the effective task type, model id, language,
  instructions path, reference-audio path, and reference-audio digest.
- [x] A live Hemma run succeeds with the English reference clip and syncs the
  resulting evidence locally.

## Implementation Notes

- The canonical Qwen benchmark surface remains `benchmark:task-79`; the Base
  clone lane was added to that existing runner rather than a separate ad hoc
  script.
- Live Hemma evidence is recorded under:
  - `build/verification/task-98-qwen-english-reference-clone/`
- The clone run used:
  - model `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
  - `task_type=Base`
  - language `English`
  - reference clip
    `build/verification/task-98-qwen-english-reference-clone/inputs/reference_audio.wav`
  - reference transcript
    `build/verification/task-98-qwen-english-reference-clone/inputs/reference_transcript.txt`
  - style instructions
    `build/verification/task-98-qwen-english-reference-clone/inputs/instructions.txt`
  - probe text
    `build/verification/task-98-qwen-english-reference-clone/inputs/probe_text.txt`
- Verified runtime truth from `report.json`:
  - `synthesized_ok=true` via successful `wav` probe
  - output artifact `artifacts/sample.wav`
  - output duration `14.32` seconds
  - output sample rate `24000 Hz`
  - peak VRAM `11448381440` bytes
  - readiness `230.171` seconds
  - Python `3.12.12`

## Validation

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task79_hemma_tts_sidecar_benchmark.py tests/sir_convert_a_lot/test_task79_qwen3_tts_request_payload.py -q`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out /tmp/sir_tasks_index.md --fail-on-missing`
- `pdm run coverage-gate` was rerun but is still red because of the unrelated
  pre-existing failure in
  `tests/sir_convert_a_lot/test_benchmark_story20_parallel_throughput.py::test_run_benchmark_writes_expected_payload`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
