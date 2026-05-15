---
type: converter
id: CONV-digiexam-intermediate-exam-representation-contract
title: DigiExam Intermediate Exam Representation Contract
status: active
created: 2026-05-08
updated: 2026-05-15
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
  - docs/backlog/stories/story-42-digiexam-renderer-neutral-embedded-asset-support.md
  - docs/backlog/stories/story-43-digiexam-exam-net-oriented-pdf-renderer.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-275-implement-digiexam-intermediate-exam-representation-and-manifest-schema-contract.md
  - docs/backlog/tasks/task-276-implement-digiexam-dxe-embedded-asset-ir-support.md
  - docs/backlog/tasks/task-277-implement-digiexam-exam-net-oriented-pdf-renderer-and-live-validation.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
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
- embedded asset payloads required by downstream renderers;
- a deterministic manifest summary for parity reporting and later bulk
  workflow audit.

Out of scope:

- Exam.net PDF formatting and option-label syntax;
- QTI/native import package layout;
- service/API route contracts;
- bulk directory orchestration;
- answer-key synthesis from incomplete source evidence.

## Versioning

The active schema versions after Task 276 are:

- exam IR: `digiexam_intermediate_exam_v2`;
- manifest: `digiexam_ir_manifest_v2`.
- effective exam: `digiexam_effective_exam_v1` when overlays or applied
  completion change renderer input.

Schema changes that remove fields or alter semantics require a new version.
Additive fields may remain on the same version only when existing consumers can
ignore them safely.

Embedded asset support is not a same-version v1 extension. Task 276 defined
`digiexam_intermediate_exam_v2` and `digiexam_ir_manifest_v2` because renderer
and parity consumers need asset fields and ordered asset summaries to be
contractually present.

Task 277 added `content_base64` to the v2 asset record as an additive field.
Existing metadata and manifest consumers can ignore it safely, while PDF/QTI
renderers need it to carry referenced assets instead of only comparing hashes.

Task 294 does not extend `digiexam_intermediate_exam_v2` to carry teacher
overlays or applied LLM completion. Source IR remains parser-owned truth.
Runtime output that incorporates reviewed answer-key completion, manual answer
keys, item patches, or review decisions MUST use `digiexam_effective_exam_v1`
and retain source binding back to the parser-owned IR.

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
- item-level `warnings`;
- embedded asset records;
- ordered embedded asset references.

Each manifest item summary MUST include source-binding fields for overlays:

- `item_id`;
- 1-based `sequence`;
- `item_type`;
- `source_item_fingerprint`;
- source IR schema version and source IR digest through the enclosing manifest.

`source_item_fingerprint` MUST be derived from stable source structure only:
item type, title/prompt text, alternatives, gap IDs/order, matching column
structure, asset hashes/references, max score, and grading policy fields that
affect target shape. It MUST exclude answer keys, result-PDF enrichment,
teacher overlays, LLM suggestions, manual answer keys, and review decisions.

The IR MUST preserve item structure separately from answer-key data. A multiple
choice item with options and absent answer provenance remains a structured item
with a missing answer key, not a negative answer key.

## Effective Exam Contract

`digiexam_effective_exam_v1` is the renderer input after source evidence,
accepted manual overlays, applied completion, or review decisions have been
resolved. It is not parser evidence and must not be serialized as
`digiexam_intermediate_exam_v2`.

The top-level effective exam MUST include:

- `schema_version`: `digiexam_effective_exam_v1`;
- `source_ir_schema_version`;
- `source_ir_sha256`;
- `source_file_sha256`;
- optional `ingestion_overlay_sha256`;
- optional `answer_key_completion_report_sha256`;
- ordered effective items;
- effective provenance summary;
- target-readiness input summary.

Each effective item MUST include:

- `item_id`, `sequence`, `item_type`, and `source_item_fingerprint`;
- source item reference;
- effective prompt/options/gaps/matching structure after any item patch;
- effective answer key, when present;
- effective answer-key provenance, such as `source_evidence`,
  `manual_teacher_key`, `reviewed_llm_completion`, or `absent`;
- applied overlay entry identifiers;
- review decisions applied to the item.

`Godkänn` / accept-current-state review decisions may affect target readiness
only after Sir Convert recomputes the effective exam and validates the target.
They do not create answer keys and do not alter source IR provenance.

## Matching Answer-Pair Requirement

Matching structure in source IR is not enough for applied matching answer-key
completion. Before Sir Convert may apply or render matching answer completion,
the IR/effective exam contract MUST expose exact answer pairs:

- stable `left_id`;
- stable `right_id`;
- `correct_matching_pairs` as ordered pairs of known IDs;
- right-option reuse policy;
- validation that every referenced left/right ID exists.

Until those fields are implemented and validated, matching completion remains
advisory/manual-review only. This is a critical dependency for Task 298, not an
optional nice-to-have.

## Embedded Asset Contract

Version 2 of the IR MUST expose embedded `.dxe` question assets separately from
prompt HTML. Asset records MUST include:

- stable `asset_id`;
- item binding;
- source image index from `question.images[]`;
- SHA-256 over decoded bytes;
- `media_type`;
- canonical base64 over the decoded payload as `content_base64`;
- `byte_length`;
- dimensions when supported by the parser contract.

Asset references MUST be modeled separately from asset records. Repeated
`<img data-image-id="N">` occurrences are valid ordered references to one asset
when they bind to the same `question.images[N]` value. The parser must fail
closed only for invalid base64, unsupported media bytes, missing references,
unused payloads, or ambiguous bindings.

Missing-reference validation applies even when `question.images[]` is empty or
absent. A `bodyHTML` `<img data-image-id="N">` reference without a corresponding
payload MUST fail closed with `missing_embedded_asset_reference`.

Asset failures MUST use explicit blocking warning codes:
`invalid_embedded_asset_base64`, `unsupported_embedded_asset_media`,
`missing_embedded_asset_reference`, `unused_embedded_asset_payload`, and
`ambiguous_embedded_asset_binding`.

The manifest MUST NOT serialize `content_base64`. Manifest asset summaries
remain parity and audit metadata only: hashes, byte lengths, media type,
dimensions, and ordered references.

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
- `asset_count`;
- exam-level `asset_summaries`;
- `warning_count`;
- `manual_follow_up_count`;
- ordered item summaries with `item_id`, `sequence`, `title`, `item_type`,
  `answer_key_provenance`, `manual_follow_up_required`, and per-item
  `asset_summaries`.

The manifest is an audit and parity surface. It must not become the renderer
format and must not hide blocked parser status.

Version 2 manifest summaries MUST also include deterministic ordered asset
summaries for exam-level and per-item parity. Asset summaries MUST include
`item_id`, `asset_id`, `source_image_index`, `sha256`, `media_type`,
`byte_length`, dimensions, and reference count/order so a renderer can prove it
is carrying the correct asset, not merely the correct number of assets.
