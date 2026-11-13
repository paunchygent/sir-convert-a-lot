---
type: task
id: TASK-SIRCON-01-02-01
title: Adopt Story 003c thin adapter in HuleEdu and validate demanding scientific
  PDF workload
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
story: ST-SIRCON-01-02
task_kind: story
acceptance_criteria:
- HuleEdu integration calls Sir Convert-a-Lot through canonical adapter contract surface.
- End-to-end HuleEdu flow can submit, poll, and retrieve results without per-document
  custom logic.
- Workload validation includes demanding scientific PDFs representative of production
  use.
- 'Workload execution demonstrates operational ease: - no manual converter code changes
  required across corpus - failures (if any) are reported via canonical error/status
  surfaces with actionable diagnostics'
- Story 003c closure decision is supportable with HuleEdu adoption evidence.
retired_ids:
- task-08-adopt-consumer-integration-thin-adapter-in-huleedu-and-validate-demanding-scientific-pdf-workload
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

Adopt the canonical Story 003c thin adapter in the HuleEdu repository and prove
it is easy to use for real, demanding scientific-paper PDF workloads, which are
the primary expected load profile for Sir Convert-a-Lot.

### PR Scope

- Implement/align HuleEdu integration adapter to use canonical Story 003c semantics
  (no business logic forks).
- Verify end-to-end usage ergonomics from HuleEdu application path.
- Run workload validation on a representative demanding scientific-paper corpus.
- Capture evidence and update this repo’s Story 003c docs for closure readiness.

### Deliverables

- [ ] HuleEdu adapter integration uses canonical v1 contract and thin adapter behavior.
- [ ] HuleEdu-side integration tests and smoke flow evidence are captured.
- [ ] Scientific-paper workload evidence package is produced (inputs summary + outcomes).
- [ ] Story 003c docs in this repo updated with HuleEdu adoption evidence links.

### Acceptance Criteria

- [ ] HuleEdu integration calls Sir Convert-a-Lot through canonical adapter contract surface.
- [ ] End-to-end HuleEdu flow can submit, poll, and retrieve results without per-document custom logic.
- [ ] Workload validation includes demanding scientific PDFs representative of production use.
- [ ] Workload execution demonstrates operational ease:
  - no manual converter code changes required across corpus
  - failures (if any) are reported via canonical error/status surfaces with actionable diagnostics
- [ ] Story 003c closure decision is supportable with HuleEdu adoption evidence.

### Workload Validation Requirements

- Corpus profile:
  - real, non-sensitive scientific papers
  - mixed complexity (figures, tables, multi-column text, references, appendices)
  - representative page-count spread for demanding workloads
  - default source path in HuleEdu repo:
    - `/Users/olofs_mba/Documents/Repos/huleedu/docs/research/research_papers/llm_as_a_annotater`
- Evidence outputs:
  - per-document status summary
  - conversion duration summary (distribution, not single sample)
  - failure taxonomy with canonical error codes
  - ease-of-use notes from HuleEdu integration perspective

### Validation

- In this repo:
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- In HuleEdu repo (to be captured in evidence):
  - integration tests for adapter path
  - end-to-end smoke against Hemma tunnel/service
  - workload run commands used for scientific-paper corpus (including
    `docs/research/research_papers/llm_as_a_annotater`)

### Checklist

- [x] Planning complete
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
