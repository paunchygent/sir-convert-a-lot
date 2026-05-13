---
id: task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes
title: Implement DigiExam migration service runtime artifact bundle routes
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md
  - docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - api-v2
  - service-runtime
  - artifact-bundle
  - qti
  - skriptoteket
  - auth
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the Sir Convert service-runtime path for the accepted DigiExam
migration artifact-bundle contract.

This task turns the Task 278 docs contract and Task 280 QTI package generator
into runtime behavior for the `digiexam_dxe -> examnet_migration_bundle` route:
validated job submission, execution, terminal bundle persistence, owner-scoped
status/result/artifact reads, and named artifact download routes.

The public product path remains authenticated and Gateway-mediated. HuleEdu
story
`/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`
owns the HuleEdu auth-edge proxy and signing plumbing. This task owns only the
Sir Convert runtime contract and fail-closed service behavior.

Cutover alignment requirements from the HuleEdu team are in scope for this Sir
Convert docs slice:

- product/browser entry is HuleEdu Gateway `/sir-convert/v2/...`;
- downstream Sir Convert runtime routes remain `/v2/convert/...`;
- `convert.hule.education` remains reserved/fail-closed for browser product
  traffic;
- HuleEdu repo paths must use `/Users/olofs_mba/Documents/Repos/huleedu/...`;
- identity header examples must use exact HuleEdu casing:
  `X-HuleEdu-Identity-Context-Version`, `X-HuleEdu-Identity-Context`,
  `X-HuleEdu-Identity-Key-Id`, and `X-HuleEdu-Identity-Signature`;
- the converter/auth docs must publish the required audience, grants, owner
  envelope, error codes, payload limits, artifact manifest schema, and named
  artifact routes.

## PR Scope

- Add the `digiexam_dxe -> examnet_migration_bundle` route execution behind
  service API v2 without reopening parser, IR, PDF-renderer, or QTI package
  contracts already accepted in Tasks 274-281.
- Validate multipart input for:
  - required `.dxe` primary upload as `file`;
  - required JSON `job_spec`;
  - optional `graded_result_pdf`;
  - optional `parity_pdf`;
  - rejection of unsupported companions, `resources`, `reference_docx`, and
    unsafe payload shapes.
- Enforce Task 278 idempotency semantics over normalized job spec plus `.dxe`
  and companion file SHA-256 digests.
- Execute the existing DigiExam parser, IR, embedded asset handling,
  Exam.net-oriented PDF renderer, and Task 280 QTI package generator through a
  modular service orchestration path.
- Persist a terminal bundle manifest using
  `digiexam_migration_bundle_v1` with deterministic artifact keys, filenames,
  content types, sizes, hashes, retention metadata, and availability states.
- Add named artifact reads:
  - `GET /v2/convert/jobs/{job_id}/artifacts`
  - `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`
- Keep the existing singular `/artifact` compatibility route only if it can
  return `artifact-bundle.json` without weakening named-route conformance.
- Enforce verified identity-derived ownership for job status, result, artifact
  listing, and named artifact download. `X-API-Key` remains transport-only and
  must not authorize cross-user reads for user-originated workloads.
- Reject missing, invalid, expired, wrong-audience, unknown-key, malformed, or
  spoofed `InternalIdentityContextV1` inputs on user-originated job and artifact
  paths according to
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- Preserve privacy constraints: no wrong answers, free-text student answers,
  scores, identity markers, or student-performance history from companion
  result PDFs may appear in API responses, IR, manifests, reports, logs intended
  for product consumption, or artifacts.
- Keep the implementation decomposed into small domain/application/infrastructure
  components. Do not create a monolithic route or renderer module; respect the
  repo module-size and SRP rules, and add Google-style module docstrings to new
  or materially changed Python modules.
- Use Dishka DI where it clarifies runtime composition, route dependencies, or
  service orchestration.

Out of scope:

- HuleEdu Gateway route/proxy implementation.
- Skriptoteket UI, adapter, or user-file persistence.
- Exam.net browser automation or upload.
- Editable DOCX generation for teacher-owned Exam.net artifacts.
- Anonymous public conversion or direct public product access to
  `convert.hule.education`.

## Deliverables

- [x] Runtime request validation for the DigiExam migration bundle route.
- [x] Runtime orchestration that produces PDF, QTI, IR, manifest,
  manual-follow-up, warnings, and asset-summary artifacts from accepted inputs.
- [x] Durable terminal artifact bundle persistence with deterministic metadata.
- [x] Named artifact listing and download routes.
- [x] Owner-scoped authorization for job/result/artifact reads.
- [x] Deterministic errors for missing, blocked, failed, not-implemented, and
  unsupported artifacts.
- [x] API tests for request validation, idempotency, authorization, bundle
  metadata, artifact downloads, QTI integration, blocked shapes, and privacy.
- [x] Live service-route smoke coverage over representative local OneDrive
  `.dxe` corpus files, without promoting raw corpus content to tracked
  artifacts.
- [x] Docs/handoff updates linking HuleEdu `ST-01-07` as the auth-edge
  dependency before product cutover.

## Acceptance Criteria

- [x] `POST /v2/convert/jobs` accepts the governed `digiexam_dxe` job spec and
  required `.dxe` upload, rejects unsupported companion parts, and records
  route-specific idempotency over all accepted payload digests.
- [x] A successful job produces a terminal `digiexam_migration_bundle_v1`
  manifest with all required Task 278 artifact entries:
  `bundle_manifest`, `examnet_pdf`, `qti_package`, `qti_validation_report`,
  `ir_json`, `migration_manifest`, `manual_follow_up_report`,
  `warnings_report`, and `asset_summary`.
- [x] `qti_package` and `qti_validation_report` use the Task 280 generator and
  validation report contract instead of placeholder-only availability.
- [x] `GET /v2/convert/jobs/{job_id}/artifacts` returns the bundle manifest
  JSON, and `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}` returns
  artifact bytes with the manifest content type.
- [x] Missing, blocked, not-implemented, failed, or unsupported artifact reads
  return deterministic error envelopes rather than empty files or private
  storage paths.
- [x] Owner A cannot read job status, result, artifact list, or named artifact
  bytes for Owner B even when the transport API key is valid.
- [x] Wrong-audience `InternalIdentityContextV1`, especially
  `aud=skriptoteket`, fails closed for Sir Convert user-originated runtime
  paths. The accepted audience is `sir-convert-a-lot`.
- [x] Browser cookies, bearer tokens, CSRF headers, unsigned identity headers,
  query-string identity claims, and `X-API-Key` alone are not accepted as user
  identity.
- [x] Companion result-PDF enrichment remains correct-answer-only and privacy
  proof tests show forbidden result data is absent from product-visible outputs.
- [x] Focused tests cover complete, partial, blocked, and manual-follow-up
  bundles, including embedded assets and unsupported resource classes.
- [x] Focused tests submit representative local OneDrive corpus `.dxe` files
  through the live service route instead of relying only on the single
  sanitized fixture.
- [x] The implementation remains modular and testable, with no new broad
  catch-all runtime or renderer modules.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

Task 282 landed the downstream Sir Convert service-runtime side only. Product
and browser entry remains HuleEdu Gateway-owned at `/sir-convert/v2/...`; Sir
Convert continues to expose the downstream `/v2/convert/...` routes. Runtime
implementation added:

- `digiexam_dxe -> examnet_migration_bundle` JobSpec support;
- HuleEdu `InternalIdentityContextV1` verification with exact
  `X-HuleEdu-*` header spelling in docs/tests and required
  `aud=sir-convert-a-lot`;
- route-specific multipart companion validation, payload limits, idempotency
  digests, and generic companion rejection;
- terminal `digiexam_migration_bundle_v1` persistence with deterministic named
  artifact entries;
- `GET /v2/convert/jobs/{job_id}/artifacts` and
  `GET /v2/convert/jobs/{job_id}/artifacts/{artifact_key}`;
- Task 280 QTI package/report integration into runtime bundles;
- owner-derived status/result/artifact reads that fail closed for cross-owner
  access even with a valid transport API key.

Focused API tests include synthetic contract cases, the sanitized embedded-image
fixture, blocked artifact reads, and a bounded live service-route smoke over
two local OneDrive validation-corpus `.dxe` files:

- `1776888013-ak7-lag-och-ratt.dxe`
- `1790207116-23c-atom-och-karnfysik-eca.dxe`

The raw OneDrive corpus remains local-only under the Task 281 policy; tests
skip the live corpus subset when the local raw files are absent.

Review 12 remediation completed the remaining public contract gaps: explicit
`conversion.targets` now controls target generator execution, unrequested
target-specific artifacts are persisted as `not_requested`, and
`GET /v2/convert/jobs/{job_id}/result` returns route-specific bundle metadata
derived from the terminal `artifact-bundle.json` manifest.
