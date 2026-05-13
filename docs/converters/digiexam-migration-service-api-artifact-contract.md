---
type: converter
id: CONV-digiexam-migration-service-api-artifact-contract
title: DigiExam Migration Service API Artifact Contract
status: active
created: 2026-05-11
updated: 2026-05-13
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

Define the service API v2 extension contract for authenticated DigiExam
migration jobs submitted by Skriptoteket and executed by Sir Convert-a-Lot.

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

The canonical v2 status enum remains unchanged. A `succeeded` job means Sir
Convert produced a terminal migration bundle. Target-specific availability is
reported inside the bundle as `complete`, `partial`, or `blocked`; consumers
must not infer target availability from job status alone.

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

Direct anonymous public conversion is not part of this contract.

## Request Contract

### Multipart Parts

`POST /v2/convert/jobs` uses multipart form data.

| Part | Required | Content type | Rules |
| --- | --- | --- | --- |
| `file` | yes | `application/octet-stream` | Primary DigiExam `.dxe` export. This is the required structure source. |
| `job_spec` | yes | `application/json` string | Canonical v2 job spec with the route key below. |
| `graded_result_pdf` | no | `application/pdf` | Optional sanitized graded-result PDF. It may enrich correct machine-marked answers only. |
| `parity_pdf` | no | `application/pdf` | Optional blank or student-view PDF for visual parity evidence only. It is never the structure source when `.dxe` is present. |

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
    "manual_follow_up_policy": "emit_item_addressable_report"
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

The initial implementation may make `conversion.targets` optional and default
it to `["examnet_pdf", "qti_package"]`, but the terminal bundle must still
include explicit availability for every defaulted target.

### Accepted Companion Evidence

Accepted companion files are intentionally narrow:

- sanitized graded DigiExam result PDFs that expose correct machine-marked
  answers without retaining forbidden student-result data;
- blank or student-view DigiExam PDFs used only for visual parity and manual
  teacher review;
- no other companion file class is accepted by this route.

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
      "bundle_schema_version": "digiexam_migration_bundle_v1",
      "bundle_status": "partial",
      "source_sha256": "sha256:...",
      "target_availability": {
        "examnet_pdf": "available",
        "qti_package": "available"
      },
      "manual_follow_up_required": true,
      "warning_count": 3,
      "artifact_count": 9
    }
  }
}
```

`bundle_status` values:

- `complete`: all requested implemented targets are available and no manual
  follow-up is required.
- `partial`: at least one requested or default target is not available, but the
  bundle contains usable target artifacts or teacher-facing reports.
- `blocked`: no target artifact can be safely produced, but Sir Convert
  produced item-addressable diagnostics.

Source validation failures and unsafe companion evidence do not produce a
terminal bundle. They use the standard v2 error envelope.

`conversion_metadata.artifact_count` is the count of entries in the persisted
bundle manifest, including the `bundle_manifest` self-entry.
`conversion_metadata.warning_count` is copied from the persisted manifest
`warnings.count` value.

## Artifact Bundle Contract

The named artifact bundle is the product contract between Sir Convert and
Skriptoteket. Skriptoteket must use bundle metadata and named artifact download
routes. It must not inspect Sir Convert work directories.

### Bundle Manifest

The canonical bundle manifest schema version is
`digiexam_migration_bundle_v1`.

```json
{
  "schema_version": "digiexam_migration_bundle_v1",
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
      "filename": "examnet-import.pdf",
      "content_type": "application/pdf",
      "availability": "available",
      "size_bytes": 48192,
      "sha256": "sha256:...",
      "download_path": "/v2/convert/jobs/job_123/artifacts/examnet_pdf"
    },
    {
      "artifact_key": "qti_package",
      "filename": "qti-package.zip",
      "content_type": "application/zip",
      "availability": "available",
      "size_bytes": 8124,
      "sha256": "sha256:...",
      "download_path": "/v2/convert/jobs/job_123/artifacts/qti_package"
    },
    {
      "artifact_key": "qti_validation_report",
      "filename": "qti-validation-report.json",
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
  "warnings": {
    "artifact_key": "warnings_report",
    "count": 3
  }
}
```

Every artifact entry MUST include:

- `artifact_key`
- deterministic `filename`
- `content_type`
- `availability`
- `size_bytes` when available
- `sha256` when available, formatted `sha256:<hex>`
- `download_path` when available
- `blocker_code` when blocked, failed, or not implemented

`availability` values:

- `available`
- `blocked`
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

| Artifact key | Filename | Content type | Availability rules |
| --- | --- | --- | --- |
| `bundle_manifest` | `artifact-bundle.json` | `application/json` | Always available for terminal bundles. |
| `examnet_pdf` | `examnet-import.pdf` | `application/pdf` | Available when the Exam.net PDF renderer carries all required content and assets. Blocked when target shape is unsupported. |
| `qti_package` | `qti-package.zip` | `application/zip` | Available when the Task 280 QTI package generator passes the governed profile. Blocked when validation fails or the source shape falls outside the proof-gated QTI profile. |
| `qti_validation_report` | `qti-validation-report.json` | `application/json` | Present when QTI generation is requested or defaulted. Task 280 defines `examnet_qti_validation_report_v1`; Task 282 service bundles expose this report as a named artifact. |
| `ir_json` | `digiexam-ir.json` | `application/json` | Available when `.dxe` parsing reaches IR generation. May include teacher-owned embedded asset payloads required by renderers. |
| `migration_manifest` | `migration-manifest.json` | `application/json` | Available when IR manifest generation succeeds. Must not embed raw asset payloads or result-PDF private data. |
| `manual_follow_up_report` | `manual-follow-up.md` | `text/markdown; charset=utf-8` | Always available for terminal bundles. Empty or review-only when no action is required. |
| `warnings_report` | `warnings.json` | `application/json` | Always available for terminal bundles. Empty list when there are no warnings. |
| `asset_summary` | `asset-summary.json` | `application/json` | Always available for terminal bundles. Must contain hashes and metadata only, not raw base64 payloads. |

Deterministic filenames are fixed per artifact key. Display names and saved
filenames in Skriptoteket may add teacher-facing context, but the Sir Convert
bundle filenames remain stable for conformance tests.

### Named Artifact Endpoints

Task 282, the service runtime task that implements this contract, must add named
artifact reads:

- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`

`GET /artifacts` returns the bundle manifest JSON. `GET /artifacts/{artifact_key}`
returns the artifact bytes using the entry content type. Missing, blocked, or
not-implemented artifacts return deterministic route errors rather than empty
files.

The existing singular `/artifact` route may return `artifact-bundle.json` for
compatibility, but consumers for this route should prefer the named endpoints.

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
  "title": "Fråga 4",
  "item_type": "matching",
  "reason_code": "unsupported_target_shape",
  "message": "Kontrollera och skapa matchningsfrågan manuellt i Exam.net.",
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
| Blocked QTI target download | `409` | `qti_validation_failed` | Named QTI package download is unavailable because validation did not pass; the validation report remains downloadable. |

Terminal bundle blockers are machine-readable inside artifact entries and
manual-follow-up reports:

| Blocker code | Target | Meaning |
| --- | --- | --- |
| `blocked_ir` | all | IR parse status blocks target rendering. |
| `manual_answer_key_required` | `examnet_pdf`, `qti_package` | Source evidence lacks a machine-marked answer key. |
| `unsupported_target_shape` | `examnet_pdf`, `qti_package` | IR item is valid but no governed target shape exists. |
| `embedded_asset_unavailable` | `examnet_pdf`, `qti_package` | Referenced asset cannot be carried safely. |
| `qti_validation_failed` | `qti_package` | QTI generation ran but did not pass the governed validation profile. |
| `not_supported_by_examnet` | `qti_package` | Source content maps to QTI but falls outside the governed Exam.net QTI support profile. |
| `unsupported_examnet_qti_resource` | `qti_package` | Source resource class, such as audio, PDF attachment, or tool resource, must be added manually after import. |

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
- inspect Sir Convert job directories;
- choose private artifact paths;
- hide blocked or manual-follow-up states from teachers;
- convert user-originated work into global service-owned jobs.

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
  -o examnet-import.pdf
```

Skriptoteket save-to-user-files is a consumer-owned action using the downloaded
bytes plus the bundle metadata. The adapter must preserve the artifact key,
content type, size, SHA-256, source `job_id`, and correlation id in the saved
file metadata.

### Blocked Outcome

```json
{
  "schema_version": "digiexam_migration_bundle_v1",
  "job_id": "job_456",
  "bundle_status": "blocked",
  "artifacts": [
    {
      "artifact_key": "examnet_pdf",
      "filename": "examnet-import.pdf",
      "content_type": "application/pdf",
      "availability": "blocked",
      "blocker_code": "unsupported_target_shape",
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
- terminal bundle manifest entries with deterministic filenames, content
  types, sizes, hashes, retention, and availability states;
- absence of forbidden result-PDF data from API responses, logs intended for
  product consumption, IR, manifests, and reports;
- blocked target shapes producing diagnostics without publishing malformed
  target artifacts;
- QTI package and QTI validation report availability through the Task 280
  package generator whenever QTI is requested or defaulted;
- blocked QTI package downloads when validation fails, with
  `qti_validation_report` still available.

The Skriptoteket adapter/UI task must add consumer conformance tests proving:

- the adapter constructs only the governed job spec and headers;
- conversion policy remains in Sir Convert;
- teachers can see partial/blocked/manual-follow-up states;
- downloaded and saved user-file artifacts preserve bundle metadata.

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

No Skriptoteket code, editable DOCX generation, Exam.net browser automation, or
anonymous public conversion is approved by this task.
