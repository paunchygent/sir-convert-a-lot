---
type: reference
id: REF-SIRCON-GENERAL-digiexam-migration-service-api-artifact-contract
title: DigiExam Migration Service API Artifact Contract
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: general
summary: DigiExam Migration Service API Artifact Contract
retired_ids:
- CONV-digiexam-migration-service-api-artifact-contract
---

## Overview

## Facts And Semantics

## Decisions And Interpretation

## Historical Source Content

### Purpose

This reference defines the Sir Convert-a-Lot v2 DigiExam migration route. Skriptoteket owns upload UX, progress presentation, downloads, and saving to authenticated user files. Sir Convert owns `.dxe` parsing, sanitized evidence enrichment, intermediate/effective exam representations, Exam.net rendering, bundle manifests, retention, and job/artifact authorization. This route is for `digiexam_dxe` input; Exam.net-origin PDFs/Word files use the separate authoring route.

### Route and lifecycle

The route uses the shared v2 lifecycle:

- `POST /v2/convert/jobs`
- `GET /v2/convert/jobs/{job_id}`
- `GET /v2/convert/jobs/{job_id}/result`
- `GET /v2/convert/jobs/{job_id}/artifacts`
- `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`

Its route key is `source.format=digiexam_dxe` and `conversion.output_format=examnet_migration_bundle`. A succeeded job means a terminal bundle exists; `target_readiness_report_v1`, not job status or a local UI flag, controls whether each target can be downloaded. OpenAPI must be exported with `pdm run openapi-export-v2` and match the runtime schemas.

Gateway owns the product/browser `/sir-convert/v2/convert/...` prefix and strips it before forwarding to Sir Convert. Sir Convert exposes only `/v2/convert/...`. `convert.hule.education` remains reserved/fail-closed for direct browser, anonymous, status-page, or external M2M traffic unless a separate accepted ADR authorizes a lane.

### Bundle and cutover authority

The active contract is `digiexam_migration_bundle_v3`. The v3 break is hard: no v1/v2 compatibility alias, source-only fallback, dual response mode, generic `review_decision`, or `accept_current_state_for_export`. Teacher corrections, manual answer keys, and reviewed advisory intents are validated and applied to an effective exam; the service emits `answer_key_review_state` and keeps `target_readiness_report_v1` as export authority.

### Authentication and ownership

Internal transport uses `X-API-Key`; job creation requires `Idempotency-Key`, and `X-Correlation-ID` is optional but returned. User-originated calls also carry signed HuleEdu `InternalIdentityContextV1` with audience `sir-convert-a-lot` using the exact headers:

- `X-HuleEdu-Identity-Context-Version`
- `X-HuleEdu-Identity-Context`
- `X-HuleEdu-Identity-Key-Id`
- `X-HuleEdu-Identity-Signature`

Required claims include `context_version=1`, `iss=api_gateway_service`, `aud=sir-convert-a-lot`, and valid `iat`/`exp` (the current default TTL is 60 seconds). Grants are route-scoped: create, read-own status/result, cancel-own, and read-own artifact/list operations. Persisted user ownership derives from the verified signed envelope (`owner_kind=user`, signed realm/subject, org/tenant, `source_app`, and `workload_purpose`) and is stored as the deterministic Sir scope `identity:v1:user:sha256:<digest>`. API-key possession alone never authorizes cross-user reads.

### Public Exam Converter grant exception

The public grant lane is contract-only and does not reopen `convert.hule.education` or authenticated ownership. HuleEdu mints `PublicConversionGrantV1`; Sir Convert verifies it for the single `digiexam_dxe_to_examnet_migration_bundle` route. The grant is not a user identity, browser session, API key, or operator lane and must contain no user/org/tenant/session identity fields. Required fields are version, issuer/audience, source app, capability, route/source/output keys, allowed targets, upload digest, policy/profile limits, TTL/lease/rate/concurrency profiles, correlation ID, `iat`/`exp`, and replay nonce `jti`. One `jti` creates at most one job; exact duplicates converge and mismatched reuse returns a deterministic `409`.

Public jobs persist `owner_kind=public_grant`, a digest derived only from approved grant material, route/target/policy snapshots, upload digest, correlation ID, and lease expiry. Public status/result require the matching unexpired grant. Public artifact list/download requires the exact signed `PublicArtifactReadLeaseV1` bound to grant `jti`, job, artifact key, owner digest, route, target snapshot, policy, timestamps, nonce, and correlation ID. Missing, malformed, expired, wrong-audience/capability/route, over-target, replayed, ownership-less, or lease-invalid requests fail closed with distinct v2 error codes; no API-key fallback is permitted.

### Request contract

`POST /v2/convert/jobs` is multipart:

- `file` (required `application/octet-stream`): the `.dxe` structure source;
- `job_spec` (required `application/json` string): canonical v2 spec;
- `graded_result_pdf` (optional PDF): sanitized correct-machine-mark evidence only;
- `parity_pdf` (optional PDF): visual parity evidence only;
- `digiexam_ingestion_overlay` (optional JSON): source-bound later review input named by `digiexam_migration_options.ingestion_overlay_filename`.

The route rejects `resources` and `reference_docx` parts. The job spec uses `api_version=v2`, upload source, `format=digiexam_dxe`, output `examnet_migration_bundle`, explicit targets (`examnet_pdf` and/or `qti_package`), Swedish artifact language, migration options, and `retention.pin=false`. `.dxe` remains the structure authority even when companion PDFs are supplied.

### Overlay, effective exam, and review state

The source IR remains immutable and carries source item IDs, sequence, type, fingerprints, assets, and source answer-key provenance. An ingestion overlay is accepted only when it echoes the source file digest, IR schema/digest, item identity, sequence, type, and source fingerprint. Supported effective patches cover governed item/prompt/option text, gap-fill visible prompts, point corrections, manual answer keys, and reviewed advisory completion; invalid or stale bindings are rejected. The service recomputes an effective exam and emits a compact `answer_key_review_state` for correction/replay. Skriptoteket must refresh readiness, artifact availability, validation state, and effective digest after every overlay or completion.

Matching pairs are source-neutral and cannot be invented by the DigiExam dialect. Readiness must distinguish missing/invalid pairs, association-limit violations, and unproven Exam.net import. Gap/open-cloze items retain accepted values and are not relabeled as generic free text. Export-only or incomplete-export policy cannot be encoded as source IR, overlay, correction replay, or readiness unlock.

### Bundle artifacts, readiness, and privacy

The terminal bundle manifest is authoritative for named artifacts, content type, deterministic filename, size, SHA-256, availability, and safe unavailable reason. At minimum it may expose `examnet_pdf`, `qti_package`, validation reports, manual-follow-up report, effective exam/report, overlay report, and manifest. Missing or unimplemented artifacts return deterministic errors; consumers use named artifact endpoints and no singular compatibility `/artifact` surface is introduced for this route.

`target_readiness_report_v1` rows include target, item/sequence when applicable, source fingerprint, readiness class, `export_enabled`, artifact key, reason code, teacher action, retryability, and message key. Readiness classes are `ready`, `needs_teacher_answer_key`, `unsupported_target_shape`, `target_validation_failed`, `provider_unavailable`, `not_requested`, and `not_implemented`. Item-level blockers remain visible even when an artifact-level unavailable code is also present.

The `.dxe` file is the structure source. Graded-result PDFs may contribute only source-bound correct machine-mark evidence. Wrong answers, free-text answers, scores, names, emails, class identifiers, and performance history must not appear in responses, logs, IR, manifests, reports, or artifacts. Raw uploads and private work directories remain internal retention-managed material.

Manual follow-up is item-addressable. Reasons include `manual_answer_key_required`, `manual_marking_required`, `unsupported_item_type`, `unsupported_target_shape`, `single_choice_import_validation_required`, `parser_warning_blocks_rendering`, `qti_validation_failed`, and `unsupported_examnet_qti_resource`; each entry carries item identity, sequence, type, reason, Swedish message, source evidence summary, and affected target keys.

### Errors and limits

Request and authorization failures use the standard v2 envelope. Required stable classes include missing/invalid `.dxe`, unsupported companion, unsafe result-PDF evidence, payload too large, job/artifact access denied, missing target artifact integrity failure, and unavailable QTI when validation fails. Terminal unavailable reasons include `source_ir_unavailable`, `manual_answer_key_required`, `unsupported_target_shape`, `embedded_asset_unavailable`, `qti_validation_failed`, `not_supported_by_examnet`, and `unsupported_examnet_qti_resource`.

### Skriptoteket adapter boundary

The adapter may build the canonical job spec, attach declared parts, generate deterministic headers, preserve Gateway identity headers, poll status/result, list/download named artifacts, and save bytes plus metadata to user files. It must not parse `.dxe` or PDFs, infer answer keys or target support, rewrite warnings, inspect Sir work directories, choose private paths, hide readiness/manual states, or convert user work to global service ownership. Saved metadata includes job ID, artifact key, deterministic/source and display filenames, content type, size, SHA-256, bundle schema, correlation ID, and save timestamp. Skriptoteket owns the saved copy; Sir Convert owns the source job until retention expiry.

### Conformance and follow-on gates

Runtime tests must cover multipart validation and limits, idempotency over `.dxe` and companions, owner-scoped reads, deterministic manifests, privacy exclusion, unavailable targets, QTI package/report behavior, overlay/effective-exam and answer-key review state, and named artifact routes. Consumer tests must prove thin transport-only adapters and visible readiness/manual states. A later public-grant task must test valid and rejected grants/leases, duplicate convergence, fail-closed public host behavior, and privacy. Task 280 owns deterministic QTI samples/validation; Task 282 owns service runtime/routes/tests; later consumer and public-grant tasks own integrations.
