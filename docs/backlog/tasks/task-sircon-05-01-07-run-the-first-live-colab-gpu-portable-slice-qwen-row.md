---
type: task
id: TASK-SIRCON-05-01-07
title: Run the first live Colab GPU portable-slice Qwen row-processing proof
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
- The proof uses a fresh bounded source-selection universe, not the live Hemma `10k`
  selection.
- The proof slice is deterministic and unique within that bounded universe.
- Colab stages only the required raw files for its slice.
- Colab runs canonical Task 103 row-processing through `selected-source-records`.
- 'The Colab run root contains at least: - `inventory/` - `audio_24k/` - `spool/rows/`
  - `run.json` - `status.json`'
- The notebook remains orchestration only, not a second preprocessing implementation.
- The notebook can prepare its proof slice from a committed proof bundle without requiring
  manual pre-run file upload steps.
- 'The proof records the exact Colab worker mix: - `row_worker_count=4` - `gpu_asr_worker_count=1`'
retired_ids:
- task-122-run-the-first-live-colab-gpu-portable-slice-qwen-row-processing-proof
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
Run the first live Colab GPU-backed portable-slice proof for Qwen Swedish row-processing without violating the Hemma-first row-selection contract or the canonical Task 103 run-root artifact contract.
## PR Scope
- Use a fresh Hemma-issued bounded `source-selection` run root for the proof.
- Build one deterministic portable slice bundle from that run root.
- Run the notebook-backed Colab proof against a GPU runtime with:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`
- Keep the proof limited to `rixvox train` row-processing only.
- Do not merge Colab spool state into the live Hemma run as part of this task.
- Record a concrete evidence bundle showing that Colab emitted the same Task
103 row-processing artifact shape as Hemma.
## Deliverables
- [ ] One fresh Hemma `source-selection` proof run root for Colab use only.
- [ ] One portable slice bundle issued from that run root.
- [ ] One Colab notebook flow that can be executed top-to-bottom in a normal
Colab UI session.
- [ ] One committed proof bundle that the notebook can extract without manual
bundle assembly.
- [ ] One live Colab row-processing run root with canonical Task 103 artifacts.
- [ ] One verification summary comparing the Colab run-root shape against the
Hemma row-processing contract.
## Acceptance Criteria
- [ ] The proof uses a fresh bounded source-selection universe, not the live
Hemma `10k` selection.
- [ ] The proof slice is deterministic and unique within that bounded universe.
- [ ] Colab stages only the required raw files for its slice.
- [ ] Colab runs canonical Task 103 row-processing through
`selected-source-records`.
- [ ] The Colab run root contains at least:
  - `inventory/`
  - `audio_24k/`
  - `spool/rows/`
  - `run.json`
  - `status.json`
- [ ] The notebook remains orchestration only, not a second preprocessing
implementation.
- [ ] The notebook can prepare its proof slice from a committed proof bundle
without requiring manual pre-run file upload steps.
- [ ] The proof records the exact Colab worker mix:
  - `row_worker_count=4`
  - `gpu_asr_worker_count=1`
## Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
- [ ] Live Colab proof complete

