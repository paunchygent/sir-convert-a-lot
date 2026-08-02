---
type: task
id: TASK-SIRCON-05-01-06
title: Add portable Colab slice-based Qwen preprocessing lane
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
story: ST-SIRCON-05-01
task_kind: story
acceptance_criteria:
- The Colab lane does not independently select rows.
- The first portable lane is explicitly limited to `rixvox train` row-processing.
- Slice bundles are deterministic and disjoint for the same bounded source selection.
- Portable selected-source records do not rely on Hemma-local absolute locator paths.
- Colab can stage only the required raw files for the chosen slice using modern `huggingface_hub`
  download methods.
- Task 103 can consume the portable slice and emit the same run-root structure as
  Hemma row-processing.
- The notebook is only an orchestrator around repo-owned script surfaces, not a second
  implementation.
- One real Colab execution produces a valid Task 103 row-processing run root from
  a portable slice bundle.
retired_ids:
- task-121-add-portable-colab-slice-based-qwen-preprocessing-lane
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

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define and scaffold one portable Colab row-processing lane that consumes a
Hemma-issued unique slice of `rixvox` train rows, stages only the raw files
needed for that slice, and emits the exact same Task 103 run-root artifacts as
the canonical Hemma preprocessing pipeline.

## PR Scope

- Define one portable slice-bundle contract rooted in a completed Hemma
  `source-selection` run.
- Ensure Colab never selects its own rows and never overlaps with rows already
  assigned to Hemma or another remote worker.
- Keep the notebook thin: it should orchestrate repo-owned scripts rather than
  embedding a second preprocessing implementation in notebook cells.
- Reuse the canonical Task 103 row-processing code path so Colab outputs the
  same `inventory/`, `audio_24k/`, `spool/rows/`, `run.json`, and
  `status.json` shapes as Hemma.
- Restrict the first portable lane to `rixvox train` row-processing only; held
  out corpora and finalization remain on Hemma.
- Provide one local proof that the slice planner yields disjoint slices and
  that the runner can consume a portable selected-source JSONL after locally
  staging the required raw archives.

## Chosen Design

1. Hemma remains the source of truth for `source-selection`.
1. A new portable slice planner emits:
   - one portable `selected_source_records.jsonl`
   - one `required_hub_files.json`
   - one `slice_summary.json`
1. Portable slice bundles are deterministic and disjoint by:
   - sorted bounded `rixvox train` row order
   - modulo partitioning by `slice_index` and `slice_count`
1. Portable selected-source rows intentionally drop Hemma-local locators.
1. Colab stages only the required dataset files for the chosen slice into a
   local raw-data root, then runs Task 103 in a new
   `selected-source-records` source mode that re-resolves local locators before
   row-processing starts.
1. Each Colab worker writes its own independent Task 103 run root; later
   Hemma-side merge/finalization remains a separate follow-on concern.

## Deliverables

- [x] One documented portable slice-bundle contract for Colab preprocessing.
- [x] One repo-owned slice planner and required-file staging surface.
- [x] One Task 103 source mode that consumes portable selected-source JSONL.
- [x] One notebook scaffold that orchestrates the repo-owned Colab lane.
- [x] One local proof that slice planning is disjoint and artifact-compatible.
- [ ] One real Colab execution proof against a portable slice bundle.

## Acceptance Criteria

- [x] The Colab lane does not independently select rows.
- [x] The first portable lane is explicitly limited to `rixvox train`
  row-processing.
- [x] Slice bundles are deterministic and disjoint for the same bounded source
  selection.
- [x] Portable selected-source records do not rely on Hemma-local absolute
  locator paths.
- [x] Colab can stage only the required raw files for the chosen slice using
  modern `huggingface_hub` download methods.
- [x] Task 103 can consume the portable slice and emit the same run-root
  structure as Hemma row-processing.
- [x] The notebook is only an orchestrator around repo-owned script surfaces,
  not a second implementation.
- [ ] One real Colab execution produces a valid Task 103 row-processing run
  root from a portable slice bundle.

## Current State

The repo now has:

- one portable-slice planner that emits disjoint `selected_source_records`
  bundles from a Hemma-issued `source-selection` run root
- one required-file staging surface that uses `hf_hub_download(...)`
- one `selected-source-records` Task 103 source mode that re-resolves local
  locators from staged raw files before row-processing starts
- one notebook scaffold that acts only as an orchestrator

The remaining gap is one real Colab execution proof. Until that exists, this
task should be treated as locally proven and operationally promising, not fully
closed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [ ] Real Colab execution proof complete
