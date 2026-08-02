---
type: task
id: TASK-SIRCON-08-01-04
title: Run service-backed auth-public-edge mirror validation for answer-key completion
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-08-01
task_kind: story
acceptance_criteria:
- The validation runs through the deployed service path, not the in-process executor.
- Authenticated access and public-edge readiness are explicitly proven or the task
  records a blocking failure.
- The governed Qwen3.6 llama.cpp provider is reachable only through the intended service/local-provider
  path and is not publicly exposed.
- Reports retain zero raw prompts and zero raw provider responses.
- Source IR and effective IR mutation semantics match Task 309 and Task 306 contracts.
- Wrong-but-valid remains the primary safety metric; manual follow-up is acceptable,
  plausible wrong keys are not.
- Unknown IDs and duplicate IDs are zero for any mirror-success claim.
- Service-backed differences from the in-process baseline are explained before any
  alpha-readiness recommendation.
retired_ids:
- task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion
---
## Context

Source record: docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md

### Objective

> Run the strict service-backed mirror validation for answer-key completion after
> Task 309's Hemma in-process validation settles the guarded provider choice and
> after Task 310 defines any needed validation-only force-eval mode.
>
> Unlike Task 309's first pass, this task intentionally includes deployed service
> behavior, authentication, public-edge readiness, provider reachability from the
> running app, and operator/user-facing alpha-readiness concerns. The goal is to
> prove the same answer-key safety properties through the real service path, not
> to compare model candidates.

## Decision And Assumption Ledger

## Story Contract Slice

### PR Scope

> - Use the governed provider lane established by Task 309. As of the 2026-05-16
>   evidence, this means Qwen3.6-27B-Q6_K on llama.cpp with JSON Schema output,
>   not the demoted Granite/vLLM or Devstral lanes.
> - Run the versioned DigiExam DXE fixture corpus through the deployed service
>   path rather than the in-process job executor.
> - Include authenticated service access and public-edge readiness checks needed
>   for real alpha testing.
> - If Task 310 is complete, run validation-only force-eval over source-keyed
>   items as a preflight or separate report before the production/auth-edge mirror
>   execution.
> - Mirror Task 309's report metrics: valid suggestion, manual follow-up,
>   wrong-but-valid answer, unknown IDs, duplicate IDs, partial gap answers,
>   latency, tokens/sec, backend failure code, and resource state.
> - Compare service-backed output against Task 309's in-process baseline and
>   explain any service-path differences.
> - Keep generated reports outside git and promote only sanitized summaries into
>   governed docs.

### Out Of Scope

> - Model bake-off or GGUF candidate comparison.
> - Reopening model bake-off or replacing the Task 309 governed provider choice
>   without a new governed operator decision.
> - Prompt-engineering around a specific failed item.
> - Weakening auth/public-edge policy to make validation easier.

## Contract Inputs

## Plan

## Implementation Steps

## Proof

### Deliverables

> - [ ] Strict service-backed launch/status command surface.
> - [ ] Auth/public-edge readiness preflight report.
> - [ ] Service-backed full-corpus mirror validation JSON report and Markdown
>   summary retained outside git.
> - [ ] Optional validation-only force-eval report when Task 310 is complete.
> - [ ] Comparison summary against Task 309's in-process baseline.
> - [ ] Alpha-readiness recommendation for persistent live testing against real
>   test users at work.

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review
