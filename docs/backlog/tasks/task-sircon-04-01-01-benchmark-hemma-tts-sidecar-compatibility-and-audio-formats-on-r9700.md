---
type: task
id: TASK-SIRCON-04-01-01
title: Benchmark Hemma TTS sidecar compatibility and audio formats on R9700
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-04-01
task_kind: story
acceptance_criteria:
- Sidecar boots on Hemma with documented Python/runtime versions.
- Hemma evidence records the live GPU identity (`R9700`, `gfx1201`) and runtime truth.
- '`/v1/audio/speech` succeeds with `wav`.'
- Benchmark output explicitly records whether compressed audio formats are supported
  on Hemma.
- Benchmark output explicitly records whether Triton flash attention was enabled.
- The task makes an explicit recommendation on the highest supported Python version
  observed in practice; if `3.14` is unsupported, the evidence records why.
retired_ids:
- task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700
---


## Context

State the bounded implementation or proof need and the parent story behavior it
supports.

## Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

## Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

## Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

## Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

## Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

## Source Body Preservation

PR-sized execution unit; may be linked to a story or standalone.
## Objective
Prove that the chosen sidecar stack can run on the real Hemma AMD Radeon AI PRO R9700 (`gfx1201`) host and record audio-format evidence before the service contract is implemented.
## PR Scope
- Add a committed benchmark/smoke surface that:
  - starts the TTS sidecar in an isolated Linux container/runtime,
  - targets Python `3.12` or newer when upstream dependencies support it,
  - verifies sidecar readiness and internal-network accessibility from Sir Convert-a-Lot,
  - exercises `/v1/audio/speech` and `/v1/audio/voices`,
  - captures `wav` output and records compressed-format availability (`mp3` and/or equivalent).
- Capture deterministic evidence under `build/verification/` or `build/benchmarks/`.
- Update the Hemma runbook with the canonical benchmark command and rollback notes.
## Deliverables
- [x] Committed benchmark/smoke command surface.
- [ ] Deterministic Hemma evidence artifacts for startup/runtime/output-format checks.
- [ ] Runbook guidance for the sidecar benchmark flow.
## Canonical Command Surface
Local entrypoint:
`pdm run benchmark:tts-sidecar`
Remote Hemma execution:
`pdm run run-hemma -- pdm run benchmark:tts-sidecar`
Current command defaults:
- image: `vllm/vllm-omni-rocm:v0.16.0`
- CustomVoice model: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- Base clone model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
- host HF cache:
`${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/huggingface}`
- compatibility mount when Docker cannot bind `/srv/*` directly:
`${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT:-/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface}`
- stage config:
`scripts/sir_convert_a_lot/devops/qwen3_tts_stage_config.yaml` (mirrors the current upstream `qwen3_tts.yaml` schema)
- output root: `build/verification/task-79-hemma-tts-sidecar/`
- response formats: `wav,mp3`
- network contract:
  - sidecar joins `hule-network`
  - service-container reachability is verified from `sir_convert_a_lot_prod`
- container cache env contract:
  - `HF_HOME=/cache/huggingface`
  - `HF_HUB_CACHE=/cache/huggingface/hub`
  - `TRANSFORMERS_CACHE=/cache/huggingface`
  - `VLLM_USE_TRITON_FLASH_ATTN=1` by default
- tokenizer prefetch contract:
  - `Qwen/Qwen3-TTS-Tokenizer-12Hz` is prefetched into the shared cache
  - tokenizer files are mirrored into the model snapshot `speech_tokenizer/` path expected by
the live `vllm-omni` stage-1 loader
- request-evidence contract:
  - `inputs/probe_text.txt`
  - `inputs/instructions.txt` when style instructions are used
  - `inputs/reference_audio.wav` when the Base clone lane is used
  - `inputs/reference_transcript.txt` when the Base clone lane is used
The benchmark writes:
- `report.json`
- `report.md`
- `docker_logs.txt`
- `artifacts/sample.wav` on success
- `artifacts/sample.mp3` when compressed output is supported
- `failure.txt` when the run fails before acceptance completes
Task 98 extends this benchmark with the official Qwen Base clone lane:
- `task_type=Base`
- `ref_audio`
- `ref_text`
- `instructions`
The clone lane keeps the same canonical `benchmark:tts-sidecar` command surface and does not introduce a parallel ad hoc benchmark script.
## Acceptance Criteria
- [ ] Sidecar boots on Hemma with documented Python/runtime versions.
- [ ] Hemma evidence records the live GPU identity (`R9700`, `gfx1201`) and runtime truth.
- [ ] `/v1/audio/speech` succeeds with `wav`.
- [ ] Benchmark output explicitly records whether compressed audio formats are supported on Hemma.
- [ ] Benchmark output explicitly records whether Triton flash attention was enabled.
- [ ] The task makes an explicit recommendation on the highest supported Python version observed
in practice; if `3.14` is unsupported, the evidence records why.
## Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [x] Docs updated

