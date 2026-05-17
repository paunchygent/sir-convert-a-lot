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

## Current Local LLM Default

Use Qwen3.6-27B MTP Q6_K through the Hemma-local `llama.cpp` HIP server as the
current guarded answer-key advisory provider. Granite/vLLM and Devstral Small
are demoted for this route by Task 309 evidence. Qwen3.6 remains advisory-only:
the zero wrong-but-valid promotion gate is not met, so teacher review or a
later governed decision is required before automatic answer-key application.

- Runtime: `llama.cpp` HIP `llama-server`
- Provider profile: `qwen36-llama-cpp-mtp`
- Model: `qwen3.6-27b-q6k-mtp`
- Bind: `127.0.0.1`
- Port: `8082`
- Context: `16384`
- Temperature: `0.15`
- Output constraint: llama.cpp JSON Schema or GBNF-constrained JSON only
- Required mode: `--reasoning off`
- Runtime proof: localhost-only provider status, GPU offload, required
  llama.cpp arguments, and no CPU fallback are proved by Task 319.
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
