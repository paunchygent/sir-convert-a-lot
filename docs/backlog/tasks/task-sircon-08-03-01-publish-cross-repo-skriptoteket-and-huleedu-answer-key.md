---
type: task
id: TASK-SIRCON-08-03-01
title: Publish cross-repo Skriptoteket and HuleEdu answer-key completion handoff
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
story: ST-SIRCON-08-03
task_kind: story
acceptance_criteria:
- '- [ ] Skriptoteket is instructed to consume Sir Convert manifest and overlay contract
  data, not duplicate parser or provider inference.'
- '- [ ] HuleEdu provider reuse is framed as optional/future and requires a new API
  shape, not reuse of comparison-only callback results.'
- '- [ ] Public/grant and authenticated routes keep separate consent and remote fallback
  semantics.'
- '- [ ] The handoff contains exact validation expectations for each repo.'
retired_ids:
- task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff
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

Publish the downstream integration handoff that lets Skriptoteket and HuleEdu
create their own governed docs/tasks from the Sir Convert answer-key completion
contract.

### PR Scope

- Write a Sir Convert-owned integration reference or handoff section that names
  exactly what Skriptoteket may send and consume.
- Identify the Skriptoteket docs/backlog surfaces that should receive the
  teacher-review UI and adapter work.
- Identify the HuleEdu decision/task needed only if LLM Provider Service should
  add a generic structured-completion API.
- Preserve the recommendation that Sir Convert implements the first
  service-backed local-first provider harness rather than blocking on HuleEdu.
- Keep public Exam Converter grant behavior and remote-provider consent
  requirements explicit.

### Deliverables

- [ ] Skriptoteket handoff prompt with required reads, scope, out-of-scope,
  adapter/UI contract, proof gates, and stop conditions.
- [ ] HuleEdu handoff prompt or task seed for generic structured-completion API
  evaluation.
- [ ] Cross-repo dependency map linked from Sir Convert docs.
- [ ] Updated `.codex/handoff.md` active pointer.

### Acceptance Criteria

- [ ] Skriptoteket is instructed to consume Sir Convert manifest and overlay
  contract data, not duplicate parser or provider inference.
- [ ] HuleEdu provider reuse is framed as optional/future and requires a new API
  shape, not reuse of comparison-only callback results.
- [ ] Public/grant and authenticated routes keep separate consent and remote
  fallback semantics.
- [ ] The handoff contains exact validation expectations for each repo.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
