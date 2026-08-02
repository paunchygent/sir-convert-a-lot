---
type: reference
id: REF-SIRCON-GENERAL-digiexam-intermediate-exam-representation-contract
title: DigiExam Intermediate Exam Representation Contract
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
retired_ids:
- CONV-digiexam-intermediate-exam-representation-contract
summary: DigiExam Intermediate Exam Representation Contract
---

## Overview

## Facts And Semantics

## Decisions And Interpretation

## Historical Source Content

### Purpose

Define the renderer-neutral intermediate exam representation and manifest
contract for the DigiExam source-adapter lane inside Sir Convert's broader
exam artifact conversion and authoring boundary.

The IR is owned by Sir Convert-a-Lot. It is not a DigiExam mirror, an Exam.net
renderer schema, a QTI package, or a bulk-conversion API response. It is the
current DigiExam source-adapter boundary. DigiExam is the first implemented
source adapter, not the product boundary. Future Exam.net-origin PDFs, Word
exports, answer-key artifacts, and other source formats must feed a governed
source-neutral authoring IR instead of extending this DigiExam-named contract.
Task 307 introduces that `ExamAuthoringIR v1` direction with matching
interactions as the first extracted slice.

### Scope

In scope:

- parsed exam metadata and parser status;
- source item order, item type, prompt body, point values, options, gap
  identifiers, source spans, and warnings;
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

### Versioning

The active schema versions after Tasks 298/307 are:

- exam IR: `digiexam_intermediate_exam_v3`;
- manifest: `digiexam_ir_manifest_v3`;
- effective exam: `digiexam_effective_exam_v2` when overlays or applied
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

Task 294 did not extend source IR to carry teacher overlays or applied LLM
completion. Source IR remains parser-owned truth. Runtime output that
incorporates reviewed answer-key completion, manual answer keys, item patches,
teacher corrections, or reviewed advisory acceptance/edit intents MUST use the
active `digiexam_effective_exam_v2` contract and retain source binding back to
the parser-owned IR.

Task 298/307 removes DigiExam-owned matching semantics from this contract
rather than adding a speculative `.dxe` matching adapter. Matching answer-key
pairs now belong to the first `ExamAuthoringIR v1` slice. Retired
`left_id`/`right_id` matching payloads must not be accepted through aliases,
and DigiExam migration contracts do not carry replacement
`correct_matching_pairs` fields.

### Exam IR Shape

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
item type, title/prompt text, alternatives, gap IDs/order,
asset hashes/references, max score, and grading policy fields that affect
target shape. It MUST exclude answer keys, result-PDF enrichment,
teacher overlays, LLM suggestions, manual answer keys, and reviewed advisory
acceptance/edit intents.

The IR MUST preserve item structure separately from answer-key data. A multiple
choice item with options and absent answer provenance remains a structured item
with a missing answer key, not a negative answer key.

### Effective Exam Contract

`digiexam_effective_exam_v2` is the renderer input after source evidence,
accepted manual overlays, applied completion, teacher corrections, or reviewed
advisory acceptance/edit intents have been resolved. It is not parser evidence
and must not be serialized as
`digiexam_intermediate_exam_v3`.

The top-level effective exam MUST include:

- `schema_version`: `digiexam_effective_exam_v2`;
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
- effective prompt/options/gaps structure after any item patch;
- effective answer key, when present;
- effective answer-key provenance, such as `reviewed` or
  `teacher_provided`, separate from parser/source provenance;
- bounded reviewed-completion lineage when an applied key began as an advisory
  candidate;
- applied overlay entry identifiers;
- reviewed advisory acceptance/edit intents applied to the item.

Compact answer-key review state is projected separately from source IR and
effective IR. It may report reviewed advisory keys or teacher-owned edits, but
it does not replace `target_readiness_report_v1` and does not alter source IR
provenance.

### Matching Answer-Pair Requirement

Canonical DigiExam `.dxe` sources do not carry matching items. DigiExam PDF
artifacts that visually show matching-like rows are non-canonical source
evidence and must remain blocked/unknown in the DigiExam parser path rather
than becoming DigiExam-owned matching IR.

Matching answer-key completion is a source-neutral authoring concern. Before
Sir Convert may apply or render keyed matching answer completion, a
matching-capable source adapter must map real source evidence into the
QTI-aligned `ExamAuthoringIR v1` matching model:

- ordered source/left match-set choices with stable IDs;
- ordered target/right match-set choices with stable IDs;
- per-choice association constraints such as `match_min` and `match_max`;
- interaction-level association constraints such as `min_associations` and
  `max_associations`;
- directed answer pairs as ordered pairs of known source/target IDs;
- validation that every referenced source/target ID exists;
- validation that duplicate identical pairs and association-limit violations
  fail closed;
- allowance for unmatched target/right choices as distractors.

The neutral authoring contract MUST NOT encode the current Exam.net PDF profile
as source truth. QTI 2.1/3.0-style matching can represent many-source-to-one-target
and one-source-to-many-target relationships when the relevant choices'
association constraints allow them. Target validators decide whether a
particular target accepts that shape.

The current Exam.net PDF target profile is narrower than the IR: keyed matching
is target-ready only when each source/left choice has at most one matched
target/right choice, each matched target/right choice is used at most once, and
unmatched target/right choices may remain as distractors. Exam.net QTI import
support remains vendor-unproven until Exam.net exposes an import test path.

Until a real matching-capable source adapter feeds `ExamAuthoringIR v1`, DigiExam
migration must not claim keyed matching export. This is the Task 298/307
contract gate, not an optional nice-to-have.

### Gap/open-cloze Accepted-value Requirement

Gap-fill and open-cloze structure in source IR is not enough for automatic
evaluation. Before Sir Convert may apply or render gapped/open-cloze answer
completion, the IR/effective exam contract MUST expose exact accepted values
bound to stable gap IDs:

- stable `gap_id`;
- visible gap order and prompt binding;
- accepted values per gap;
- normalization policy for comparison and export;
- multi-gap completeness validation.

Until those fields are implemented and validated, gapped/open-cloze completion
remains advisory/manual-review only. This is the Task 305 contract gate.

### Embedded Asset Contract

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

### Answer-Key Contract

Answer-key fields MUST include:

- `provenance`: one of the parser provenance states, including `absent`,
  `dxe_populated_key`, `graded_result_pdf_correct_labels`,
  `manual_teacher_key`, or `not_applicable`;
- `correct_alternative_ids`;
- `correct_gap_answers` as gap `guid` plus accepted `value`.

Matching answer pairs are intentionally absent from DigiExam IR. Real matching
sources must map into `ExamAuthoringIR v1` instead.

DigiExam gap data remains source-specific adapter data. Task 305 maps
`DigiExamIrItem.gaps[].guid`, `.dxe` `bodyHTML` `span dx-wg-id` bindings, and
`correct_gap_answers[]` into the source-neutral
`ExamAuthoringGapOpenClozeInteraction` contract in
`scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py`. Target
validators/exporters may consume that neutral contract in later cutover work;
this DigiExam IR contract must not become the universal gap/open-cloze model.

The IR and manifest MUST NOT retain incorrect student selections, student
free-text answers, earned-score labels or values, student identity markers, or
student-performance history from result PDFs. Result PDFs may enrich only
source-bound correct machine-marked answer evidence.

### Manual Follow-Up Contract

Manual follow-up records are required when the IR cannot safely produce a
complete machine-ready item from source evidence. Initial reason codes:

- `manual_marking_required`;
- `manual_answer_key_required`;
- `unsupported_item_type`;
- `parser_warning_blocks_rendering`.

Manual follow-up is descriptive, not renderer behavior. Later renderer stories
decide how to expose it in target artifacts.

### Manifest Summary Shape

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
