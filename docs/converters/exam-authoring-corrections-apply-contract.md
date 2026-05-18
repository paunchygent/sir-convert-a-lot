---
type: converter
id: CONV-exam-authoring-corrections-apply-contract
title: Exam Authoring Corrections Apply Contract
status: draft
created: 2026-05-18
updated: 2026-05-18
owners:
  - platform
tags:
  - exam-authoring
  - correction-contract
  - source-neutral
  - skriptoteket
  - huleedu
  - api
links:
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
---

## Purpose

Define the draft source-neutral teacher-correction apply contract for exam
authoring:

```text
POST /v2/exam-authoring/corrections/apply
```

This route is the canonical target for teacher-authored correction application
under accepted ADR-0011 once the runtime or consumer work is attached to its own
governed implementation slice. It replaces the route-per-item direction with one
producer-owned API that validates source-bound corrections, projects effective
authoring state, recomputes target readiness, and reports artifact availability.

This document remains draft until the follow-up implementation task adds the
runtime route and generated OpenAPI surface. It is intentionally contract-only:
it does not claim that the route exists in current OpenAPI or runtime.

## Product Boundary

The correction API is source-neutral from the consumer perspective. HuleEdu and
Skriptoteket must not need to know whether the original exam came from DigiExam,
Exam.net, CSV, DOCX, Markdown, or another future source in order to submit a
teacher correction.

Source adapters remain ingestion details. They may own source-native parse
models, evidence, fingerprints, and adapter mapping into a producer-returned
authoring state. Sir Convert owns:

- correction validation;
- source-binding checks;
- effective-state projection;
- target-readiness recomputation;
- artifact availability reporting.

Browser-local edits are never authoritative. A consumer can enable download,
save, or export only after Sir Convert returns accepted effective state and
target readiness from this route.

## Route

```text
POST /v2/exam-authoring/corrections/apply
Content-Type: application/json
```

Initial request schema:

```text
exam_authoring_corrections_apply_request_v1
```

Initial response schema:

```text
exam_authoring_corrections_apply_result_v1
```

The route accepts one source-bound authoring state plus an ordered list of typed
correction entries. All entries are validated before effective state, readiness,
or artifact availability is projected. A batch can return accepted and rejected
entries, but rejected entries must not partially unlock files.

## Request Envelope

The request envelope binds the correction batch to producer-returned state:

```json
{
  "schema_version": "exam_authoring_corrections_apply_request_v1",
  "request_id": "correction-request-001",
  "source_binding": {
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "source_bundle_id": "bundle-123",
    "source_file_sha256": "sha256:source-file"
  },
  "source_authoring_state": {
    "schema_version": "exam_authoring_correction_source_state_v1",
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "items": []
  },
  "corrections": [],
  "requested_targets": ["examnet_pdf", "qti_package"]
}
```

`source_authoring_state` is the sanitized producer-returned state needed for
binding and validation. It must not contain raw `.dxe`, raw PDF text, raw
provider data, raw overlay JSON, credentials, identity markers, student-result
data, earned scores, wrong selections, free-text student answers, or per-student
performance history.

The initial source-state projection must expose only the data needed to validate
teacher corrections:

- `item_id`;
- `sequence`;
- `item_type`;
- optional `source_item_fingerprint`;
- supported visible text fields and option IDs for content patches;
- current bounded `max_score`;
- nested interaction IDs and interaction kind;
- choice IDs, gap IDs, matching source IDs, and matching target IDs where
  present;
- existing answer-key state and provenance when needed for validation;
- source or effective-state digests needed for stale-state rejection.

`source_binding.source_state_sha256` must match
`source_authoring_state.source_state_sha256`. If a source item or interaction
carries a fingerprint in producer state, the corresponding correction entry must
echo it exactly. Missing or mismatched binding fails before rendering or target
readiness.

## Correction Entry Union

Every correction entry uses a strict typed discriminator:

```json
{
  "entry_id": "corr-001",
  "kind": "point_correction",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source"
}
```

Common entry fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `entry_id` | yes | Consumer-stable correction ID used in accepted/rejected reports. |
| `kind` | yes | Typed correction discriminator. |
| `item_id` | yes | Producer-returned item ID. |
| `sequence` | yes | Producer-returned item sequence. |
| `item_type` | yes | Producer-returned item type at submission time. |
| `source_item_fingerprint` | when producer state has one | Fail-closed source item binding. |
| `interaction_id` | when nested interaction is touched | Producer-returned choice/gap/matching interaction ID. |
| `submission_origin` | when answer-key data is submitted | `teacher_authored`, `accepted_advisory_candidate`, or `teacher_edited_advisory_candidate`. |
| `candidate_lineage` | for advisory candidate origins | Bounded candidate lineage, never raw provider data. |

Unknown fields fail schema validation. The contract must not accept an untyped
JSON patch, source-adapter-specific overlay blob, retired matching alias, or
generic `metadata` escape hatch.

## Entry Shapes

### Item Text Patch

```json
{
  "entry_id": "corr-text-001",
  "kind": "item_text_patch",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "patches": [
    {
      "field": "prompt_html",
      "value": "<p>Updated prompt</p>"
    },
    {
      "field": "visible_option_text",
      "choice_id": "choice-002",
      "value": "Updated visible option"
    }
  ]
}
```

Supported fields are `item_title`, `stem_html`, `prompt_html`,
`body_html`, `visible_option_text`, and `gap_prompt_text` where the source state
exposes the addressed field or nested ID. The patch changes effective renderer
input only. It never creates answer-key evidence, point correction, parser
provenance, or target readiness by itself.

### Point Correction

```json
{
  "entry_id": "corr-points-001",
  "kind": "point_correction",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "max_score": 3
}
```

`max_score` must be a strict positive integer. Zero, negative, fractional,
string-coerced, rubric, marking-matrix, scoring-policy, and partial-credit
payloads fail before effective state or artifacts are projected.

### Manual Choice Answer Key

```json
{
  "entry_id": "corr-choice-key-001",
  "kind": "manual_choice_answer_key",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "interaction_id": "choice-001",
  "submission_origin": "teacher_authored",
  "correct_choice_ids": ["choice-002"]
}
```

Choice IDs must exist in the producer state for the addressed interaction.
Single-choice items accept exactly one correct choice. Multiple-response items
accept one or more correct choices according to the producer item type. The
entry maps to effective answer-key provenance `teacher_provided` unless
`submission_origin` is advisory-candidate based.

### Manual Gap/Open-Cloze Answer Key

```json
{
  "entry_id": "corr-gap-key-001",
  "kind": "manual_gap_open_cloze_answer_key",
  "item_id": "item-002",
  "sequence": 2,
  "item_type": "gap_fill",
  "source_item_fingerprint": "sha256:item-source",
  "interaction_id": "gap-001",
  "submission_origin": "teacher_authored",
  "gap_answers": [
    {
      "gap_id": "gap-001-a",
      "accepted_values": ["fotosyntes"]
    }
  ]
}
```

Each `gap_id` must exist in producer state. Each required gap needs at least one
accepted value before the item can become automatically evaluable. Accepted
values are answer-key data and must be preserved in effective state and target
artifacts when target generation succeeds.

### Manual Matching Answer Key

```json
{
  "entry_id": "corr-matching-key-001",
  "kind": "manual_matching_answer_key",
  "item_id": "item-003",
  "sequence": 3,
  "item_type": "matching",
  "source_item_fingerprint": "sha256:item-source",
  "interaction_id": "matching-001",
  "submission_origin": "teacher_authored",
  "pairs": [
    {
      "source_id": "source-001",
      "target_id": "target-001"
    }
  ]
}
```

This entry is the target shape for Task 324 matching semantics. It uses exact
`source_id` and `target_id` directed pairs. Retired `left_id` and `right_id`
aliases fail schema validation. Unknown IDs, duplicate identical pairs,
association-bound violations, aggregate `mixed` provenance, and non-empty pairs
with absent provenance fail before target readiness.

### Reviewed Candidate Answer Key

Choice, gap/open-cloze, and matching key entries may use advisory candidate
lineage when the teacher accepts or edits a producer candidate:

```json
{
  "entry_id": "corr-reviewed-choice-001",
  "kind": "manual_choice_answer_key",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "interaction_id": "choice-001",
  "submission_origin": "accepted_advisory_candidate",
  "candidate_lineage": {
    "completion_report_sha256": "sha256:completion-report",
    "candidate_id": "candidate-item-001",
    "candidate_payload_digest": "sha256:candidate-payload",
    "provider_profile_id": "local-structured",
    "schema_name": "digiexam_choice_answer_key_decision_v1",
    "schema_version": "digiexam_choice_answer_key_decision_v1",
    "prompt_template_version": "digiexam_choice_answer_key_prompt_v1",
    "validation_state": "valid"
  },
  "correct_choice_ids": ["choice-002"]
}
```

For `accepted_advisory_candidate`, the submitted answer-key payload must digest
to `candidate_lineage.candidate_payload_digest`. For
`teacher_edited_advisory_candidate`, the answer-key payload may differ but must
validate against the same item-local ID/value rules. Accepted advisory candidates
map to effective answer-key provenance `reviewed`; teacher-edited advisory
candidates map to `teacher_provided` with candidate lineage.

### Review Decision

```json
{
  "entry_id": "corr-review-001",
  "kind": "review_decision",
  "item_id": "item-004",
  "sequence": 4,
  "item_type": "multiple_response",
  "source_item_fingerprint": "sha256:item-source",
  "decision": "accept_current_state_for_export",
  "decision_id": "review-123",
  "accepted_targets": ["examnet_pdf"],
  "note": "Teacher accepts export without a machine-marked answer key."
}
```

`accept_current_state_for_export` is not an answer key. It can enable export only
after Sir Convert validates the source binding, applies the governed
accepted-current-state target policy, creates target bytes, and validates those
bytes. It never creates answer-key provenance and never changes source parser
provenance.

### Candidate Suppression

```json
{
  "entry_id": "corr-suppress-001",
  "kind": "candidate_suppression",
  "item_id": "item-001",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "candidate_lineage": {
    "completion_report_sha256": "sha256:completion-report",
    "candidate_id": "candidate-item-001",
    "candidate_payload_digest": "sha256:candidate-payload",
    "provider_profile_id": "local-structured",
    "schema_name": "digiexam_choice_answer_key_decision_v1",
    "schema_version": "digiexam_choice_answer_key_decision_v1",
    "prompt_template_version": "digiexam_choice_answer_key_prompt_v1",
    "validation_state": "valid"
  },
  "suppression_reason": "teacher_rejected_candidate"
}
```

Candidate suppression rejects or hides an advisory candidate for the addressed
item. It does not apply a key, create manual-unkeyed state, accept current state,
clear readiness blockers, or unlock PDF/QTI artifacts. Any later replacement key
must be submitted as a separate answer-key correction entry.

## Validation Matrix

| Entry kind | Required binding | Supported result | Fail-closed examples |
| --- | --- | --- | --- |
| `item_text_patch` | item ID, sequence, item type, source item fingerprint, addressed field or nested ID | Effective visible content changes; no key or readiness unlock by itself | unknown field, unsupported item type, missing choice/gap ID, stale fingerprint |
| `point_correction` | item ID, sequence, item type, source item fingerprint | Effective `max_score` changes and target readiness recomputes | zero/negative/fractional score, rubric payload, stale item binding |
| `manual_choice_answer_key` | item ID, sequence, item type, source item fingerprint, choice interaction ID, choice IDs | Effective answer key with teacher or reviewed provenance | unknown choice ID, wrong item type, multiple IDs on single-choice item, candidate digest mismatch |
| `manual_gap_open_cloze_answer_key` | item ID, sequence, item type, source item fingerprint, gap interaction ID, gap IDs | Effective accepted values for addressed gaps | unknown gap ID, empty required accepted values, wrong item type, stale binding |
| `manual_matching_answer_key` | item ID, sequence, item type, source item fingerprint, matching interaction ID, source/target IDs | Effective directed matching pairs | retired `left_id`/`right_id`, unknown IDs, duplicate pairs, association-bound failure, opaque `mixed` provenance |
| `review_decision` | item ID, sequence, item type, source item fingerprint, decision ID, accepted targets | Governed accepted-current-state target policy may run; no key is created | unsupported target, decision treated as answer key, stale binding, missing policy |
| `candidate_suppression` | item ID, sequence, item type, source item fingerprint, candidate lineage | Candidate hidden/rejected in report only | readiness unlock attempt, missing candidate digest, raw provider data, replacement key hidden inside suppression |

Validation order:

1. Validate request schema and reject unknown fields.
1. Validate request-level source binding and source-state digest.
1. Validate every entry's item and nested-interaction binding.
1. Validate entry-specific semantics.
1. Apply accepted entries to effective state in request order.
1. Recompute target readiness from accepted effective state.
1. Report accepted and rejected entries without leaking raw submitted payloads.

## Response Projection

The route returns producer-owned effective state and reports:

```json
{
  "schema_version": "exam_authoring_corrections_apply_result_v1",
  "request_id": "correction-request-001",
  "source_binding": {
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "source_bundle_id": "bundle-123",
    "source_file_sha256": "sha256:source-file"
  },
  "effective_state": {
    "schema_version": "exam_authoring_effective_state_v1",
    "effective_state_sha256": "sha256:effective-state",
    "items": []
  },
  "correction_report": {
    "schema_version": "exam_authoring_correction_report_v1",
    "accepted_entries": [
      {
        "entry_id": "corr-choice-key-001",
        "kind": "manual_choice_answer_key",
        "item_id": "item-001",
        "sequence": 1,
        "applied_fields": ["answer_key"],
        "effective_provenance": "teacher_provided"
      }
    ],
    "rejected_entries": []
  },
  "target_readiness": {
    "schema_version": "target_readiness_report_v1",
    "targets": []
  },
  "artifact_availability": []
}
```

Rejected entries include `entry_id`, `kind`, item binding, `reason_code`,
`message_key`, `teacher_action`, and `retryable`. They must not echo raw overlay
JSON, raw provider payloads, raw source text, credentials, student data, or
identity markers.

Accepted entries report applied fields by typed domain names, for example
`item_text_patch`, `point_correction`, `answer_key`, `review_decision`, or
`candidate_suppression`. Candidate suppression is reported separately from
answer-key application.

## Compatibility And Hard Cut

Task 324 created:

```text
POST /v2/exam-authoring/matching/manual-answer-key/apply
```

That route is historical bridge work only. The unified implementation must not
preserve it as an adapter, shim, alias, wrapper, or compatibility layer.

The follow-up implementation task must:

- add `POST /v2/exam-authoring/corrections/apply`;
- move Task 324 matching semantics into `manual_matching_answer_key`;
- remove the matching-specific route registration and OpenAPI path exposure;
- remove request/response code that exists only for the matching-specific route;
- remove or rewrite route-specific tests that assert the old route;
- keep reusable matching value objects, DTOs, or validators only where they are
  directly used by the unified correction-entry implementation;
- prove that requests to the old matching route are not accepted.

Existing DigiExam `digiexam_ingestion_overlay_v2` semantics map into the unified
contract as follows:

| Existing field | Unified entry |
| --- | --- |
| `effective_item_patch` | `item_text_patch` |
| `point_correction` | `point_correction` |
| `manual_answer_key.kind == "choice"` | `manual_choice_answer_key` |
| `manual_answer_key.kind == "gap_fill"` | `manual_gap_open_cloze_answer_key` |
| `reviewed_completion_answer_key` | answer-key entry with advisory `submission_origin` and `candidate_lineage` |
| `review_decision.kind == "accept_current_state_for_export"` | `review_decision` |
| Task 324 matching DTO | `manual_matching_answer_key` |

This mapping is semantic, not a runtime compatibility promise. Task 327 does not
authorize the runtime route or deletion work. The later unified-route
implementation must perform the add/remove hard cut atomically.

## Consumer Sequencing

1. Task 327 completed this contract artifact.
1. Review 23 accepted ADR-0011 as the source-neutral correction/apply decision.
1. A Sir Convert implementation task adds the unified route and removes the
   Task 324 matching-specific route/dead code in the same governed slice.
1. HuleEdu proxies the single unified route through authenticated
   `/sir-convert`.
1. Skriptoteket PR-0332 migrates teacher-correction submission to the unified
   route and treats returned effective state/readiness as authoritative.

## Privacy And Provenance

The contract must remain at least as strict as the DigiExam overlay and matching
apply contracts. Requests and reports must not contain:

- raw `.dxe`;
- raw PDF text;
- raw overlay JSON;
- raw provider responses or raw prompts;
- credentials or API keys;
- identity markers beyond governed auth context;
- student-result data;
- earned scores;
- wrong selections;
- free-text student answers;
- per-student performance history.

Teacher corrections alter effective authoring state or effective renderer input
only. They never mutate parser-owned source IR, source evidence, parser
provenance, or advisory-candidate production history.
