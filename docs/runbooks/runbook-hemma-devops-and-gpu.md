---
type: runbook
id: RUN-hemma-devops-and-gpu
title: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
status: active
created: '2026-02-11'
updated: '2026-05-17'
owners:
  - platform
system: hemma.hule.education
tags:
  - devops
  - hemma
  - gpu
  - sir-convert-a-lot
links:
  - .codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md
  - docs/runbooks/runbook-hemma-service-ops.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - docs/runbooks/runbook-answer-key-local-model-operator-guide.md
  - docs/runbooks/runbook-hemma-conversion-benchmarks.md
  - docs/runbooks/runbook-hemma-tts-sidecar-benchmarks.md
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
---

## Purpose

This is the doorway for Sir Convert-a-Lot Hemma operations. It routes to focused
runbooks and holds only the invariants that apply across service, GPU, model,
benchmark, and tunnel work.

## Route By Job

| Job | Read |
|---|---|
| Service placement, deploys, tunnels, health checks, prod env mirror | `docs/runbooks/runbook-hemma-service-ops.md` |
| GPU checks, scratch-backed caches, vLLM, llama.cpp, Docling GPU validation | `docs/runbooks/runbook-hemma-gpu-runtime.md` |
| Answer-key local model setup, GGUF switching, structured probes, lessons learned | `docs/runbooks/runbook-answer-key-local-model-operator-guide.md` |
| Conversion smoke tests, throughput, bottleneck triage | `docs/runbooks/runbook-hemma-conversion-benchmarks.md` |
| TTS sidecar and Swedish voice benchmark lanes | `docs/runbooks/runbook-hemma-tts-sidecar-benchmarks.md` |
| Public API or CLI contract behavior | `docs/converters/` and `docs/decisions/` |
| Local answer-key model selection and structured-output benchmark plan | `docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md` |

## Global Invariants

- Canonical remote repo: `/home/paunchygent/apps/sir-convert-a-lot`.
- Canonical Hemma command wrapper: `pdm run run-hemma -- ...`.
- `run-hemma` SSHes from client machines and runs directly when the current
  session is already in the canonical Hemma Server checkout.
- `pdm run run-hemma --shell ...` is for short probes that need shell syntax.
- Long-running Hemma work uses committed detached runners or supervised remote
  surfaces.
- Canonical client tunnel lane: `http://127.0.0.1:28085`.
- Docker work uses BuildKit and Docker Compose v2.
- GPU/offload work is GPU-first; no silent CPU fallback.
- Long-lived Docker state, model caches, and generated active artifacts stay on
  `/srv/scratch`, not the Hemma OS disk.
- Raw corpora and cold completed artifacts belong on `/srv/storage`.
- Runtime changes need governing backlog/reference/ADR authority before they are
  treated as product behavior.

## Current Answer-Key Provider Default

Use OpenAI `gpt-5.4-mini-2026-03-17` as the temporary accepted/default
structured answer-key provider in development and Hemma production. Task 326
teacher adjudication leaves mini at 43 correct, 1 wrong-but-valid, and 0 manual
follow-up on 44 eligible rows, ahead of the retained Qwen3.6 baseline of 41
correct, 3 wrong-but-valid, and 0 manual follow-up. Qwen3.6 remains the guarded
local rollback provider and can be stopped in production to free GPU VRAM while
mini is default.

- Default provider profile: `openai-gpt-5.4-mini-2026-03-17`
- Default model: `gpt-5.4-mini-2026-03-17`
- Endpoint kind: OpenAI Responses
- Output constraint: JSON Schema structured output
- Remote-provider controls: `SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_PROVIDERS_ENABLED=1`
  and `SIR_CONVERT_A_LOT_STRUCTURED_LLM_REMOTE_FALLBACK_POLICY_AUTHORIZED=1`
  are required when mini is the primary provider.
- Qwen rollback profile: `qwen36-llama-cpp-mtp`
- Qwen production container: `sir_convert_qwen_answer_key`; do not recreate it
  unless explicitly returning to the local provider.
- Cache contract: `docs/runbooks/runbook-hemma-gpu-runtime.md`
- Operator details:
  `docs/runbooks/runbook-answer-key-local-model-operator-guide.md`
- Evidence and benchmark authority:
  `docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md`
- Productionization authority:
  `docs/backlog/tasks/task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline.md`
- Model-selection reference:
  `docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md`

## Closeout

For docs or operational-governance edits, run:

```bash
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

If a procedure grows beyond this routing surface, move it into one focused
runbook. If evidence grows beyond a focused runbook, move it into the governing
task or reference document.
