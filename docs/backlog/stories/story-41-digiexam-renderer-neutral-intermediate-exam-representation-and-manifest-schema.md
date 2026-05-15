---
id: story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema
title: DigiExam renderer-neutral intermediate exam representation and manifest schema
type: story
status: completed
priority: high
created: '2026-05-08'
last_updated: '2026-05-08'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md
  - docs/backlog/stories/story-40-digiexam-dxe-source-parser-and-answer-key-provenance.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
labels:
  - exam-migration
  - digiexam
  - intermediate-representation
  - manifest
  - renderer-neutral
---

Implementation slice with acceptance-driven scope.

## Objective

Define and implement the first renderer-neutral DigiExam intermediate exam
representation and manifest schema. This story sits after the completed PDF and
`.dxe` parser lanes and before any Exam.net renderer/import decision.
DigiExam is the source adapter for this story; the broader product boundary is
exam artifact conversion/authoring through a Sir Convert-owned intermediary
shape to Exam.net-compatible PDF and QTI targets.

## Scope

- Convert existing DigiExam parser outputs into one stable Sir Convert-owned
  intermediate exam model.
- Preserve item order, item type, prompt body, options, gap identifiers, point
  values, source spans, parse status, warnings, and
  answer-key provenance.
- Represent manual follow-up explicitly for open-ended marking, missing machine
  answer keys, unsupported shapes, and parser-blocking warnings.
- Emit a deterministic manifest summary that downstream renderer and bulk
  workflow stories can consume for parity checks.
- Keep the model renderer-neutral: no Exam.net labels, no QTI package shape, no
  PDF layout instructions, no service/API route contract, and no bulk workflow.
- Keep answer synthesis out of scope. Missing answer keys remain missing unless
  a `.dxe`, graded-result PDF, or later teacher-provided key supplies them.

## Acceptance Criteria

- [x] The IR has a versioned schema identifier independent of parser and
  renderer names.
- [x] The IR can be built from the completed `.dxe` parser output for the
  2026-05-07 mixed-question fixture.
- [x] The IR can be built from the PDF artifact parser output without
  promoting PDF-only evidence above `.dxe` evidence.
- [x] The IR preserves source item order and stable item identifiers.
- [x] The IR preserves open-ended, single-choice, multiple-response, gap-fill,
  and unknown item-type states without renderer-specific syntax. Matching-like
  PDF artifact rows remain unknown/non-canonical in the DigiExam lane.
- [x] The IR carries answer-key provenance separately from item structure.
- [x] The IR preserves result-PDF-enriched correct MCQ IDs and gap GUID/value
  answer pairs when they are available.
- [x] The IR and manifest serialization from graded-result PDF enrichment
  retains only correct machine-marked answer evidence and excludes incorrect
  selections, student free-text answers, earned scores, identity markers, and
  student-performance history.
- [x] The IR manifest reports parse status, renderer readiness, item count,
  warning count, and manual follow-up count deterministically.
- [x] The IR manifest includes ordered item summaries with item id, sequence,
  title, item type, answer-key provenance, and manual-follow-up flag for parity
  consumers.
- [x] Blocked parser outputs remain blocked in the IR manifest and do not become
  renderer-ready by translation.

## Test Requirements

- [x] Fixture-backed tests cover `.dxe` output with absent answer keys.
- [x] Fixture-backed tests cover `.dxe` output enriched from the sanitized
  graded-result PDF.
- [x] Fixture-backed tests cover the chemistry PDF artifact's matching-like
  visible rows as unsupported/non-canonical DigiExam evidence.
- [x] Tests assert manual follow-up entries for open-ended manual marking and
  missing machine-answer keys.
- [x] Tests serialize the graded-result PDF enriched IR and manifest and assert
  result-PDF-only negative data is absent.
- [x] Tests assert the manifest item-summary shape required by the converter
  contract, not only aggregate counts.
- [x] Tests assert blocked/unsupported parser output remains blocked in the IR
  manifest.

## Done Definition

Story 41 is done when Task 275 lands the renderer-neutral IR and manifest
contract, fixture-backed mapping tests pass for the completed parser lanes, and
EPIC-10 docs continue to reserve Exam.net renderer/import behavior for a later
governed story. Task 275 completed this contract on 2026-05-08.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
