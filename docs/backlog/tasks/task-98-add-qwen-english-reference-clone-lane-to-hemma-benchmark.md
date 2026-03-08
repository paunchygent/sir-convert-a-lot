---
id: task-98-add-qwen-english-reference-clone-lane-to-hemma-benchmark
title: Add Qwen English reference clone lane to Hemma benchmark
type: task
status: in_progress
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

- [ ] Extended `benchmark:task-79` command surface for Qwen Base voice cloning.
- [ ] Deterministic request-input evidence under one Task 98 output root.
- [ ] Live Hemma English clone artifact generated from the approved reference
  clip plus the requested style instructions.
- [ ] Runbook/task documentation updated to describe the Qwen Base clone lane.

## Acceptance Criteria

- [ ] The benchmark supports both the existing CustomVoice lane and the new
  Base clone lane without ad hoc scripts.
- [ ] Base clone runs require and record reference-audio plus reference
  transcript evidence.
- [ ] The report records the effective task type, model id, language,
  instructions path, reference-audio path, and reference-audio digest.
- [ ] A live Hemma run succeeds with the English reference clip and syncs the
  resulting evidence locally.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
