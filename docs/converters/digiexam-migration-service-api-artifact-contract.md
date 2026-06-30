---
type: converter
id: CONV-digiexam-migration-service-api-artifact-contract
title: DigiExam Migration Service API Artifact Contract
status: active
created: 2026-05-11
updated: 2026-06-29
owners:
  - platform
tags:
  - digiexam
  - exam-migration
  - examnet
  - api
  - v2
  - artifact-bundle
  - skriptoteket
links:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md
  - docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md
  - docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/multi_format_conversion_service_api_v2_errors.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md
  - docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
---

## Purpose

Define the service API v2 extension contract for DigiExam migration jobs
submitted by Skriptoteket and executed by Sir Convert-a-Lot. The default lane is
authenticated Skriptoteket product work. A narrow public Exam Converter grant
lane is defined below as a separate contract exception for future runtime work.

This contract is the boundary between the products:

- Sir Convert owns parsing, sanitized evidence enrichment, intermediate
  representation generation, Exam.net artifact rendering, bundle manifesting,
  retention, and job/artifact authorization.
- Skriptoteket owns teacher-facing upload UX, progress presentation, artifact
  download, and save-to-authenticated-user-files persistence.

The contract is active runtime authority for the Sir Convert downstream service
route implemented by Task 282. HuleEdu Gateway exposure and Skriptoteket UI/user
file persistence remain separate cutover tasks in the owning repos.

This is one route in a shared exam-artifact service API family. Normal
teacher-owned Exam.net PDFs, Word exports, answer keys, and QTI authoring
artifacts belong to the separate
`examnet_artifact -> teacher_authoring_bundle` route defined by Story 45 /
Task 279, not to this DigiExam `.dxe` migration route.

## Relationship To Existing V2 API

DigiExam migration uses the service API v2 job lifecycle:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- named artifact listing and download endpoints defined below for this bundle
  route.

The generated OpenAPI contract is part of the consumer contract. Sir Convert
exports it with `pdm run openapi-export-v2` to
`docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`. That snapshot must
match the runtime FastAPI schema and include the DigiExam migration multipart
JSON-part schemas, bundle manifest, effective exam, overlay report, and
target-readiness report components before Skriptoteket live Docker/service
tests rely on changed API behavior.

The route is a v2 extension with this route key:

```json
{
  "source.format": "digiexam_dxe",
  "conversion.output_format": "examnet_migration_bundle"
}
```

The sibling Exam.net authoring route reuses the v2 job lifecycle and named
artifact-bundle pattern, but it has a different source authority and route key:

```json
{
  "source.format": "examnet_artifact",
  "conversion.output_format": "teacher_authoring_bundle"
}
```

Consumers must choose the route from source provenance. Exam.net-origin PDFs
or Word exports must not be submitted to this DigiExam route just to reuse the
bundle contract.

The canonical v2 job status enum remains unchanged. A `succeeded` job means Sir
Convert produced a terminal migration bundle. Target-specific readiness is
reported inside the bundle through `target_readiness_report_v1`; consumers must
not infer target availability from job status or bundle status alone.

## Bundle V3 Cutover

Task 294 introduced the first hard migration-bundle break for overlay and
effective-exam semantics. Task 298 supersedes that baseline with the current
`digiexam_migration_bundle_v3` contract so matching answer-key pairs can be
represented without compatibility aliases. There is no compatibility shim,
source-only fallback lane, or dual-version response mode for older bundle
contracts. Existing consumers must migrate to the v3 manifest, target
readiness report, and effective-exam semantics before depending on this route.

Task 337 and Task 373 hard-cut the old accepted-current-state/review-decision
model. Skriptoteket sends concrete teacher corrections, manual answer keys, or
reviewed advisory acceptance/edit intents. Sir Convert validates those inputs,
recomputes the effective exam, emits `answer_key_review_state` for correction
apply/replay, and keeps `target_readiness_report_v1` as the export authority
before consumers enable PDF or QTI downloads. No compatibility path accepts
generic `review_decision`, `history`, or `accept_current_state_for_export`
payloads.

Task 295 implements runtime application for manual answer keys. Task 302
implements runtime application of supported
`effective_item_patch` values for item text, option text, prompt/body,
and gap-fill visible prompt repair.
Task 373 owns the compact answer-key review-state projection used by first-pass
bundle jobs and correction apply/replay responses.

## Cutover Route Boundary

The product/browser route is HuleEdu Gateway-owned:

- browser/product entry: `/sir-convert/v2/convert/...`
- downstream Sir Convert service route: `/v2/convert/...`

The Gateway strips the `/sir-convert` product prefix when forwarding to Sir
Convert and signs `InternalIdentityContextV1` for Sir Convert with
`aud="sir-convert-a-lot"`. Sir Convert must not implement a second
`/sir-convert/v2/...` route family internally.

`convert.hule.education` remains reserved/fail-closed for browser product
traffic. Direct anonymous conversion, direct browser conversion, status pages,
or external M2M access on that host require a separate accepted ADR/task.

## Authentication And Ownership

Current transport remains aligned with service API v2 and
`internal_adapter_contract_v2.md`:

- `X-API-Key` proves the caller is an allowed internal integration transport
  during migration.
- `Idempotency-Key` is required for job creation.
- `X-Correlation-ID` is optional but strongly recommended and is returned by
  the service.

User-originated Skriptoteket calls must preserve HuleEdu
`InternalIdentityContextV1` with audience `sir-convert-a-lot` as described in
`ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
`X-API-Key` alone is not job ownership and must not authorize cross-user job,
result, or artifact access after the Gateway/internal identity cutover.

Signed identity headers MUST use this exact HuleEdu casing in docs, tests, and
client examples:

- `X-HuleEdu-Identity-Context-Version`
- `X-HuleEdu-Identity-Context`
- `X-HuleEdu-Identity-Key-Id`
- `X-HuleEdu-Identity-Signature`

Required signed identity claims:

- `context_version`: `1`
- `iss`: `api_gateway_service`
- `aud`: `sir-convert-a-lot`
- `iat` / `exp`: valid within the configured clock skew and TTL; current Sir
  Convert default TTL is 60 seconds.

Required Sir Convert grants by route:

| Downstream service route | Required grant |
| --- | --- |
| `POST /v2/convert/jobs` | `sir-convert:jobs:create` |
| `GET /v2/convert/jobs/{job_id}` | `sir-convert:jobs:read-own` |
| `GET /v2/convert/jobs/{job_id}/result` | `sir-convert:jobs:read-own` |
| `POST /v2/convert/jobs/{job_id}/cancel` | `sir-convert:jobs:cancel-own` |
| `GET /v2/convert/jobs/{job_id}/artifact` | `sir-convert:artifacts:read-own` |
| `GET /v2/convert/jobs/{job_id}/artifacts` | `sir-convert:artifacts:read-own` |
| `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}` | `sir-convert:artifacts:read-own` |

For this route, persisted job ownership is derived from the verified identity
context:

- `owner_kind`: `user`
- `owner_realm`: signed product realm when present, otherwise signed
  `source_app`
- `owner_subject_id`: signed realm subject when present, otherwise signed
  `sub`
- `org_id` and `tenant_id`: signed values
- `source_app`: expected `skriptoteket` for the product workflow
- `workload_purpose`: `product_conversion`

Task 282 runtime persists the owner as a deterministic Sir Convert scope:
`identity:v1:user:sha256:<digest>`, where the digest is computed over the
signed owner envelope above. Product-visible artifacts must not expose raw
identity envelopes unless a later audit contract explicitly authorizes it.

The following reads are owner-scoped and fail closed with `403` for other
users even when the transport API key is valid:

- job status
- terminal result
- artifact bundle listing
- named artifact download
- checkpoint or future partial-route reads if later added to this route

Direct anonymous public conversion is not part of this contract. The only public
exception is the HuleEdu-signed public Exam Converter grant lane below.

## Public Exam Converter Grant Lane

Task 291 adds a contract-only public grant lane for the blocked Skriptoteket
`PR-0320` no-login Exam Converter workflow. It does not implement public runtime
conversion, does not reopen `convert.hule.education`, and does not change the
authenticated `InternalIdentityContextV1` behavior above.

The authority chain is intentionally split:

- HuleEdu `TASK-0563` and
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/reference/ref-public-exam-converter-grant-v1-contract.md`
  define the minting authority and normative `PublicConversionGrantV1` field
  contract.
- This Sir Convert contract defines verifier input, public job ownership,
  route operations, artifact-read authorization, and rejection behavior.
- Skriptoteket `PR-0320` remains blocked until the HuleEdu grant authority and
  this Sir Convert verifier/ownership contract are both accepted by their
  respective review gates.

### Public Grant Boundary

`PublicConversionGrantV1` is not `InternalIdentityContextV1`, not a browser
session, not a user identity, not service ownership, and not an operator lane.
It must not contain user, org, tenant, role, product-realm subject, email,
display-name, session, or linked-identity fields.

The browser never calls Sir Convert directly and never receives Sir Convert
transport credentials, HuleEdu signing material, or a self-constructed grant.
The Skriptoteket public backend is the server-side grant carrier: it obtains a
HuleEdu-signed grant through the HuleEdu public grant authority and carries it
to the Sir Convert public-grant verifier when a later runtime task implements
the lane.

`X-API-Key` may remain a transport admission credential for the server-side
integration, but it is never public job ownership and never authorizes public
submit, status, result, artifact-list, or named-download access without a valid
public grant or public artifact-read lease.

### Accepted Public Grant Fields

Sir Convert must verify the exact signed HuleEdu grant payload before creating
or authorizing any public grant-owned job.

| Field | Required semantics |
| --- | --- |
| `grant_version` | Literal integer `1`. |
| `iss` | HuleEdu minting authority; initially `api_gateway_service` unless a later accepted HuleEdu task narrows it. |
| `aud` | Sir Convert public grant verifier audience; initially `sir-convert-a-lot`. |
| `source_app` | `skriptoteket`. |
| `capability` | `documents.conversion_hub.exam_converter`. |
| `route_key` | `digiexam_dxe_to_examnet_migration_bundle`. |
| `source_format` | `digiexam_dxe`. |
| `output_format` | `examnet_migration_bundle`. |
| `allowed_targets` | Non-empty subset of `examnet_pdf` and `qti_package`. |
| `upload_digest` | Digest of the exact public upload payload or canonical multipart digest used for idempotency. |
| `policy_version` | Nonblank public Exam Converter policy version. |
| `policy_profile_id` | Nonblank payload, rate, concurrency, TTL, and telemetry profile identifier. |
| `max_upload_bytes` | Maximum aggregate multipart payload accepted under the grant. |
| `allowed_mime_types` | MIME/type allowlist for the public upload parts. |
| `request_time_budget_seconds` | Maximum server processing budget represented by the policy. |
| `artifact_ttl_seconds` | Maximum retention window for public grant artifacts. |
| `artifact_read_lease_seconds` | Maximum read-lease window for manifest and named artifact downloads. |
| `rate_limit_profile_id` | Public rate-limit profile applied before minting or forwarding. |
| `concurrency_profile_id` | Public concurrency profile applied before minting or forwarding. |
| `correlation_id` | Required correlation id propagated across submit, poll, result, manifest, and download. |
| `iat` / `exp` | Issued-at and expiry timestamps accepted only within configured skew. |
| `jti` | Nonblank nonce used for replay and idempotency handling. |

The verifier must reject unknown required-behavior fields until both HuleEdu and
Sir Convert accept the new shape. Additive optional fields are allowed only
when their absence preserves the v1 behavior above.

### Public Job Ownership

Successful public submit persists an ownership envelope with:

| Field | Required semantics |
| --- | --- |
| `owner_kind` | `public_grant`. |
| `owner_digest` | Stable digest derived only from verifier-approved grant identity material, including issuer, audience, capability, route key, policy version, and `jti`. |
| `source_app` | Signed `source_app`. |
| `route_key` | Signed route key. |
| `allowed_targets_snapshot` | Signed allowed-target list captured at job creation. |
| `policy_profile_id` | Signed policy profile captured at job creation. |
| `artifact_read_lease_expires_at` | Derived from grant policy and job/artifact lifecycle. |
| `upload_digest` | Signed upload digest captured at job creation and used for duplicate-submit idempotency. |
| `correlation_id` | Signed or propagated correlation id. |

Public ownership must never be derived from IP address, browser cookies,
browser bearer tokens, unsigned form fields, `X-API-Key`, authenticated user
identity, service identity, operator identity, or product-visible metadata. A
public grant-owned job must not be upgraded into authenticated user files,
global service ownership, recoverable guest ownership, or operator ownership by
Sir Convert.

One grant `jti` can create at most one Sir Convert job. Exact duplicate submits
with the same grant `jti`, owner digest, upload digest, route, target snapshot,
policy profile, and idempotency key converge on the existing job. Mismatched
reuse of a grant `jti` or idempotency key returns a deterministic conflict
error and must not create a second job.

### Public Routes And Operations

The public grant lane uses the same downstream v2 route family, but only for
this route key and only when the public verifier succeeds.

| Operation | Authorization rule |
| --- | --- |
| `POST /v2/convert/jobs` | Requires a valid `PublicConversionGrantV1`; creates a `public_grant` owner envelope and accepts only `digiexam_dxe -> examnet_migration_bundle` job specs whose requested targets are within `allowed_targets`. |
| `GET /v2/convert/jobs/{job_id}` | Requires a valid, unexpired public grant whose verified owner digest and `jti` match the persisted public-grant job. |
| `GET /v2/convert/jobs/{job_id}/result` | Same public grant ownership rule as job status. |
| `GET /v2/convert/jobs/{job_id}/artifacts` | Requires a valid `PublicArtifactReadLeaseV1` for `bundle_manifest` bound to the persisted public-grant job. |
| `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}` | Requires a valid `PublicArtifactReadLeaseV1` for the exact artifact key bound to the persisted public-grant job. |

Public grant status and result polling fail closed when the grant is missing,
expired, malformed, untrusted, or no longer matches the persisted public owner
envelope. Public artifact reads fail closed when the artifact-read lease is
missing, expired, mismatched, replayed outside the idempotent retry policy, or
requests an unavailable artifact.

### Public Artifact-Read Lease

Public artifact listing and named downloads require a signed
`PublicArtifactReadLeaseV1`. Unspecified derived lease shapes are forbidden in
v1.

Every lease must include:

| Field | Required semantics |
| --- | --- |
| `lease_version` | Literal integer `1`. |
| `iss` | Sir Convert issuer, initially `sir-convert-a-lot`. |
| `aud` | Sir Convert public artifact-read verifier audience. |
| `parent_grant_jti` | Parent public grant `jti`. |
| `job_id` | Exact public-grant-owned job id. |
| `artifact_key` | Exact artifact key, or `bundle_manifest` for manifest/list reads. |
| `owner_digest` | Persisted owner digest derived from the parent grant. |
| `route_key` | `digiexam_dxe_to_examnet_migration_bundle`. |
| `source_app` | `skriptoteket`. |
| `allowed_targets_snapshot` | Parent grant target snapshot. |
| `policy_version` | Parent grant policy version. |
| `iat` / `exp` | Lease issued-at and expiry timestamps. |
| `jti` | Nonblank lease nonce. |
| `correlation_id` | Correlation id propagated from the parent grant/job. |

The lease TTL must not exceed the smallest of the parent grant
`artifact_read_lease_seconds`, the remaining artifact retention window, and the
Sir Convert public artifact-read maximum configured for this route. Expired or
mismatched leases return deterministic public artifact access errors without
falling back to user, service, operator, guest, or API-key ownership.

### Public Grant Rejections

Public grant failures use the standard v2 error envelope with route-specific
codes. Runtime tasks may refine names, but must preserve these conditions as
separate deterministic rejection classes:

| Condition | HTTP status | Code |
| --- | --- | --- |
| Missing public grant on public submit, status, or result | `401` | `public_grant_required` |
| Malformed, unsigned, unknown-key, or untrusted grant | `401` | `public_grant_untrusted` |
| Expired grant or future `iat` beyond accepted skew | `401` | `public_grant_expired` |
| Wrong audience | `403` | `public_grant_wrong_audience` |
| Wrong capability | `403` | `public_grant_wrong_capability` |
| Wrong route, source format, or output format | `403` | `public_grant_wrong_route` |
| Requested target outside `allowed_targets` | `403` | `public_grant_target_not_allowed` |
| Replayed or mismatched grant `jti` outside idempotency policy | `409` | `public_grant_replay_rejected` |
| Valid transport API key but no valid public grant ownership | `403` | `public_grant_ownership_required` |
| Missing artifact-read lease for public artifact list/download | `401` | `public_artifact_read_lease_required` |
| Expired, wrong-job, wrong-artifact, wrong-owner, or widened-target lease | `403` | `public_artifact_read_lease_denied` |

Direct public `convert.hule.education` product traffic outside the accepted
grant lane remains fail-closed. Public grants do not authorize arbitrary Sir
Convert routes, general file conversion, Exam.net browser automation,
authenticated artifact saving, Vault/MyFiles writes, account history, or
recoverable guest jobs.

The Task 282 privacy boundary is unchanged for public grant jobs: companion
result PDFs may enrich only correct machine-marked answers, and
product-visible outputs must not contain wrong answers, free-text student
answers, scores, identity markers, or student-performance history.

## Request Contract

### Multipart Parts

`POST /v2/convert/jobs` uses multipart form data.

| Part | Required | Content type | Rules |
| --- | --- | --- | --- |
| `file` | yes | `application/octet-stream` | Primary DigiExam `.dxe` export. This is the required structure source. |
| `job_spec` | yes | `application/json` string | Canonical v2 job spec with the route key below. |
| `graded_result_pdf` | no | `application/pdf` | Optional sanitized graded-result PDF. It may enrich correct machine-marked answers only. |
| `parity_pdf` | no | `application/pdf` | Optional blank or student-view PDF for visual parity evidence only. It is never the structure source when `.dxe` is present. |
| `digiexam_ingestion_overlay` | no | `application/json` | Optional source-bound overlay from a later Skriptoteket review request. It must be referenced by filename in `digiexam_migration_options.ingestion_overlay_filename`. |

The route does not accept v2 `resources` or `reference_docx` parts. Embedded
question assets must come from the `.dxe` IR asset contract, not a caller-supplied
resource archive.

### Job Spec

```json
{
  "api_version": "v2",
  "source": {
    "kind": "upload",
    "filename": "exam.dxe",
    "format": "digiexam_dxe"
  },
  "conversion": {
    "output_format": "examnet_migration_bundle",
    "targets": ["examnet_pdf", "qti_package"],
    "artifact_language": "sv",
    "reference_docx_filename": null
  },
  "digiexam_migration_options": {
    "graded_result_pdf_filename": "graded-result-sanitized.pdf",
    "parity_pdf_filename": "student-view.pdf",
    "result_pdf_usage": "correct_machine_marked_answers_only",
    "manual_follow_up_policy": "emit_item_addressable_report",
    "bundle_schema_version": "digiexam_migration_bundle_v3",
    "completion_mode": "source_evidence_only",
    "eligible_completion_item_types": ["choice", "multiple_response", "gap_fill"],
    "remote_provider_policy": "forbidden",
    "ingestion_overlay_filename": null,
    "ingestion_overlay_policy": "none"
  },
  "retention": {
    "pin": false
  }
}
```

Field rules:

- `source.kind` MUST be `upload`.
- `source.filename` MUST end with `.dxe`.
- `source.format` MUST be `digiexam_dxe`.
- `conversion.output_format` MUST be `examnet_migration_bundle`.
- `conversion.targets` MAY include `examnet_pdf` and `qti_package`.
- `artifact_language` defaults to `sv` for teacher-facing reports and labels.
- `digiexam_migration_options.graded_result_pdf_filename`, when present, MUST
  match the uploaded `graded_result_pdf` part filename.
- `digiexam_migration_options.parity_pdf_filename`, when present, MUST match
  the uploaded `parity_pdf` part filename.
- `result_pdf_usage` MUST be `correct_machine_marked_answers_only`.
- `manual_follow_up_policy` MUST be `emit_item_addressable_report`.
- `bundle_schema_version` MUST be `digiexam_migration_bundle_v3`.
- `completion_mode` MUST be one of `source_evidence_only`,
  `local_llm_suggest_missing_machine_marked`, or
  `local_llm_apply_missing_machine_marked_with_review`.
- `local_llm_apply_missing_machine_marked_with_review` requires a submitted
  `digiexam_ingestion_overlay` part and matching `ingestion_overlay_filename`;
  it applies reviewed data and must not call a structured provider.
- `remote_provider_policy` defaults to `forbidden`; public/grant jobs must keep
  it forbidden until a later signed grant version explicitly allows otherwise.
- `ingestion_overlay_policy` MUST be `none` when
  `ingestion_overlay_filename` is null, and MUST be `apply_teacher_overlay`
  when the overlay multipart part is present.
- `ingestion_overlay_filename`, when present, MUST match the uploaded
  `digiexam_ingestion_overlay` part filename.

The contract no longer preserves older source-only compatibility. A request
without overlay still produces the current bundle manifest and readiness
report.

### Accepted Companion Evidence

Accepted companion files are intentionally narrow:

- sanitized graded DigiExam result PDFs that expose correct machine-marked
  answers without retaining forbidden student-result data;
- blank or student-view DigiExam PDFs used only for visual parity and manual
  teacher review;
- no other companion file class is accepted by this route.

## Ingestion Overlay Contract

`digiexam_ingestion_overlay_v2` is accepted only when referenced by
`digiexam_migration_options.ingestion_overlay_filename`. It is source-bound and
uses concrete teacher edits, item point corrections, manual answer keys, or
reviewed completion answer keys. Task 337 removes accepted-current-state review
decisions from this contract: authoring corrections mutate effective exam state,
while export policy consumes effective exam state and produces artifacts.
`accept_current_state_for_export` is no longer accepted in authoring,
ingestion-overlay, correction-replay, or target-readiness unlock paths.

Current runtime note: Task 295 applies manual answer keys. Task 302 applies
supported `effective_item_patch` values to effective renderer input only. Task
306 applies reviewed completion keys only when
`completion_mode=local_llm_apply_missing_machine_marked_with_review`. Source
IR, source manifest fingerprints, and parser provenance remain unchanged.
Task 322 applies supported `point_correction` values to effective renderer
input only.

```json
{
  "schema_version": "digiexam_ingestion_overlay_v2",
  "source_binding": {
    "source_file_sha256": "sha256:source-file",
    "source_ir_schema_version": "digiexam_intermediate_exam_v3",
    "source_ir_sha256": "sha256:source-ir"
  },
  "items": [
    {
      "item_id": "item-1",
      "sequence": 1,
      "item_type": "choice",
      "source_item_fingerprint": "sha256:item-source",
      "effective_item_patch": {
        "kind": "choice",
        "alternative_overrides": [
          {"alternative_id": "A", "text": "Updated visible option"}
        ]
      },
      "manual_answer_key": {
        "kind": "choice",
        "correct_alternative_ids": [2]
      },
      "point_correction": {
        "kind": "item_points",
        "max_score": 3
      }
    }
  ]
}
```

Point corrections are bounded item-point corrections, not rubric or
partial-credit policy. The external overlay field is `point_correction`, and
the corrected value is `max_score`:

```json
{
  "item_id": "item-1",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "point_correction": {
    "kind": "item_points",
    "max_score": 3
  }
}
```

`point_correction.max_score` MUST be a positive integer. Zero, negative,
fractional, string-coerced, non-numeric, scoring-policy, rubric,
marking-matrix, and partial-credit payloads fail before target rendering. A
point correction may be submitted with `manual_answer_key` or
`reviewed_completion_answer_key` for the same item because it is orthogonal to
answer-key provenance. Accepted overlay reports list every applied field, such
as `["point_correction", "manual_answer_key"]`, so Skriptoteket projects
returned Sir Convert state instead of trusting local UI edits.

Gap-fill overlays use existing source gap IDs:

```json
{
  "item_id": "item-2",
  "sequence": 2,
  "item_type": "gap_fill",
  "source_item_fingerprint": "sha256:item-source",
  "manual_answer_key": {
    "kind": "gap_fill",
    "gap_answers": [
      {
        "gap_id": "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
        "accepted_values": ["fotosyntes"]
      }
    ]
  }
}
```

Reviewed completion overlays are separate from `manual_answer_key`:

```json
{
  "item_id": "item-1",
  "sequence": 1,
  "item_type": "single_choice",
  "source_item_fingerprint": "sha256:item-source",
  "reviewed_completion_answer_key": {
    "kind": "choice",
    "review_decision_id": "review-decision-001",
    "review_outcome": "accepted_unchanged",
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
    "answer_payload": {
      "kind": "choice",
      "correct_alternative_ids": [2]
    }
  }
}
```

For `accepted_unchanged`, `answer_payload` must digest to
`candidate_lineage.candidate_payload_digest`. For `teacher_edited`, the payload
may differ from the advisory candidate but must still validate against the
item-local ID/value contract. Candidate lineage is audit metadata; it is not
source/parser provenance and does not authorize cross-job lookup in this
slice.

Matching overlays are not part of the DigiExam-specific migration overlay
contract because this source adapter does not receive canonical matching items
from `.dxe`. That source fact must not define generic target support. Task
298/307 moves matching semantics into the source-neutral `ExamAuthoringIR v1`
slice so matching-capable source adapters can use `source_id`/`target_id`
directed pairs without accepting retired `left_id`/`right_id` aliases.

Task 323 exposes the reusable source-neutral matching manual-answer-key
producer DTO without adding a DigiExam matching overlay. Task 324's
matching-specific route is superseded by Task 330. Matching-capable source
flows now use the unified
`POST /v2/exam-authoring/corrections/apply` route with a
`manual_matching_answer_key` correction entry, source-item fingerprint binding,
effective state, and target readiness. Skriptoteket must continue treating
DigiExam `manual_answer_key` overlays as choice/gap-only.

Task 324 exists because matching had no callable neutral producer route while
choice/gap, point correction, and item patching already had reviewed
overlay/application paths. That asymmetry is historical, not the
accepted ADR-0011 product architecture. Task 327 defines the
source-neutral correction/apply contract so future teacher correction work,
including PR-0332 work, converges on one producer-owned route instead of adding
more item-specific, source-adapter, Gateway, or service routes. Task 330
hard-cuts from the Task 324 matching route and does not preserve it as an
adapter, shim, alias, wrapper, transitional route, or compatibility layer.

Task 327 publishes the unified correction/apply contract in
`docs/converters/exam-authoring-corrections-apply-contract.md`, and Task 330
adds the initial runtime/OpenAPI implementation for matching. That contract maps
`effective_item_patch`, `point_correction`, choice/gap manual keys, reviewed
completion keys, and Task 324 matching semantics into typed
source-neutral correction entries. The mapping is semantic and
implementation-directing; it does not preserve DigiExam overlay field names as
the long-term teacher-correction API.

The implementation must version affected public DigiExam artifacts for removed
legacy matching overlay fields and update Skriptoteket consumers in the same
slice.

Schema-version handling must use generated or centralized constants. Do not
copy version literals across Sir Convert runtime modules, OpenAPI tests,
Skriptoteket adapters, or browser API models. Where a consumer must branch on a
schema version, that branch must reference a contract constant or generated
type derived from the Sir Convert contract snapshot.

Gapped/open-cloze overlays likewise require exact gap accepted-value fields
before applied completion can treat them as automatically evaluated.

Accepted-current-state is not an answer key and not durable exam state. Task 337
removes `review_decision.kind == "accept_current_state_for_export"` from
authoring/correction contracts. Missing answer keys remain missing until a real
authoring correction supplies key state.

Source-derived item context is not an overlay field. It is the parser/provider
input context already present in source IR: exam title/metadata, item title,
prompt/body HTML, alternatives, gaps, grading policy, and asset references. It
is not answer-key evidence.

## Effective Exam And Report Contracts

`effective_ir_json` uses `digiexam_effective_exam_v2` whenever source IR is not
the exact renderer input.

```json
{
  "schema_version": "digiexam_effective_exam_v2",
  "source_file_sha256": "sha256:source-file",
  "source_ir_schema_version": "digiexam_intermediate_exam_v3",
  "source_ir_sha256": "sha256:source-ir",
  "ingestion_overlay_sha256": "sha256:overlay",
  "answer_key_completion_report_sha256": null,
  "items": [
    {
      "item_id": "item-1",
      "sequence": 1,
      "item_type": "choice",
      "source_item_fingerprint": "sha256:item-source",
      "effective_answer_key": {
        "provenance": "teacher_provided",
        "correct_alternative_ids": [2],
        "correct_gap_answers": [],
        "lineage": null
      },
      "effective_point_correction": {
        "kind": "item_points",
        "source_max_score": 2,
        "effective_max_score": 3,
        "source_item_fingerprint": "sha256:item-source"
      },
      "applied_overlay_entry_ids": ["item-1"],
      }
  ]
}
```

Reviewed completion keys use effective provenance, not parser provenance:

```json
{
  "provenance": "reviewed",
  "correct_alternative_ids": [2],
  "correct_gap_answers": [],
  "lineage": {
    "completion_report_sha256": "sha256:completion-report",
    "candidate_id": "candidate-item-001",
    "candidate_payload_digest": "sha256:candidate-payload",
    "provider_profile_id": "local-structured",
    "schema_name": "digiexam_choice_answer_key_decision_v1",
    "schema_version": "digiexam_choice_answer_key_decision_v1",
    "prompt_template_version": "digiexam_choice_answer_key_prompt_v1",
    "validation_state": "valid",
    "review_decision_id": "review-decision-001",
    "review_outcome": "accepted_unchanged"
  }
}
```

Teacher-edited reviewed candidates use `provenance: "teacher_provided"` with
the same bounded lineage. Plain `manual_answer_key` overlays use
`provenance: "teacher_provided"` with `lineage: null`.

`ingestion_overlay_report_v1` records validation/application outcomes without
exposing raw overlay JSON:

```json
{
  "schema_version": "ingestion_overlay_report_v1",
  "overlay_sha256": "sha256:overlay",
  "source_ir_sha256": "sha256:source-ir",
  "accepted_entries": [
    {
      "item_id": "item-1",
      "sequence": 1,
      "applied_fields": ["manual_answer_key"]
    }
  ],
  "rejected_entries": []
}
```

Accepted overlay report `applied_fields` may include `effective_item_patch`
only when a supported visible-content patch changed effective renderer input.
It includes `point_correction` when a bounded positive integer point correction
is applied. Rejected patch fields remain item-addressable in
`rejected_entries`; manual answer keys, reviewed advisory acceptance/edit
intents, and teacher corrections continue through their bounded apply paths.

`answer_key_completion_report_v1` records structured provider advisory
candidates, admission-time provider lineage, and backend validation states,
never raw prompts, raw provider responses, source/parser provenance claims,
student data, owner metadata, raw `.dxe`, result-PDF content, raw request
payloads, API keys, or artifact paths. Candidate digests are computed from the
canonical backend-validated candidate payload only, not raw provider responses,
raw prompts, or pre-validation payloads:

When provider execution fails before a validated candidate exists, report items
may include a redacted `provider_error_diagnostic` object. The diagnostic is
operator evidence only: it may contain `status_code`, OpenAI `x-request-id`
when supplied, provider `error.type`, `error.code`, `error.param`, and
`message_sha256` for a short sanitized provider message. It must not contain
prompt text, item text, raw images or data URLs, raw request payloads, raw
provider response bodies, API keys, owner metadata, student data, or artifact
paths.

```json
{
  "schema_version": "answer_key_completion_report_v1",
  "job_id": "job-1",
  "completion_mode": "local_llm_suggest_missing_machine_marked",
  "provider_lineage": {
    "provider_family": "local_structured_llm",
    "provider_profile_id": "local-structured",
    "model": "ibm-granite/granite-4.1-8b-fp8",
    "endpoint_kind": "chat_completions",
    "output_mode": "json_schema",
    "reasoning_effort": null,
    "text_verbosity": null,
    "settings_version": 1,
    "route_class": "operator_default",
    "route_decision": "active_provider_profile",
    "remote_provider_authorized": false
  },
  "items": [
    {
      "item_id": "item-1",
      "sequence": 1,
      "item_type": "single_choice",
      "decision_state": "suggested",
      "validation_state": "valid",
      "candidate_id": "item-1:5d41402abc4b2a76",
      "candidate_payload_digest": "sha256:5d41402abc4b2a76b9719d911017c5920f3a8c7e0b921b4d55ab11cd22ef3344",
      "answer_payload": {
        "kind": "choice",
        "correct_alternative_ids": [2]
      },
      "provider_profile_id": "local-structured",
      "model_profile": "ibm-granite/granite-4.1-8b-fp8",
      "schema_name": "digiexam_choice_answer_key_decision_v1",
      "schema_version": "digiexam_choice_answer_key_decision_v1",
      "prompt_template_version": "digiexam_choice_answer_key_prompt_v1",
      "backend_status": "success",
      "backend_failure_code": null,
      "provider_error_diagnostic": null
    }
  ]
}
```

Failed provider rows use the same bounded shape without candidate payloads:

```json
{
  "item_id": "item-013",
  "sequence": 13,
  "item_type": "gap_fill",
  "decision_state": "manual_follow_up_required",
  "validation_state": "manual_follow_up_required",
  "candidate_id": null,
  "candidate_payload_digest": null,
  "answer_payload": null,
  "provider_profile_id": "openai-gpt-5.4-mini-2026-03-17",
  "model_profile": "gpt-5.4-mini-2026-03-17",
  "schema_name": "digiexam_gap_fill_answer_key_decision_v1",
  "schema_version": "digiexam_gap_fill_answer_key_decision_v1",
  "prompt_template_version": "digiexam_gap_fill_answer_key_prompt_v1",
  "backend_status": "manual_follow_up_required",
  "backend_failure_code": "provider_http_error",
  "provider_error_diagnostic": {
    "status_code": 400,
    "request_id": "req_redacted_example",
    "error_type": "invalid_request_error",
    "error_code": "invalid_schema",
    "error_param": "text.format.schema",
    "message_sha256": "sha256:5d41402abc4b2a76b9719d911017c5920f3a8c7e0b921b4d55ab11cd22ef3344"
  }
}
```

`answer_key_completion_report_v1` is also published as
`DigiExamAnswerKeyCompletionReportV1` in the generated v2 OpenAPI contract so
Skriptoteket can generate consumer types from the same versioned shape.

Rejected companion classes include:

- unsanitized result PDFs containing identity markers, earned scores, wrong
  selections, free-text student answers, or performance history;
- class result exports, CSV/XLSX gradebooks, screenshots, arbitrary images, or
  generic archives;
- additional `.dxe` files in companion parts;
- PDFs that cannot be classified as the declared `graded_result_pdf` or
  `parity_pdf` role.

Unsafe or unrecognized companion evidence fails closed before conversion. The
service must not silently strip and continue from a submitted unsafe result PDF
because that would make privacy behavior depend on best-effort parsing.

### Payload Limits

Route implementations must publish configured limits in OpenAPI and enforce
them before parsing:

- `.dxe` upload: maximum 50 MiB
- `graded_result_pdf`: maximum 100 MiB
- `parity_pdf`: maximum 100 MiB
- aggregate multipart payload: maximum 200 MiB

Deployments may choose lower limits. A payload rejected by size returns `413`
with a typed route error.

## Idempotency And Correlation

Skriptoteket adapters must use deterministic idempotency keys under the
`internal_adapter_contract_v2.md` policy. The fingerprint for this route is the
normalized job spec plus SHA-256 digests of:

- the `.dxe` upload;
- `graded_result_pdf`, when present;
- `parity_pdf`, when present.
- `digiexam_ingestion_overlay`, when present.

The same owner, route, key, job spec, and upload digests return the original
`job_id` with `X-Idempotent-Replay: true`. Reusing the same key with different
payloads returns `409` with
`idempotency_key_reused_with_different_payload`.

`X-Correlation-ID` should be generated by Skriptoteket at the teacher action
boundary and preserved unchanged across submit, poll, result, artifact listing,
artifact download, and save-to-user-files events.

## Terminal Result Contract

`GET /v2/convert/jobs/{job_id}/result` returns normal v2 result semantics with
route-specific conversion metadata.

```json
{
  "api_version": "v2",
  "job": {
    "job_id": "job_123",
    "status": "succeeded"
  },
  "result": {
    "artifact": {
      "filename": "artifact-bundle.json",
      "content_type": "application/json",
      "sha256": "sha256:...",
      "size_bytes": 3281
    },
    "conversion_metadata": {
      "route_key": "digiexam_dxe_to_examnet_migration_bundle",
      "bundle_schema_version": "digiexam_migration_bundle_v3",
      "bundle_status": "partial",
      "source_sha256": "sha256:...",
      "target_readiness_report_artifact_key": "target_readiness_report",
      "manual_follow_up_required": true,
      "warning_count": 3,
      "artifact_count": 13
    }
  }
}
```

`bundle_status` values:

- `complete`: all requested implemented targets are available and no manual
  follow-up is required.
- `partial`: at least one requested or default target is not available, but the
  bundle contains usable target artifacts or teacher-facing reports.
- `needs_review`: Sir Convert produced item-addressable reports, but no
  requested target is exportable until a teacher supplies an overlay or review
  decision.
- `failed`: Sir Convert attempted a target and retained diagnostics, but target
  validation or artifact materialization failed.

Source validation failures and unsafe companion evidence do not produce a
terminal bundle. They use the standard v2 error envelope.

`conversion_metadata.artifact_count` is the count of entries in the persisted
bundle manifest, including the `bundle_manifest` self-entry.
`conversion_metadata.warning_count` is copied from the persisted manifest
`warnings.count` value.

## Compact Answer-Key Review State

Task 373 adds `digiexam_answer_key_review_state_v1` as the compact,
item-addressable answer-key review projection for DigiExam migration consumers.
It is emitted as the named artifact `answer_key_review_state_report` for
terminal first-pass bundle jobs.

The projection is review-state only. `target_readiness_report_v1` remains the
only authority for enabling PDF or QTI export actions. Consumers must not use
`review_state`, `current_key_origin`, reasons, or replay references from this
projection to unlock downloads without matching target-readiness rows.

Strict review state values are:

- `review_required`
- `review_complete`
- `teacher_modified`
- `validation_required`

Strict current-key origin values are:

- `none`
- `source_provided`
- `reviewed_advisory`
- `teacher_authored`
- `teacher_edited_advisory`
- `mixed`

Strict reason values are:

- `source_answer_key_present`
- `advisory_candidate_pending`
- `reviewed_advisory_accepted`
- `teacher_answer_key_present`
- `teacher_edited_advisory_candidate`
- `answer_key_not_applicable`
- `manual_answer_key_required`
- `no_correct_choice_selected`
- `required_gap_accepted_values_missing`
- `unsupported_item_type`
- `unsupported_target_shape`
- `target_validation_failed`
- `provider_unavailable`
- `correction_rejected`
- `stale_source_state`
- `replay_artifact_unavailable`
- `matching_source_state_unavailable`

Rows expose item binding, supported interaction IDs, choice IDs, gap IDs,
correction affordances, reasons, `message_key`, optional bounded
`provenance_detail`, and replay-scoped artifact references only when Sir
Convert produced corrected replay target artifacts. The projection must not
contain generic `history`, `review_decision`,
`accept_current_state_for_export`, source-state signatures, identity/grant data,
private paths, raw source/provider/student data, provider diagnostics, or public
advisory `provenance_detail` unless a later governed public grant explicitly
allows it.

The first-pass DigiExam bundle also persists the bounded advisory candidate
context inside the signed correction source-state sidecar as
`advisory_answer_key_candidates`. Correction apply/replay consumes that
producer-owned context so accepting one advisory candidate does not erase
untouched valid sibling candidates from the compact projection. Accepted
advisory corrections project as `review_complete` with
`current_key_origin = reviewed_advisory` and
`reasons = [reviewed_advisory_accepted]`; untouched valid advisory siblings
remain `review_required` with `current_key_origin = none` and
`reasons = [advisory_candidate_pending]`; keyed siblings with no valid advisory
remain validation rows. Free-text/open-writing rows that are outside keyed
answer-key review project as `review_complete` with
`current_key_origin = none` and `reasons = [answer_key_not_applicable]` even if
bad source-state context contains an advisory candidate row for them. This
context is limited to item binding, candidate digest, provider/profile/schema
identifiers, prompt-template version, and validation state. It must not include
raw provider prompts or responses, source files, private paths,
identity/session data, credentials, browser-local state, or student data.

## Artifact Bundle Contract

The named artifact bundle is the product contract between Sir Convert and
Skriptoteket. Skriptoteket must use bundle metadata and named artifact download
routes. It must not inspect Sir Convert work directories.

### Bundle Manifest

The canonical bundle manifest schema version is
`digiexam_migration_bundle_v3`.

```json
{
  "schema_version": "digiexam_migration_bundle_v3",
  "job_id": "job_123",
  "source": {
    "filename": "exam.dxe",
    "sha256": "sha256:...",
    "format": "digiexam_dxe"
  },
  "bundle_status": "partial",
  "retention": {
    "pin": false,
    "expires_at": "2026-05-18T12:00:00Z"
  },
  "artifacts": [
    {
      "artifact_key": "examnet_pdf",
      "filename": "exam.pdf",
      "content_type": "application/pdf",
      "availability": "available",
      "size_bytes": 48192,
      "sha256": "sha256:...",
      "download_path": "/v2/convert/jobs/job_123/artifacts/examnet_pdf"
    },
    {
      "artifact_key": "qti_package",
      "filename": "exam.zip",
      "content_type": "application/zip",
      "availability": "available",
      "size_bytes": 8124,
      "sha256": "sha256:...",
      "download_path": "/v2/convert/jobs/job_123/artifacts/qti_package"
    },
    {
      "artifact_key": "qti_validation_report",
      "filename": "exam-qti-validation-report.json",
      "content_type": "application/json",
      "availability": "available",
      "size_bytes": 2048,
      "sha256": "sha256:...",
      "download_path": "/v2/convert/jobs/job_123/artifacts/qti_validation_report"
    }
  ],
  "manual_follow_up": {
    "required": true,
    "artifact_key": "manual_follow_up_report",
    "count": 2
  },
  "readiness": {
    "artifact_key": "target_readiness_report",
    "exportable_targets": ["examnet_pdf"],
    "review_required": true
  },
  "answer_key_review_state": {
    "artifact_key": "answer_key_review_state_report"
  },
  "source_binding": {
    "source_ir_schema_version": "digiexam_intermediate_exam_v3",
    "source_ir_sha256": "sha256:...",
    "effective_exam_schema_version": "digiexam_effective_exam_v2",
    "effective_exam_sha256": "sha256:..."
  },
  "warnings": {
    "artifact_key": "warnings_report",
    "count": 3
  }
}
```

Every artifact entry MUST include:

- `artifact_key`
- deterministic public `filename` from the artifact-key definition
- `content_type`
- `availability`
- `size_bytes` when available
- `sha256` when available, formatted `sha256:<hex>`
- `download_path` when available
- `unavailable_code` when unavailable, failed, or not implemented

`availability` values:

- `available`
- `unavailable`
- `failed`
- `not_requested`
- `not_implemented`
- `not_supported_by_examnet`

`not_requested` is the required availability for target-specific artifacts
whose generator was intentionally skipped because the caller provided a
selective `conversion.targets` list. For example, a request with only
`"examnet_pdf"` must emit `qti_package` and `qti_validation_report` entries as
`not_requested`, and named downloads for those entries must return a typed
unavailable-artifact error.

### Required Bundle Entries

| Artifact key | Public filename pattern | Content type | Availability rules |
| --- | --- | --- | --- |
| `bundle_manifest` | `<source-stem>-artifact-bundle.json` | `application/json` | Always available for terminal bundles. |
| `examnet_pdf` | `<source-stem>.pdf` | `application/pdf` | Available when the Exam.net PDF renderer carries all required content and assets. Blocked when target shape is unsupported. |
| `qti_package` | `<source-stem>.zip` | `application/zip` | Available when the Task 280 QTI package generator passes the governed local profile. Blocked when local validation fails, when adapter mapping cannot represent all source items, or when required accepted values are missing. Live Exam.net import proof state is reported separately. |
| `qti_validation_report` | `<source-stem>-qti-validation-report.json` | `application/json` | Present when QTI generation is requested or defaulted. Task 280 defines `examnet_qti_validation_report_v1`; Task 282 service bundles expose this report as a named artifact. |
| `ir_json` | `<source-stem>-digiexam-ir.json` | `application/json` | Available when `.dxe` parsing reaches IR generation. May include teacher-owned embedded asset payloads required by renderers. |
| `effective_ir_json` | `<source-stem>-digiexam-effective-exam.json` | `application/json` | Available when LLM completion, manual overlay, item patch, teacher correction, or reviewed advisory acceptance/edit intent changes renderer input. Uses `digiexam_effective_exam_v2`, not the parser-owned source IR schema. |
| `migration_manifest` | `<source-stem>-migration-manifest.json` | `application/json` | Available when IR manifest generation succeeds. Must not embed raw asset payloads or result-PDF private data. |
| `target_readiness_report` | `<source-stem>-target-readiness-report.json` | `application/json` | Always available for terminal v2 bundles. It is the consumer authority for enabling PDF/QTI export actions. |
| `answer_key_review_state_report` | `<source-stem>-answer-key-review-state-report.json` | `application/json` | Always available for terminal v2 bundles. It is the compact item review-state projection for DigiExam answer keys and must not replace target readiness. |
| `ingestion_overlay_report` | `<source-stem>-ingestion-overlay-report.json` | `application/json` | Available when an overlay is submitted. Summarizes accepted/rejected overlay entries without exposing raw overlay JSON. |
| `answer_key_completion_report` | `<source-stem>-answer-key-completion-report.json` | `application/json` | Available for advisory `local_llm_suggest_missing_machine_marked`. Not requested for reviewed apply mode in this slice; reviewed apply consumes submitted bounded lineage and must not call the provider. |
| `manual_follow_up_report` | `<source-stem>-manual-follow-up.md` | `text/markdown; charset=utf-8` | Always available for terminal bundles. Empty or review-only when no action is required. |
| `warnings_report` | `<source-stem>-warnings.json` | `application/json` | Always available for terminal bundles. Empty list when there are no warnings. |
| `asset_summary` | `<source-stem>-asset-summary.json` | `application/json` | Always available for terminal bundles. Must contain hashes and metadata only, not raw base64 payloads. |

Public filenames preserve the uploaded source filename stem so Skriptoteket and
other callers can present downloadable artifacts with the teacher's original
source name. Internal storage filenames remain fixed per artifact key for
deterministic service operation. The QTI ZIP public filename is also recorded
in `qti_validation_report.package_filename`; QTI package files such as
`imsmanifest.xml` and `items/*.xml` remain at archive root to preserve the
governed local QTI package profile.

### Idempotent Replay Compatibility

Same-key, same-fingerprint `succeeded` replay for this route is strict only
when the persisted terminal bundle satisfies the current artifact contract.
Service API v2 registers the `digiexam_migration_bundle_v3` terminal artifact
compatibility contract beside the route policy for
`digiexam_dxe -> examnet_migration_bundle`.

A persisted DigiExam success is compatible when all of the following are true:

- the bundle manifest is valid `digiexam_migration_bundle_v3` and its `job_id`
  matches the persisted job;
- every current required artifact key is present exactly once;
- `readiness.artifact_key` is `target_readiness_report`;
- `answer_key_review_state.artifact_key` is
  `answer_key_review_state_report`;
- source and effective schema versions are current:
  `digiexam_intermediate_exam_v3` and `digiexam_effective_exam_v2`;
- `target_readiness_report` parses as `target_readiness_report_v1` for the
  same job;
- `answer_key_review_state_report` parses as
  `digiexam_answer_key_review_state_v1`;
- every non-manifest `available` artifact entry has existing bytes whose size
  and `sha256:<hex>` digest match the manifest entry.

The `bundle_manifest` self-entry may remain size/hash exempt. `complete`,
`partial`, `needs_review`, schema-valid `failed`, and manual-follow-up states
remain compatible terminal workflow states when the required reports, pointers,
schema versions, and available bytes are valid. Strict replay does not require
all PDF/QTI target artifacts to be exportable; `target_readiness_report_v1`
remains the export authority.

When a same-key, same-fingerprint succeeded job is incompatible and the fresh
request can be safely admitted, the service admits a fresh attempt and returns
`idempotency.state = service_reattempt` with
`idempotency.reason = terminal_artifact_contract_incompatible`. The stale job
remains in `idempotency.previous_attempts`; no synthetic failed job is created,
and no production idempotency or artifact file is edited as remediation.

### Named Artifact Endpoints

Task 282, the service runtime task that implements this contract, must add named
artifact reads:

- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`

`GET /artifacts` returns the bundle manifest JSON. `GET /artifacts/{artifact_key}`
returns the artifact bytes using the entry content type. Missing, unavailable, or
not-implemented artifacts return deterministic route errors rather than empty
files.

Consumers for this route MUST use the named artifact endpoints. Do not add a
bundle-v1 singular `/artifact` compatibility surface for this route.

## Privacy Contract

The `.dxe` file is the required structure source. Sanitized graded-result PDFs
are optional correct-answer evidence only.

Sir Convert MUST NOT retain any of the following from graded result PDFs in API
responses, logs, manifests, IR, reports, or bundle artifacts:

- wrong student answers;
- free-text student answers;
- earned score labels or values;
- student names, email addresses, usernames, class identifiers, or other
  identity markers;
- per-student performance history.

Correct machine-marked answer evidence may be retained only when it can be
bound to source `.dxe` items and represented through the IR answer-key
provenance contract.

Private work directories and raw uploaded companion files are not API
artifacts. They remain internal retention-managed job material.

## Manual Follow-Up Semantics

Manual follow-up is first-class and item-addressable. The report and JSON
warnings must allow Skriptoteket to show teachers what needs attention without
re-implementing conversion logic.

Initial manual follow-up reasons:

- `manual_answer_key_required`
- `manual_marking_required`
- `unsupported_item_type`
- `unsupported_target_shape`
- `single_choice_import_validation_required`
- `parser_warning_blocks_rendering`
- `qti_validation_failed`
- `unsupported_examnet_qti_resource`

Manual follow-up entries include:

- `item_id`
- 1-based `sequence`
- `title`
- `item_type`
- `reason_code`
- teacher-facing Swedish message
- source evidence summary
- affected target keys

Example:

```json
{
  "item_id": "item_0004",
  "sequence": 4,
  "title": "Para ihop",
  "item_type": "unknown",
  "reason_code": "unsupported_target_shape",
  "message": "Kontrollera itemformen manuellt innan export.",
  "affected_targets": ["examnet_pdf", "qti_package"]
}
```

## Error And Blocker Codes

Request and authorization failures use the standard v2 error envelope.

| Condition | HTTP status | Code | Notes |
| --- | --- | --- | --- |
| Missing `.dxe` structure source | `422` | `digiexam_structure_source_required` | The route never falls back to PDF as structure source. |
| Invalid or unreadable `.dxe` | `422` | `digiexam_source_invalid` | Covers corrupt zip/JSON, missing required DigiExam question structure, or unsupported container shape. |
| Unsupported companion file | `422` | `digiexam_companion_unsupported` | Companion role or content type is outside this contract. |
| Unsafe result-PDF evidence | `422` | `digiexam_result_pdf_unsafe_evidence` | Detected forbidden student-result data or failed sanitization proof. |
| Payload too large | `413` | `digiexam_payload_too_large` | Details include the rejected part and configured byte limit. |
| Unauthorized job read | `403` | `job_access_denied` | Valid transport credential but wrong owner or missing grant. |
| Unauthorized artifact read | `403` | `artifact_access_denied` | Same owner/grant rule as the parent job artifact route. |
| Missing named artifact after available manifest entry | `500` | `digiexam_target_artifact_missing` | Service integrity failure; do not synthesize an empty file. |
| Unavailable QTI target download | `409` | `qti_validation_failed` | Named QTI package download is unavailable because validation did not pass; the validation report remains downloadable. |

Terminal bundle unavailable reasons are machine-readable inside artifact
entries, target readiness reports, and manual-follow-up reports:

| Reason code | Target | Meaning |
| --- | --- | --- |
| `source_ir_unavailable` | all | IR parse status prevents target rendering. |
| `manual_answer_key_required` | `examnet_pdf`, `qti_package` | Source evidence lacks a machine-marked answer key. |
| `unsupported_target_shape` | `examnet_pdf`, `qti_package` | IR item is valid but no governed target shape exists. For gap/open-cloze this is a target capability/degradation state, not a reason to erase source intent. |
| `embedded_asset_unavailable` | `examnet_pdf`, `qti_package` | Referenced asset cannot be carried safely. |
| `qti_validation_failed` | `qti_package` | QTI generation ran but did not pass the governed validation profile. |
| `not_supported_by_examnet` | `qti_package` | Source content maps to QTI but falls outside the governed Exam.net QTI support profile. |
| `unsupported_examnet_qti_resource` | `qti_package` | Source resource class, such as audio, PDF attachment, or tool resource, must be added manually after import. |

## Target Readiness Report

`target_readiness_report_v1` is the consumer authority for enabling target
actions. Skriptoteket must not derive export availability from `bundle_status`,
artifact `availability`, manual-follow-up counts, or a local UI state flag.

Each row MUST include:

- `target`: `examnet_pdf` or `qti_package`;
- `item_id` and `sequence` when the readiness is item-specific;
- `source_item_fingerprint` when the row can be bound to a source item;
- `readiness`: one of the classes below;
- `export_enabled`: boolean;
- `artifact_key` when a downloadable artifact exists;
- `reason_code`;
- `teacher_action`;
- `retryable`;
- `message_key` for localized consumer copy.

Readiness classes:

| Readiness | Export enabled | Meaning |
| --- | --- | --- |
| `ready` | yes | Target bytes were created and validated from source or effective evidence. |
| `needs_teacher_answer_key` | no | A machine-marked item lacks an answer key and needs a manual answer-key overlay. |
| `unsupported_target_shape` | no | Source/effective item shape has no governed PDF/QTI target representation. |
| `target_validation_failed` | no | Target generation ran but failed validation, such as QTI package validation. |
| `provider_unavailable` | no | Requested local provider completion could not run and remote fallback is forbidden or unavailable. |
| `not_requested` | no | The target was intentionally skipped by `conversion.targets`. |
| `not_implemented` | no | The target is outside the implemented route surface. |

Example:

```json
{
  "schema_version": "target_readiness_report_v1",
  "job_id": "job_123",
  "source_ir_sha256": "sha256:source-ir",
  "effective_exam_sha256": "sha256:effective",
  "targets": [
    {
      "target": "examnet_pdf",
      "readiness": "ready",
      "export_enabled": true,
      "artifact_key": "examnet_pdf",
      "reason_code": "target_available",
      "teacher_action": "none",
      "retryable": false,
      "message_key": "exam_converter.target.ready"
    },
    {
      "target": "qti_package",
      "item_id": "item-3",
      "sequence": 3,
      "source_item_fingerprint": "sha256:item-source",
      "readiness": "unsupported_target_shape",
      "export_enabled": false,
      "artifact_key": null,
      "reason_code": "matching_pairs_missing",
      "teacher_action": "manual_target_creation_required",
      "retryable": false,
      "message_key": "exam_converter.target.unsupported_matching_shape"
    }
  ]
}
```

Matching readiness rows are owned by matching-capable source flows that consume
`ExamAuthoringIR v1`; DigiExam `.dxe` migration must not invent keyed matching
rows from a source dialect that does not carry them. Matching readiness rows
must distinguish at least:

- `matching_pairs_missing`: the IR/effective item has matching structure but no
  trusted directed pairs.
- `matching_pair_ids_invalid`: a submitted or reviewed pair references an
  unknown source/left or target/right ID.
- `matching_association_limits_exceeded`: the directed pair set violates the
  item's intermediary `match_min`/`match_max` or association count limits.
- `examnet_qti_import_unproven`: a package may be general-QTI valid, but live
  Exam.net QTI import readiness cannot be claimed until Exam.net exposes an
  import test path.

Skriptoteket must display these as Sir Convert-owned readiness states. It must
not infer exportability from duplicate right IDs, unmatched right IDs, or local
pair counts. Repeated source or target associations are supported when the
source-neutral matching interaction bounds allow them.

Gap/open-cloze readiness rows consume the Task 305
`ExamAuthoringGapOpenClozeInteraction` semantics. Missing accepted values on
required gaps mean the item is structurally valid but not automatically
evaluable. When accepted values exist, target proof gaps must not remove them
from the generated artifacts. Exam.net PDF must not relabel gap/open-cloze as
`Fritext` in the current profile; accepted values must be included under the
gap/open-cloze target shape. Exam.net QTI may remain live-import proof-gated,
but the package must still carry the keyed text-entry responses when local QTI
generation succeeds.

Unsupported native target export, such as unproven native multi-gap Exam.net
PDF import, is reported as a native-target limitation only for the native target
claim. Missing-key targets remain blocked until real authoring corrections
provide keys unless a future export-only request contract reintroduces
incomplete export. Export-only policy must not be encoded as source IR,
effective IR, ingestion overlay, or correction replay state.

When effective renderer input changes a source-fingerprint field, such as a
Task 322 `point_correction.max_score`, `target_readiness_report_v1` rows remain
bound to the original source item fingerprint. The corrected point value affects
target bytes and effective report state, not source identity.

Tasks 303 and 308 documented the now-removed accepted-current-state QTI/PDF
paths. Task 337 supersedes those paths for authoring/correction replay:
reviewed/source/teacher keys are artifact data, while missing-key export remains
blocked until a real key correction is supplied.

When an item has multiple material blockers, such as missing accepted values
and a multi-gap `Lucktext` shape without a promoted native Exam.net PDF target,
Sir Convert must not let artifact-level first-warning selection hide the
item-specific native target limitation. The artifact entry may expose one
`unavailable_code`, but `target_readiness_report_v1` must preserve actionable
item reasons so Skriptoteket does not display a generic missing-key blocker for
item-013-style cases. Missing-key PDF/QTI export remains blocked until real
reviewed/source/teacher key corrections are supplied; any future incomplete or
best-effort export must enter through a governed export-only request policy,
not through source IR, effective IR, ingestion overlays, correction replay, or
target-readiness unlocks.

## Skriptoteket Adapter Contract

Skriptoteket remains a thin consumer. Its adapter may:

- build the canonical job spec;
- attach the `.dxe` and optional companion files;
- generate deterministic idempotency and correlation headers;
- preserve Gateway/InternalIdentityContextV1 headers for user-originated work;
- poll status and result endpoints;
- list bundle artifacts;
- download named artifacts;
- save downloaded artifacts and metadata into authenticated user files.

The adapter must not:

- parse `.dxe` or result PDFs;
- infer answer keys;
- rewrite target-shape warnings;
- infer matching target support from pair counts, duplicate IDs, repeated
  associations, or unmatched right-side options;
- inspect Sir Convert job directories;
- choose private artifact paths;
- hide target readiness, validation-failed, or manual-follow-up states from
  teachers;
- convert user-originated work into global service-owned jobs.

Skriptoteket may store locally:

- source and effective bundle schema versions;
- job id, correlation id, route key, source SHA-256, and target list;
- manifest item summaries, including `item_id`, `sequence`, `item_type`, and
  `source_item_fingerprint`;
- artifact metadata and target readiness rows;
- teacher edits, manual answer keys, reviewed advisory acceptance/edit intents,
  and correction-session drafts in the UI.

Skriptoteket must echo unchanged when submitting overlays:

- source file SHA-256;
- source IR schema version and digest;
- item id, sequence, item type, and source item fingerprint;
- artifact/job correlation identifiers required by the route.

Skriptoteket must refresh from Sir Convert before enabling export/save:

- target readiness rows;
- artifact availability and download paths;
- target validation state;
- effective exam digest after overlay or completion.

When Task 298/307 removes DigiExam-owned matching fields, Skriptoteket must
regenerate from the Sir Convert OpenAPI snapshot and replace hard-coded schema
strings with generated or centralized contract constants in projection models,
save metadata, and UI/API tests in the same schema-bump slice. DigiExam review
state must not draft matching pairs, and target export/save buttons remain
bound to refreshed `target_readiness_report_v1` rows from Sir Convert. No
Skriptoteket adapter may submit or accept retired `left_id`/`right_id` matching
pair payloads after the cutover.

When Skriptoteket saves an artifact into user files, it should persist at
least:

- Sir Convert `job_id`;
- `artifact_key`;
- deterministic source `filename`;
- saved display filename;
- `content_type`;
- `size_bytes`;
- `sha256`;
- `bundle_schema_version`;
- `correlation_id`;
- save timestamp.

Skriptoteket owns the saved copy after download. Sir Convert remains the
authority for the original job and artifact bundle until its retention window
expires.

## API Examples

### Submit

```bash
curl -sS -X POST "${SIR_BASE_URL}/v2/convert/jobs?wait_seconds=0" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "Idempotency-Key: idem_skriptoteket_digiexam_001" \
  -H "X-Correlation-ID: corr_skriptoteket_digiexam_001" \
  -H "X-HuleEdu-Identity-Context-Version: 1" \
  -H "X-HuleEdu-Identity-Context: ${SIGNED_CONTEXT}" \
  -H "X-HuleEdu-Identity-Key-Id: ${KEY_ID}" \
  -H "X-HuleEdu-Identity-Signature: ${SIGNATURE}" \
  -F 'file=@./exam.dxe;type=application/octet-stream' \
  -F 'graded_result_pdf=@./graded-result-sanitized.pdf;type=application/pdf' \
  -F 'job_spec={
    "api_version":"v2",
    "source":{"kind":"upload","filename":"exam.dxe","format":"digiexam_dxe"},
    "conversion":{
      "output_format":"examnet_migration_bundle",
      "targets":["examnet_pdf","qti_package"],
      "artifact_language":"sv",
      "reference_docx_filename":null
    },
    "digiexam_migration_options":{
      "graded_result_pdf_filename":"graded-result-sanitized.pdf",
      "result_pdf_usage":"correct_machine_marked_answers_only",
      "manual_follow_up_policy":"emit_item_addressable_report"
    },
    "retention":{"pin":false}
  }'
```

### Poll

```bash
curl -sS "${SIR_BASE_URL}/v2/convert/jobs/job_123" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_skriptoteket_digiexam_001"
```

### Read Result And List Artifacts

```bash
curl -sS "${SIR_BASE_URL}/v2/convert/jobs/job_123/result" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_skriptoteket_digiexam_001"
```

```bash
curl -sS "${SIR_BASE_URL}/v2/convert/jobs/job_123/artifacts" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_skriptoteket_digiexam_001"
```

### Download Or Save A Named Artifact

```bash
curl -sS "${SIR_BASE_URL}/v2/convert/jobs/job_123/artifacts/examnet_pdf" \
  -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
  -H "X-Correlation-ID: corr_skriptoteket_digiexam_001" \
  -o exam.pdf
```

Skriptoteket save-to-user-files is a consumer-owned action using the downloaded
bytes plus the bundle metadata. The adapter must preserve the artifact key,
content type, size, SHA-256, source `job_id`, and correlation id in the saved
file metadata.

### Needs-Review Outcome

```json
{
  "schema_version": "digiexam_migration_bundle_v3",
  "job_id": "job_456",
  "bundle_status": "needs_review",
  "artifacts": [
    {
      "artifact_key": "examnet_pdf",
      "filename": "exam.pdf",
      "content_type": "application/pdf",
      "availability": "unavailable",
      "unavailable_code": "unsupported_target_shape",
      "size_bytes": null,
      "sha256": null
    },
    {
      "artifact_key": "manual_follow_up_report",
      "filename": "manual-follow-up.md",
      "content_type": "text/markdown; charset=utf-8",
      "availability": "available",
      "size_bytes": 2143,
      "sha256": "sha256:..."
    }
  ]
}
```

Skriptoteket should present this as a completed conversion requiring teacher
action, not as a transport failure.

## Conformance Requirements For Later Tasks

Task 282, the service runtime task that implements this contract, must add tests
for:

- request validation for required `.dxe`, optional sanitized result PDF,
  optional parity PDF, unsupported companions, and payload-size limits;
- idempotency replay across `.dxe` and companion-file digests;
- owner-scoped job, result, artifact-list, and named artifact reads;
- terminal bundle manifest entries with deterministic public filenames, content
  types, sizes, hashes, retention, and availability states;
- absence of forbidden result-PDF data from API responses, logs intended for
  product consumption, IR, manifests, and reports;
- unavailable target shapes producing diagnostics without publishing malformed
  target artifacts;
- QTI package and QTI validation report availability through the Task 280
  package generator whenever QTI is requested or defaulted;
- unavailable QTI package downloads when validation fails, with
  `qti_validation_report` still available.

The Skriptoteket adapter/UI task must add consumer conformance tests proving:

- the adapter constructs only the governed job spec and headers;
- conversion policy remains in Sir Convert;
- teachers can see partial, readiness, validation-failed, and manual-follow-up
  states;
- downloaded and saved user-file artifacts preserve bundle metadata.

The later public Exam Converter runtime task must add Sir Convert conformance
tests proving:

- valid `PublicConversionGrantV1` submit, status, result, artifact manifest,
  and named artifact download behavior for the
  `digiexam_dxe -> examnet_migration_bundle` route;
- `owner_kind=public_grant` persistence, owner digest derivation from verified
  grant material, exact duplicate-submit convergence, and mismatched
  grant/idempotency reuse rejection;
- rejection for missing grant, malformed grant, expired grant, wrong audience,
  wrong capability, wrong route, over-target requests, replayed `jti`, forged
  issuer/key id, and valid `X-API-Key` without public grant ownership;
- `PublicArtifactReadLeaseV1` rejection for missing, expired, wrong-job,
  wrong-artifact, wrong-owner, widened-target, and replay-outside-idempotency
  cases;
- direct public `convert.hule.education` traffic remains fail-closed outside
  the accepted grant lane;
- forbidden result-PDF data is absent from public API responses, product-facing
  logs, manifests, and artifacts.

## Follow-On Implementation Gates

Task 278 authorizes this contract only. The next implementation work must be
split as follows:

- QTI/native renderer: Task 280 provides deterministic sample packages and
  validation reports, and Task 282 integrates that generator into the service
  route for the currently governed MCQ/free-text/image-bearing profile.
- Sir Convert service runtime exposure: Task 282 adds request validation, job
  execution, artifact bundle persistence, named artifact routes, and API tests.
  Product/browser exposure also depends on the HuleEdu auth-edge story at
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`.
- Skriptoteket adapter/UI and user-file persistence: a later Skriptoteket-owned
  task that consumes the accepted Sir Convert contract without forking
  conversion policy.
- Public Exam Converter runtime: a later governed runtime task may consume
  HuleEdu `TASK-0563` and Sir Convert Task 291 to implement
  `PublicConversionGrantV1` verification, `owner_kind=public_grant`, and
  `PublicArtifactReadLeaseV1` authorization for Skriptoteket `PR-0320`.

No Skriptoteket code, editable DOCX generation, Exam.net browser automation, or
public runtime conversion is approved by Task 278 alone.
