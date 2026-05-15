---
type: converter
id: CONV-exam-authoring-ir-v1-contract
title: ExamAuthoringIR v1 Contract
status: active
created: 2026-05-15
updated: 2026-05-15
owners:
  - platform
tags:
  - exam-authoring-ir
  - source-adapter
  - matching
  - gap-fill
  - open-cloze
  - qti
links:
  - docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
---

## Purpose

`ExamAuthoringIR v1` is the source-neutral authoring contract that sits between
source adapters and target validators/exporters. It prevents source-specific
parse models, such as the DigiExam adapter shape, from becoming universal exam
contracts by accident.

Task 307 introduced the first slice: matching interactions. Task 305 is planned
as the next slice for gapped/open-cloze accepted values. Later slices will move
the remaining reusable choices, provenance, evidence spans, warnings, and
manual-follow-up state into this authoring boundary after the relevant
source-adapter contracts are complete.

## Architecture Boundary

The intended flow is:

```text
source parser -> source adapter -> ExamAuthoringIR v1 -> target validators/exporters
```

Source parsers own extraction and source evidence. Source adapters map
source-native parse results into the neutral contract. Target validators and
exporters decide whether the neutral structure can be emitted as Exam.net PDF,
general QTI, future Exam.net QTI, or another target format.

DigiExam `.dxe` sources do not carry matching items. The DigiExam migration
contract therefore must not emit keyed matching interactions or construct QTI
match pairs. Matching-capable sources, such as Exam.net PDF artifacts or
teacher-authored structured DOCX/Markdown, must use their own source-native
parse models and then adapt into this contract.

## Matching Interaction V1

The active schema version is `exam_authoring_ir_v1`, defined in
`scripts/sir_convert_a_lot/domain/exam_authoring_schema_versions.py`.

A matching interaction contains:

- stable `interaction_id`;
- ordered source choices with `choice_id`, visible text, order, and
  `match_min`/`match_max` association bounds;
- ordered target choices with the same stable ID/text/order/bounds fields;
- interaction-level `min_associations` and `max_associations`;
- answer-key provenance;
- directed answer pairs from source choice ID to target choice ID;
- optional source evidence records with source family, source ID, and locator.

The neutral validator rejects blank choice IDs, duplicate source or target
choice IDs, duplicate identical pairs, unknown source or target IDs, interaction
association-count violations, and per-choice association-limit violations.

The neutral validator allows QTI-permissive shapes when bounds allow them,
including many-source-to-one-target, one-source-to-many-target, one-to-one, and
unmatched target distractors.

## Target Profiles

Target-profile validators layer stricter target constraints on top of the
neutral contract.

The current Exam.net PDF matching profile allows one-to-one matched pairs plus
unmatched target distractors. It rejects one source matched to several targets
and one target matched from several sources.

Exam.net QTI import remains vendor-unproven until Exam.net exposes an import
test path. Sir Convert may validate general QTI shape, but it must not claim
live Exam.net QTI import readiness without that vendor path.

## Implementation Authority

Runtime value objects and validators live in:

- `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`;
- `scripts/sir_convert_a_lot/domain/exam_authoring_schema_versions.py`.

Focused proof lives in:

- `tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`.

The DigiExam parser and `DigiExamIntermediateExam` contracts intentionally do
not contain matching structures or matching answer pairs after this slice.

## Planned Gap/Open-Cloze Interaction V1

Task 305 owns the first source-neutral gap/open-cloze accepted-value slice.
This contract must preserve source intent even when a target cannot emit a
native gap item.

The planned gap/open-cloze interaction contains:

- stable interaction ID;
- ordered gaps with `gap_id`, display order, prompt/body binding, and source
  evidence/span;
- accepted values per gap;
- normalization profile for validation and export decisions;
- a flag or equivalent policy that states whether each gap is required for
  automatic evaluation;
- answer-key provenance;
- source evidence records that can represent DigiExam `.dxe`, layout PDF,
  DOCX, Markdown, or future source families without faking a DigiExam shape.

The neutral validator should reject unknown gap IDs, duplicate/conflicting
accepted values under the selected normalization profile, missing accepted
values for required gaps, and multi-gap completeness violations. It should not
reject source intent merely because a target cannot export a native gap item.

Target validators decide whether a gap/open-cloze interaction can be emitted as
native Exam.net PDF, degraded manual/free-text, omitted with teacher approval,
manual recreation guidance, general QTI, future Exam.net QTI, or another target
shape.

QTI 3 documents `qti-gap-match-interaction`, and QTI 2.1 includes
`gapMatchInteraction`; these standards prove that gap interactions are QTI
concepts. Exam.net publicly advertises fill-the-gaps in its own authoring UI,
but Sir Convert must not claim native Exam.net gap import/export support until
a governed Exam.net proof path exists.

Matching-styled gap/open-cloze source shapes, such as a teacher workaround that
uses visible gap rows to simulate matching, stay in this neutral authoring
space. Source adapters preserve the evidence; target exporters decide whether
safe matching remapping is available.
