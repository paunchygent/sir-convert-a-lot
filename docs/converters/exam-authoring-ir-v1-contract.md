---
type: converter
id: CONV-exam-authoring-ir-v1-contract
title: ExamAuthoringIR v1 Contract
status: active
created: 2026-05-15
updated: 2026-05-18
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
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
---

## Purpose

`ExamAuthoringIR v1` is the source-neutral authoring contract that sits between
source adapters and target validators/exporters. It prevents source-specific
parse models, such as the DigiExam adapter shape, from becoming universal exam
contracts by accident.

Task 307 introduced the first slice: matching interactions. Task 305 adds the
second slice: gapped/open-cloze accepted values. Later slices will move the
remaining reusable choices, provenance, evidence spans, warnings, and
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
- whole-key answer-key provenance: `absent`, `source_provided`,
  `teacher_provided`, or `reviewed`;
- directed answer pairs from source choice ID to target choice ID;
- optional source evidence records with source family, source ID, and locator.

The neutral validator rejects blank choice IDs, duplicate source or target
choice IDs, duplicate identical pairs, unknown source or target IDs, opaque
aggregate `mixed` answer-key provenance, non-empty pairs with `absent`
answer-key provenance, malformed association bounds,
interaction association-count violations, and per-choice association-limit
violations. Minimum bounds must be non-negative. Maximum bounds must be
non-negative; `0` means unbounded, while every non-zero maximum must be greater
than or equal to its minimum.

The neutral validator allows QTI-permissive shapes when bounds allow them,
including many-source-to-one-target, one-source-to-many-target, one-to-one, and
unmatched target distractors.

Matching provenance is whole-key provenance in this slice. `mixed` is invalid
for matching until a future governed contract adds per-pair provenance and
evidence. A reviewed LLM-derived matching key may therefore be represented as a
whole-key `reviewed` answer key only when the reviewed application accepts the
complete directed pair set. Candidate lineage, such as provider profile,
completion report digest, candidate digest, and review decision ID, belongs in
the effective/report metadata owned by the reviewed-application slice, not in
source parser provenance and not as aggregate `mixed` matching provenance.

## Target Profiles

Target-profile validators layer target-specific checks on top of the neutral
contract.

The current Exam.net PDF matching profile uses the source-neutral matching
bounds directly: one-to-one, many-source-to-one-target, one-source-to-many-target,
and unmatched target distractors are valid when the interaction and per-choice
`match_min`/`match_max` bounds allow them.

Exam.net QTI import remains vendor-unproven until Exam.net exposes an import
test path. Sir Convert may validate general QTI shape, but it must not claim
live Exam.net QTI import readiness without that vendor path.

## Matching Implementation Authority

Runtime value objects and validators live in:

- `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`;
- `scripts/sir_convert_a_lot/domain/exam_authoring_schema_versions.py`.
- `scripts/sir_convert_a_lot/domain/exam_authoring_matching_manual_answer_key.py`
  owns the Task 323 producer-ready matching manual-answer-key submission DTO
  and application boundary.
- `scripts/sir_convert_a_lot/application/exam_authoring_matching_apply_contracts.py`
  owns the Task 324 source-neutral request/response contract and readiness
  projection for the matching apply route.
- `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_matching_v2.py`
  exposes the Task 324 v2 HTTP route.

Focused proof lives in:

- `tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`.
- `tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py`.
- `tests/sir_convert_a_lot/test_exam_authoring_matching_apply_route.py`.

The DigiExam parser and `DigiExamIntermediateExam` contracts intentionally do
not contain matching structures or matching answer pairs after this slice.

## Matching Manual Answer-Key Producer DTO

Task 323 exposes a source-neutral matching manual-answer-key producer DTO for
Skriptoteket and other consumers that need to submit reviewed teacher keys
against `ExamAuthoringIR v1` matching interactions. The DTO is not a DigiExam
overlay and must not be represented as `DigiExamOverlayMatchingManualAnswerKey`.

The public DTO shape is:

```json
{
  "schema_version": "exam_authoring_ir_v1",
  "kind": "matching",
  "interaction_id": "matching-001",
  "source_item_fingerprint": "sha256:item-source",
  "answer_key": {
    "provenance": "teacher_provided",
    "pairs": [
      {
        "source_id": "source-001",
        "target_id": "target-001"
      }
    ]
  }
}
```

The DTO accepts only whole-key `absent`, `source_provided`,
`teacher_provided`, and `reviewed` provenance. It does not expose `mixed` as a
valid generated consumer type because matching pairs do not yet carry per-pair
provenance. Non-empty pairs with `absent` provenance fail closed. Retired
`left_id`/`right_id` aliases are rejected by schema validation rather than
translated.

Application validates schema version, interaction ID, optional source item
fingerprint, exact source/target IDs, duplicate pairs, association bounds, and
the neutral matching validation rules before returning an updated
`ExamAuthoringIR v1` interaction. It does not mutate parser-owned source IR or
source/parser provenance.

## Matching Manual Answer-Key Apply Route

Task 324 exposes the producer-owned source-neutral route that accepts the DTO as
OpenAPI request-body JSON:

```text
POST /v2/exam-authoring/matching/manual-answer-key/apply
```

The request body contains:

- `source_interaction`: the producer-returned `ExamAuthoringIR v1` matching
  interaction state, including `source_item_fingerprint` when the source state
  carries one;
- `exam_authoring_matching_manual_answer_key`: the Task 323 DTO exactly;
- `requested_targets`: optional target readiness keys, currently `examnet_pdf`
  and `qti_package`.

The route applies the submitted key to the supplied source-neutral interaction
and returns `exam_authoring_matching_apply_result_v1` with:

- `effective_interaction`: the corrected producer-owned matching state;
- `target_readiness`: target rows with export enablement, reason code, and
  message key;
- `artifact_availability`: artifact availability keyed by requested target.

Source binding is fail-closed. When the producer interaction carries
`source_item_fingerprint`, a missing or mismatched
`source_item_fingerprint` in the submitted manual key fails before target
readiness is projected. Consumers must submit the binding from returned producer
state, not infer it from local browser drafts.

The route rejects stale schema version, stale interaction ID, retired
`left_id`/`right_id` aliases, unknown source/target IDs, duplicate pairs,
association-bound failures, non-empty pairs with `absent` provenance, and
aggregate `mixed` provenance before any target is reported ready.

`examnet_pdf` readiness is projected through the current Exam.net PDF matching
profile. `qti_package` remains unavailable with
`examnet_qti_matching_import_unproven` until a governed Exam.net QTI import
proof exists. DigiExam ingestion overlays remain choice/gap-fill only and do
not accept matching keys through `digiexam_ingestion_overlay`.

This route is historical bridge work for the first missing matching producer
path. It is not the target path for new `PR-0332` teacher-correction work and it
must not survive the unified correction route implementation as an adapter,
shim, alias, wrapper, or compatibility layer. The accepted ADR-0011 target
teacher-correction architecture is not one `/exam-authoring/.../apply` route per
item type or source adapter. Task 327 owns the contract for one source-neutral
correction/apply route:

```text
POST /v2/exam-authoring/corrections/apply
```

That future contract must use typed correction entries for visible item text,
points, manual choice keys, manual gap/open-cloze accepted values, manual
matching keys, review decisions, and candidate suppression while keeping source
adapters as ingestion details. Consumers should not need to know whether the
original item came from DigiExam, Exam.net, CSV, DOCX, Markdown, or another
source in order to submit teacher corrections. When that unified route is
implemented, the matching manual-answer-key semantics above must move into a
typed matching correction entry and the matching-specific route must be removed
in the same governed implementation slice.

The draft unified correction/apply contract lives in
`docs/converters/exam-authoring-corrections-apply-contract.md`. It defines
`manual_matching_answer_key` as the target correction entry for the matching
semantics above and keeps this IR contract focused on source-neutral authoring
state rather than teacher-correction transport.

## Gap/Open-Cloze Interaction V1

Task 305 owns the first source-neutral gap/open-cloze accepted-value slice.
This contract preserves source intent even when a target cannot emit a native
gap item.

The gap/open-cloze interaction contains:

- stable interaction ID;
- ordered gaps with `gap_id`, display order, typed prompt/body binding, a
  required-for-auto-evaluation flag, and source evidence;
- accepted values per gap, with typed value-level provenance and evidence;
- normalization profile for validation and export decisions;
- derived answer-key provenance summary;
- source evidence records that can represent DigiExam `.dxe`, layout PDF,
  DOCX, Markdown, or future source families without faking a DigiExam shape.

Runtime value objects and validators live in:

- `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py`;
- `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py`.

Focused proof lives in:

- `tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`.

The neutral validator rejects duplicate gap IDs, blank gap IDs, duplicate or
invalid display order, blank prompt bindings, unknown gap IDs, blank accepted
values, duplicate normalized accepted values, accepted values with absent
provenance, accepted values with value-level mixed provenance, and accepted
values whose typed provenance contradicts known evidence origin.

Accepted-value provenance is the authoritative trust unit for automatic
evaluation. Accepted values themselves must use concrete trust states:
`source_provided`, `teacher_provided`, or `reviewed`. The answer-key provenance
summary is derived from its values: `absent`, one concrete provenance when all
values share it, or `mixed` when a multi-gap or multi-value key combines
source-provided, teacher-provided, or reviewed values.

Missing accepted values for required gaps keep the interaction structurally
valid but not ready for automatic evaluation. This distinction is deliberate:
source intent is still preserved, while target readiness and teacher follow-up
make the missing answer-key state visible.

Normalization profiles are:

- `exact_trim_case_sensitive`;
- `trim_case_insensitive`;
- `trim_case_punctuation_insensitive`.

Normalization is validation-owned. Spelling variants are not inferred; they
must appear as separate accepted values from trusted source, teacher/manual, or
reviewed evidence.

Target validators decide whether a gap/open-cloze interaction can be emitted as
native Exam.net PDF, free-text-style PDF with accepted values included, manual
accepted-current-state preservation, omitted with teacher approval, manual
recreation guidance, general QTI, future Exam.net QTI, or another target shape.

The current Exam.net PDF target profile keeps native gap-field import proof
separate from artifact correctness. Reviewed/source/teacher accepted values
must be preserved in the PDF artifact even when the PDF item renders as
free-text. A missing-key accepted-current-state fallback may preserve visible
content without accepted values only after an explicit teacher review decision.
That target limitation does not remove source-neutral gap/open-cloze semantics
from the IR.

QTI 3 documents `qti-gap-match-interaction`, and QTI 2.1 includes
`gapMatchInteraction`; these standards prove that gap interactions are QTI
concepts. Exam.net publicly advertises fill-the-gaps in its own authoring UI,
but Sir Convert must not claim native Exam.net gap import/export support until
a governed Exam.net proof path exists.

Matching-styled gap/open-cloze source shapes, such as a teacher workaround that
uses visible gap rows to simulate matching, stay in this neutral authoring
space. Source adapters preserve the evidence; target exporters decide whether
safe matching remapping is available.
