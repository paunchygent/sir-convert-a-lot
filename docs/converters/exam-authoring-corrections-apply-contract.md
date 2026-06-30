---
type: converter
id: CONV-exam-authoring-corrections-apply-contract
title: Exam Authoring Corrections Apply Contract
status: active
created: 2026-05-18
updated: 2026-06-30
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

Task 330 adds the runtime route and generated OpenAPI surface for the initial
`manual_matching_answer_key` implementation. Other entry kinds remain governed
contract shapes and are rejected explicitly by the initial runtime until later
implementation slices move those families from their current source-specific
paths into the unified route.

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
or artifact availability is projected. The Task 331 runtime treats any rejected
entry as batch-blocking: no correction-derived target readiness or artifact
availability is unlocked until the consumer resubmits a batch whose entries all
validate. Later item-level partial success requires a separate governed
contract change.

## Source-State Issuance Route

```text
POST /v2/exam-authoring/corrections/source-state/issue
Content-Type: application/json
```

Initial request schema:

```text
exam_authoring_correction_source_state_issue_request_v1
```

Initial response schema:

```text
exam_authoring_correction_source_state_issue_result_v1
```

This Sir Convert-owned producer surface resolves a server-owned source-state
artifact from a succeeded producer job, canonicalizes that persisted
`source_authoring_state`, recomputes `source_state_sha256`, and returns the
signed `source_binding` bundle that downstream consumers echo unchanged to
`POST /v2/exam-authoring/corrections/apply`. Consumers must not know or receive
`SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET`, must not post
browser-local state for signing, and must not mint their own signatures.
The current runtime producer that emits this artifact is the governed DigiExam
`digiexam_dxe -> examnet_migration_bundle` job path; future authoring producers
must emit the same source-neutral artifact before consumers can obtain a signed
correction bundle from their jobs.

Request:

```json
{
  "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
  "job_id": "jobv2_abc123",
  "expected_source_state_sha256": "sha256:optional-consumer-stale-state-guard"
}
```

Response:

```json
{
  "schema_version": "exam_authoring_correction_source_state_issue_result_v1",
  "source_binding": {
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:canonical-source-state",
    "source_state_signature": "hmac-sha256:producer-signature",
    "source_bundle_id": "bundle-123",
    "source_file_sha256": "sha256:source-file"
  },
  "source_authoring_state": {
    "schema_version": "exam_authoring_correction_source_state_v1",
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:canonical-source-state",
    "items": []
  }
}
```

The issuer derives `source_bundle_id` from the resolved producer job and
`source_file_sha256` from the server-stored upload bytes. If the job is missing,
not accessible, not succeeded, or lacks a server-owned correction source-state
artifact, issuance fails closed. A request body that includes
`source_authoring_state` is invalid; source state is never accepted from the
consumer path for signing.

The issuance route is not a Task 324 compatibility route, adapter, shim, alias,
wrapper, or route-preserving layer. It is source-neutral correction contract
plumbing for the same source-state bundle consumed by the unified apply route.

## Request Envelope

The request envelope binds the correction batch to producer-returned state:

```json
{
  "schema_version": "exam_authoring_corrections_apply_request_v1",
  "request_id": "correction-request-001",
  "source_binding": {
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "source_state_signature": "hmac-sha256:producer-signature",
    "source_bundle_id": "bundle-123",
    "source_file_sha256": "sha256:source-file"
  },
  "source_authoring_state": {
    "schema_version": "exam_authoring_correction_source_state_v1",
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "items": [],
    "advisory_answer_key_candidates": []
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
- supported visible text fields, including item title, prompt HTML, prompt
  lines, and option IDs/text for content patches;
- current bounded `max_score`;
- nested interaction IDs and interaction kind;
- choice IDs, gap IDs, matching source IDs, and matching target IDs where
  present;
- existing answer-key state and provenance when needed for validation;
- bounded first-pass advisory answer-key candidate context when advisory
  completion produced validated candidates;
- source or effective-state digests needed for stale-state rejection.

`advisory_answer_key_candidates` is producer-owned context for correction apply
and replay. Each row is item-addressed and limited to `item_id`, `sequence`,
`candidate_id`, `candidate_payload_digest`, `provider_profile_id`,
`schema_name`, `schema_version`, `prompt_template_version`, and
`validation_state`. It must not carry raw provider prompts or responses, source
file content, source paths, identity/session data, credentials, browser-local
state, student data, or UI drafts. Valid untouched candidates may project as
`review_required` / `current_key_origin = none` /
`advisory_candidate_pending`; invalid, skipped, or manual-follow-up candidates
do not become pending review rows.

For DigiExam `.dxe` producer state, the signed sidecar exposes only the
source-owned structures DigiExam actually carries: visible item text,
`max_score`, choice interactions with stable choice IDs, gap/open-cloze
interactions with stable gap IDs, and current answer-key provenance where
available. It intentionally emits no `matching_interactions` because the
current DigiExam IR has no canonical matching item type. Downstream
`manual_matching_answer_key` use requires a matching-capable producer governed
separately; consumers must not infer matching structure from DigiExam unknown
items, prompt prose, or browser-local drafts.

`source_binding.source_state_sha256` must match
`source_authoring_state.source_state_sha256`. The submitted
`source_authoring_state.source_state_sha256` must also equal Sir Convert's
canonical stable digest of the sanitized source-authoring state content,
computed without the digest field itself and including
`advisory_answer_key_candidates`. The binding must also carry
`source_state_signature`, a Sir Convert server signature over the source-state
digest, source-authoring schema version, source bundle ID, and source file
digest. A consumer may echo this signature from the producer-returned state but
must not mint it. If a source item or interaction carries a fingerprint in
producer state, the corresponding correction entry must echo it exactly.
Missing, mismatched, non-canonical, or non-authoritative binding fails before
effective state, rendering, target readiness, or artifact availability.

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

### Removed Review Decision Entry

Task 337 removes `review_decision` / `accept_current_state_for_export` from the
authoring correction contract. Authoring corrections mutate effective exam
state; export policy consumes effective state and produces artifacts.
Accepted-current-state is not durable exam state and must not be reintroduced
through correction replay unless a future export-only request contract
explicitly approves incomplete export.

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
| `candidate_suppression` | item ID, sequence, item type, source item fingerprint, candidate lineage | Candidate hidden/rejected in report only | readiness unlock attempt, missing candidate digest, raw provider data, replacement key hidden inside suppression |

Validation order:

1. Validate request schema and reject unknown fields.
1. Validate request-level source binding, canonical source-state digest, and
   signed producer-state authority.
1. If the validated binding carries `source_bundle_id`, resolve and authorize
   that source job before returning any success with exportable readiness,
   available artifacts, or replay references.
1. Validate every entry's item and nested-interaction binding.
1. Validate entry-specific semantics.
1. If any entry is rejected, stop before mutating effective state or projecting
   correction-derived readiness/artifacts.
1. Apply accepted entries to effective state in request order.
1. Recompute target readiness from accepted effective state.
1. Report accepted and rejected entries without leaking raw submitted payloads.

## Source-Job Fail-Closed Behavior

Current DigiExam correction apply is source-bound when
`source_binding.source_bundle_id` is present. After schema, canonical
source-state digest, and source-state signature validation succeed, Sir Convert
must resolve and authorize that source job before any successful response can
advertise exportable target readiness, available artifact rows, or correction
replay references.

A missing or expired bound source job returns the standard Service API error
envelope:

```json
{
  "error": {
    "code": "exam_authoring_correction_source_job_unavailable",
    "message": "Correction replay source job is unavailable.",
    "retryable": false
  }
}
```

The HTTP status is `409 Conflict`. A wrong owner or missing required artifact
read grant remains `403 exam_authoring_correction_replay_access_denied`.
Invalid, stale, or forged source-state bindings are still rejected before source
job lookup so callers cannot probe job existence through bad signatures.

Success without source-job lookup is reserved for an explicit non-artifact
correction mode with no `source_bundle_id`, no requested export targets, no
available artifact availability, and no replay references. That mode preserves
source-state and review projection tests only; it is not a DigiExam correction
replay artifact path.

## Response Projection

The route returns producer-owned effective state and reports:

```json
{
  "schema_version": "exam_authoring_corrections_apply_result_v1",
  "request_id": "correction-request-001",
  "source_binding": {
    "source_authoring_schema_version": "exam_authoring_ir_v1",
    "source_state_sha256": "sha256:source-state",
    "source_state_signature": "hmac-sha256:producer-signature",
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
  "answer_key_review_state": {
    "schema_version": "digiexam_answer_key_review_state_v1",
    "items": []
  },
  "target_readiness": {
    "schema_version": "target_readiness_report_v1",
    "targets": [
      {
        "target": "examnet_pdf",
        "artifact_key": "correction_replay_examnet_pdf",
        "readiness": "ready",
        "export_enabled": true,
        "reason_code": "ready",
        "message_key": "exam_converter.target.ready",
        "item_id": null,
        "sequence": null,
        "artifact_reference": {
          "schema_version": "correction_replay_artifact_reference_v1",
          "job_id": "bundle-123",
          "artifact_set_id": "crset-request-scoped",
          "artifact_key": "correction_replay_examnet_pdf",
          "target": "examnet_pdf",
          "content_sha256": "sha256:artifact-content",
          "request_id": "correction-request-001",
          "source_binding_digest": "sha256:source-binding",
          "source_state_sha256": "sha256:source-state",
          "correction_payload_digest": "sha256:correction-payload",
          "target_set_digest": "sha256:target-set",
          "replay_profile_version": "digiexam_correction_replay_v1",
          "created_at": "2026-06-30T00:00:00Z"
        }
      }
    ]
  },
  "artifact_availability": [
    {
      "artifact_key": "examnet_pdf",
      "availability": "available",
      "unavailable_code": null,
      "artifact_reference": {
        "schema_version": "correction_replay_artifact_reference_v1",
        "job_id": "bundle-123",
        "artifact_set_id": "crset-request-scoped",
        "artifact_key": "correction_replay_examnet_pdf",
        "target": "examnet_pdf",
        "content_sha256": "sha256:artifact-content",
        "request_id": "correction-request-001",
        "source_binding_digest": "sha256:source-binding",
        "source_state_sha256": "sha256:source-state",
        "correction_payload_digest": "sha256:correction-payload",
        "target_set_digest": "sha256:target-set",
        "replay_profile_version": "digiexam_correction_replay_v1",
        "created_at": "2026-06-30T00:00:00Z"
      }
    }
  ]
}
```

Rejected entries include `entry_id`, `kind`, item binding, `reason_code`,
`message_key`, `teacher_action`, and `retryable`. They must not echo raw overlay
JSON, raw provider payloads, raw source text, credentials, student data, or
identity markers.

Accepted entries report applied fields by typed domain names, for example
`item_text_patch`, `point_correction`, `answer_key`, or
`candidate_suppression`. Candidate suppression is reported separately from
answer-key application.

`answer_key_review_state` is the same compact producer projection emitted as
the DigiExam first-pass `answer_key_review_state_report` artifact. Correction
apply/replay responses return it at top level so consumers do not join
`effective_state`, correction reports, target readiness, local correction
sessions, and first-pass advisory artifacts to infer answer-key review state.
It uses strict `review_state`, `current_key_origin`, and reason vocabularies
from Task 373, may include bounded `provenance_detail` for detail display, and
must reject generic `history`, `review_decision`,
`accept_current_state_for_export`, and other accepted-current-state substitutes.
When one advisory candidate is accepted, that item becomes `review_complete`
with `current_key_origin = reviewed_advisory` and
`reasons = [reviewed_advisory_accepted]`. Untouched valid sibling candidates
from the signed source-state remain `review_required` with
`current_key_origin = none` and `reasons = [advisory_candidate_pending]`.
Untouched keyed rows with no valid advisory candidate remain validation rows
such as `no_correct_choice_selected` or
`required_gap_accepted_values_missing`. Free-text/open-writing rows are not
expanded into advisory keyed answer-key review; they return
`review_complete` / `current_key_origin = none` /
`answer_key_not_applicable` for this projection even if malformed advisory
context references them.

Replay artifact references appear inside the projection only after Sir Convert
has produced replay-scoped target artifacts such as
`correction_replay_examnet_pdf` or `correction_replay_qti_package`. They do not
replace `target_readiness_report_v1`, which remains the export-action
authority.

## Request-Scoped Correction Replay Artifacts

Corrected replay artifacts are immutable request-scoped artifact sets. Sir
Convert stores each set under:

```text
correction-replays/{artifact_set_id}/manifest.json
correction-replays/{artifact_set_id}/{target-file}
```

The nested download route is:

```text
GET /v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}?content_sha256={content_sha256}
```

The existing named-artifact route
`/v2/convert/jobs/{job_id}/artifacts/{artifact_key}` is not correction replay
download authority for static `correction_replay_*` keys. Consumers must use
the typed `artifact_reference` returned by correction apply. Sir Convert never
falls back to the latest bytes for a source job.

Each `correction_replay_artifact_reference_v1` contains:

- `schema_version`
- `job_id`
- `artifact_set_id`
- `artifact_key`
- `target`
- `content_sha256`
- `request_id`
- `source_binding_digest`
- `source_state_sha256`
- `correction_payload_digest`
- `target_set_digest`
- `replay_profile_version`
- `created_at`

The artifact-set manifest records the same request identity plus artifact
content hashes. Exact duplicate normalized correction requests may return the
same verified artifact set. Reusing the same `request_id` with different
normalized content returns
`409 exam_authoring_correction_replay_request_conflict`.

Missing artifact sets return:

```json
{
  "error": {
    "code": "correction_replay_artifact_set_not_found",
    "message": "Correction replay artifact set was not found.",
    "retryable": false
  }
}
```

The HTTP status is `404 Not Found`. Wrong job, artifact set, artifact key, or
`content_sha256` returns:

```json
{
  "error": {
    "code": "correction_replay_artifact_reference_mismatch",
    "message": "Correction replay artifact reference does not match the stored artifact set.",
    "retryable": false
  }
}
```

The HTTP status is `409 Conflict`. Artifact references and manifests remain
content-safe metadata only; they must not include raw source payloads, private
filesystem paths, teacher identity data, source text, signatures, grant
envelopes, uploaded bytes, or provider responses.

## Compatibility And Hard Cut

Task 324 created:

```text
POST /v2/exam-authoring/matching/manual-answer-key/apply
```

That route is superseded and abandoned as an implementation path. Task 330
removes it rather than preserving it as an adapter, shim, alias, wrapper, or
compatibility layer.

Task 330 implements the hard cut:

- added `POST /v2/exam-authoring/corrections/apply`;
- moved Task 324 matching semantics into `manual_matching_answer_key`;
- removed the matching-specific route registration and OpenAPI path exposure;
- removed request/response code that existed only for the matching-specific route;
- rewrote route-specific tests to assert the old route is not accepted;
- kept reusable matching value objects, DTOs, or validators only where they are
  directly used by the unified correction-entry implementation;
- proved that requests to the old matching route are not accepted.

Existing DigiExam `digiexam_ingestion_overlay_v2` semantics map into the unified
contract as follows:

| Existing field | Unified entry |
| --- | --- |
| `effective_item_patch` | `item_text_patch` |
| `point_correction` | `point_correction` |
| `manual_answer_key.kind == "choice"` | `manual_choice_answer_key` |
| `manual_answer_key.kind == "gap_fill"` | `manual_gap_open_cloze_answer_key` |
| `reviewed_completion_answer_key` | answer-key entry with advisory `submission_origin` and `candidate_lineage` |
| Task 324 matching DTO | `manual_matching_answer_key` |

This mapping is semantic, not a runtime compatibility promise. Task 330
performed the route hard cut. Task 333 implements runtime support for the
DigiExam-backed non-matching entries that HuleEdu/Skriptoteket may consume
after the HuleEdu unified authenticated edge lands: item text, point, choice,
and gap/open-cloze corrections. Task 332 owns later
`manual_matching_answer_key` downstream enablement through a real
matching-capable producer.

## Consumer Sequencing

1. Task 327 completed this contract artifact.
1. Review 23 accepted ADR-0011 as the source-neutral correction/apply decision.
1. Task 330 adds the unified route and removes the Task 324 matching-specific
   route/dead code in the same governed slice.
1. Task 331 remediates Review 24's contract blockers for producer-state
   authority, advisory lineage, batch unlock, validation privacy, and DigiExam
   source-owned text/point/choice/gap state. Downstream matching use remains
   blocked on Task 332 because DigiExam source state emits no real
   `matching_interactions`.
1. Task 333 implemented runtime apply behavior for the DigiExam-backed
   non-matching families whose producer-issued source state exists:
   point, choice, gap/open-cloze, and item text corrections.
1. HuleEdu replaces the abandoned Task 324 matching-specific edge with the
   single unified source-state issue/apply edge through authenticated
   `/sir-convert`.
1. Skriptoteket PR-0332 migrates teacher-correction submission to the unified
   route only after both the Sir Convert runtime support and HuleEdu product
   edge exist for that correction family. For `manual_matching_answer_key`, that
   means Task 332 must first provide a matching-capable producer.

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

Validation-error envelopes must preserve only bounded diagnostic shape such as
location, error type, and message. They must not echo raw submitted `input`,
unsafe `ctx` fragments, raw overlay/source values, credentials, student data, or
identity markers.

Teacher corrections alter effective authoring state or effective renderer input
only. They never mutate parser-owned source IR, source evidence, parser
provenance, or advisory-candidate production history.
