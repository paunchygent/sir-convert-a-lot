---
type: task
id: TASK-SIRCON-REP-0029
title: Repair Exam.net QTI export to the confirmed import contract
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-28'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- Regenerated QTI packages emit one assessmentTest resource with assessmentItemRef and dependency wiring and pass the probe-derived regression fixtures.
- A regenerated DigiExam-migration package imports live into Exam.net with every item in its confirmed family and its keys and points intact.
- The empirical Exam.net import contract is published as a governed reference and the prior vendor-reported strategy reference is marked superseded in the same slice.
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the Exam.net QTI 2.1 export so generated packages import correctly into
Exam.net's early-access QTI importer.

- Emit one `assessmentTest` resource (`imsqti_test_xmlv2p1`) with
  `assessmentItemRef` and dependency wiring in every package, alongside the
  existing `imsmanifest.xml` and per-item `imsqti_item_xmlv2p1` resources.
- Emit only empirically confirmed constructions: keyed interactions carry
  `correctResponse` plus positive `mapping` plus `map_response`; gap items may
  derive keys and scoring from mappings; matching emits directed pairs where
  every displayed left row has at least one correct association.
- Never emit negative mapped values, mappings without `correctResponse` on
  keyed choice or matching items, `match_correct` as the scoring mechanism for
  multiple-response, matching, or gap items, or the QTI `shuffle` attribute as
  a delivery control.
- Free-text items default to the non-inflating pattern: one mapped criterion
  at the full item score plus visible grading guidance; intentional
  per-criterion values are emitted only when the source provides them.
- Promote the diagnostic session's empirical observations ledger to a governed
  reference and mark the vendor-reported import-contract-and-validation
  strategy reference superseded in the same slice.
- Convert the probe families into repository regression fixtures and tests for
  the writer.

Out of scope: the four open empirical unknowns (save-and-reopen persistence,
BND002 candidate-side grading, the corrected one-left-to-many matching probe,
the native Enkelt svar signal), any new item family, matching emission from
DigiExam sources, and any LLM or provider change.

## Contract Inputs

- Empirical contract ledger: diagnostic session
  `.orchestration/context/sessions/01a0474c-158e-7bf1-85ae-6adb4198c143`,
  `scratch/01a0474a-65b2-7e30-8a62-4aeef7704f81/examnet-qti-contract-observations.md`,
  validated boundary ledger (sha256 `9ff8e1602cae0351f41fcf78c4949b1356d0a8422c21e6c91d0bc891134f3060`).
- Writer surfaces: `scripts/sir_convert_a_lot/domain/examnet_qti_*.py`,
  `scripts/sir_convert_a_lot/domain/digiexam_examnet_qti_adapter.py`,
  `scripts/sir_convert_a_lot/infrastructure/examnet_qti_package_writer.py`,
  wired from `infrastructure/digiexam_migration_bundle_builder.py`.
- Retained planning record: session
  `01a048d5-69f7-7394-93dd-8ff91af608cd`,
  `evidence/planning/TASK-SIRCON-REP-0029/plan.md`.
- Exam.net's public documentation carries no QTI import contract; the
  empirical ledger is the sole contract source and importer volatility is an
  accepted risk.

## Core Vertical And Performance

The core vertical is `.dxe` source through the existing migration bundle
builder to a regenerated `qti-package.zip` that imports live into Exam.net
with confirmed families, keys, and points. Package generation is stdlib
zip/XML work with no material performance concern.

## Validation

- `pdm run check --plan exam`, then `pdm run check exam`.
- Regenerate sample packages via `pdm run examnet-qti-samples` and
  `pdm run examnet-qti-migration-samples`; fixtures assert the confirmed
  contract shapes.
- Live Exam.net import proof of one regenerated DigiExam-migration package,
  recorded in the task record.
- Docs close-out: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run handoff-validate`, `git diff --check`.

## Stop Conditions

- A regenerated package is rejected by Exam.net for a construction the ledger
  marks confirmed: stop and record the observation; do not improvise new
  constructions.
- The repair would require emitting an unconfirmed or refuted lane: stop and
  return to planning.
- Scope pressure toward the open empirical unknowns: stop; they need explicit
  user authorization.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The repair lands as a bounded repository task in sir-convert-a-lot now, before and independent of the Skriptoteket port epic. |
| D2  | The empirical observations ledger is promoted to a governed reference and supersedes the vendor-reported strategy reference in the same slice. |
| D3  | The probe families become repository regression fixtures for the writer. |
| D4  | The writer emits only empirically confirmed Exam.net lanes; refuted constructions are never emitted or retried. |
| D5  | The four open empirical unknowns stay open and are not expanded without explicit user request. |
| D6  | Execution custody lives with the planning lane that absorbed the diagnostic session handoff; the ledger is evidence, not implementation authority. |
