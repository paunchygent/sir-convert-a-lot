---
type: task
id: TASK-SIRCON-05-02-04
title: Enable Triton flash attention for the Qwen Hemma sidecar benchmark
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
story: ST-SIRCON-05-02
task_kind: story
acceptance_criteria:
- Local tests cover the new default and the explicit fallback flag.
- '`docs/runbooks/runbook-hemma-devops-and-gpu.md` reflects the new default.'
- '`docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
  reflects the new default.'
- The change does not introduce a silent CPU fallback or a raw-host workaround path.
retired_ids:
- task-99-enable-triton-flash-attention-for-the-qwen-hemma-sidecar-benchmark
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Remove the older hardcoded `VLLM_USE_TRITON_FLASH_ATTN=0` assumption from the
Qwen Hemma benchmark lane and make Triton flash attention the explicit default
again for the supported ROCm container path.

### PR Scope

- Update the Task 79 benchmark runtime helper so Triton flash attention is
  enabled by default and can be disabled only through one explicit triage flag.
- Record the selected flash-attention mode in the benchmark runtime report so
  Hemma evidence can prove which path actually ran.
- Update tests, task docs, and the Hemma runbook to match the new default.

### Deliverables

- [ ] Runtime helper defaults to `VLLM_USE_TRITON_FLASH_ATTN=1`.
- [ ] One bounded fallback flag exists for regression triage.
- [ ] Benchmark report records whether Triton flash attention was enabled.
- [ ] Runbook/task wording no longer claims Triton is disabled by default.

### Acceptance Criteria

- [ ] Local tests cover the new default and the explicit fallback flag.
- [ ] `docs/runbooks/run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md` reflects the new default.
- [ ] `docs/backlog/tasks/task-sircon-04-01-01-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
  reflects the new default.
- [ ] The change does not introduce a silent CPU fallback or a raw-host
  workaround path.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
