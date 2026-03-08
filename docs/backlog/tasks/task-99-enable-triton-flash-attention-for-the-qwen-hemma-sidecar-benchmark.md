---
id: task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark
title: Enable Triton flash attention for the Qwen Hemma sidecar benchmark
type: task
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md
  - docs/backlog/tasks/task-98-add-qwen-english-reference-clone-lane-to-hemma-benchmark.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - flash-attn
  - triton
  - hemma
  - rocm
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the older hardcoded `VLLM_USE_TRITON_FLASH_ATTN=0` assumption from the
Qwen Hemma benchmark lane and make Triton flash attention the explicit default
again for the supported ROCm container path.

## PR Scope

- Update the Task 79 benchmark runtime helper so Triton flash attention is
  enabled by default and can be disabled only through one explicit triage flag.
- Record the selected flash-attention mode in the benchmark runtime report so
  Hemma evidence can prove which path actually ran.
- Update tests, task docs, and the Hemma runbook to match the new default.

## Deliverables

- [ ] Runtime helper defaults to `VLLM_USE_TRITON_FLASH_ATTN=1`.
- [ ] One bounded fallback flag exists for regression triage.
- [ ] Benchmark report records whether Triton flash attention was enabled.
- [ ] Runbook/task wording no longer claims Triton is disabled by default.

## Acceptance Criteria

- [ ] Local tests cover the new default and the explicit fallback flag.
- [ ] `docs/runbooks/runbook-hemma-devops-and-gpu.md` reflects the new default.
- [ ] `docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
  reflects the new default.
- [ ] The change does not introduce a silent CPU fallback or a raw-host
  workaround path.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
