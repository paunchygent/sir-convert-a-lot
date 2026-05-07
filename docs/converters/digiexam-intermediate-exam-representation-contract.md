---
type: converter
id: CONV-digiexam-intermediate-exam-representation-contract
title: DigiExam Intermediate Exam Representation Contract
status: active
created: 2026-05-08
updated: 2026-05-08
owners:
  - platform
tags:
  - digiexam
  - exam-migration
  - intermediate-representation
  - manifest
  - renderer-neutral
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-41-digiexam-renderer-neutral-intermediate-exam-representation-and-manifest-schema.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
---

## Purpose

Define the renderer-neutral intermediate exam representation and manifest
contract for the DigiExam to Exam.net migration lane.

The IR is owned by Sir Convert-a-Lot. It is not a DigiExam mirror, an Exam.net
renderer schema, a QTI package, or a bulk-conversion API response. It is the
stable boundary between source parsers and later renderer/import stories.

## Scope

In scope:

- parsed exam metadata and parser status;
- source item order, item type, prompt body, point values, options, matching
  structures, gap identifiers, source spans, and warnings;
- answer-key provenance and source-proven correct answers when available;
- manual follow-up records for missing answer keys or manual marking;
- a deterministic manifest summary for parity reporting and later bulk
  workflow audit.

Out of scope:

- Exam.net PDF formatting and option-label syntax;
- QTI/native import package layout;
- service/API route contracts;
- bulk directory orchestration;
- answer-key synthesis from incomplete source evidence.

## Versioning

The first schema versions are:

- exam IR: `digiexam_intermediate_exam_v1`;
- manifest: `digiexam_ir_manifest_v1`.

Schema changes that remove fields or alter semantics require a new version.
Additive fields may remain on the same version only when existing consumers can
ignore them safely.

## Exam IR Shape

The top-level IR MUST include:

- `schema_version`;
- `source_filename`;
- `source_producer`;
- `parse_status`;
- `renderer_ready`;
- ordered `items`;
- source parser `warnings`;
- `manual_follow_ups`.

Each item MUST include:

- stable `item_id`;
- 1-based `sequence`;
- `title`;
- renderer-neutral `item_type`;
- source `digiexam_type_code` when available;
- `prompt_html` and/or `prompt_lines`;
- `max_score`;
- `source_span`;
- `options`;
- `matching`;
- `gaps`;
- `grading_policy`;
- `answer_key`;
- item-level `warnings`.

The IR MUST preserve item structure separately from answer-key data. A multiple
choice item with options and absent answer provenance remains a structured item
with a missing answer key, not a negative answer key.

## Answer-Key Contract

Answer-key fields MUST include:

- `provenance`: one of the parser provenance states, including `absent`,
  `dxe_populated_key`, `graded_result_pdf_correct_labels`,
  `manual_teacher_key`, or `not_applicable`;
- `correct_alternative_ids`;
- `correct_gap_answers` as gap `guid` plus accepted `value`.

The IR and manifest MUST NOT retain incorrect student selections, student
free-text answers, earned-score labels or values, student identity markers, or
student-performance history from result PDFs. Result PDFs may enrich only
source-bound correct machine-marked answer evidence.

## Manual Follow-Up Contract

Manual follow-up records are required when the IR cannot safely produce a
complete machine-ready item from source evidence. Initial reason codes:

- `manual_marking_required`;
- `manual_answer_key_required`;
- `unsupported_item_type`;
- `parser_warning_blocks_rendering`.

Manual follow-up is descriptive, not renderer behavior. Later renderer stories
decide how to expose it in target artifacts.

## Manifest Summary Shape

The manifest summary MUST include:

- `schema_version`;
- `exam_schema_version`;
- `source_filename`;
- `source_producer`;
- `parse_status`;
- `renderer_ready`;
- `item_count`;
- `warning_count`;
- `manual_follow_up_count`;
- ordered item summaries with `item_id`, `sequence`, `title`, `item_type`,
  `answer_key_provenance`, and `manual_follow_up_required`.

The manifest is an audit and parity surface. It must not become the renderer
format and must not hide blocked parser status.
