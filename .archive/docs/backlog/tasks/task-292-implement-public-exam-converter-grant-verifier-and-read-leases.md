---
id: task-292-implement-public-exam-converter-grant-verifier-and-read-leases
title: Implement public Exam Converter grant verifier and artifact read leases
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md
  - docs/backlog/tasks/task-291-define-public-exam-converter-grant-lane-for-digiexam-migration-bundles.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0565-implement-public-exam-converter-grant-minting-endpoint.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0322-st-21-03-exam-converter-public-live-upstream-proof.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - public-access
  - grant-verifier
  - artifact-lease
  - skriptoteket
---

Runtime implementation slice for the public Exam Converter grant lane defined
by Task 291 and HuleEdu Task 0565.

## Objective

Implement the Sir Convert side of `PublicConversionGrantV1` verification and
`PublicArtifactReadLeaseV1` issuance for the narrow public
`digiexam_dxe -> examnet_migration_bundle` lane.

The runtime must let Skriptoteket submit, poll, inspect results, list bundle
artifacts, and download named artifacts without modeling the work as an
authenticated user job or as `X-API-Key` ownership.

## PR Scope

- Verify HuleEdu-signed RS256 `PublicConversionGrantV1` tokens supplied by the
  Skriptoteket backend on the existing v2 DigiExam migration job routes.
- Accept the public grant only for
  `digiexam_dxe -> examnet_migration_bundle`, capability
  `documents.conversion_hub.exam_converter`, source app `skriptoteket`, and
  targets inside `examnet_pdf` / `qti_package`.
- Persist grant-owned jobs under a deterministic `public_grant` owner digest.
- Keep direct anonymous traffic and `X-API-Key`-only ownership fail-closed for
  the public lane.
- Issue short-lived `PublicArtifactReadLeaseV1` tokens after public job
  ownership is established:
  - a `bundle_manifest` lease for manifest reads;
  - exact artifact-key leases for named artifact downloads.
- Require matching, unexpired read leases for public artifact manifest and
  named artifact routes.
- Preserve existing authenticated `InternalIdentityContextV1` behavior.

## Architectural Shape

This slice must stay deliberately split. Do not implement public grant handling
as one route helper or one procedural validator.

- Contract shapes: define `PublicConversionGrantV1`,
  `PublicArtifactReadLeaseV1`, and small response fragments only. These models
  own JSON shape, required fields, and primitive field constraints. They do not
  verify signatures, compare jobs, know HTTP headers, or raise service errors.
- Token codec infrastructure: decode compact JWS/JWT envelopes and verify
  RS256 / HS256 signatures. This layer knows algorithms, key ids, PEM loading,
  and HMAC signing only. It does not know Exam Converter route constants or
  job ownership semantics.
- Public grant policy: evaluate HuleEdu grant trust and Exam Converter scope
  against an explicit public access profile. It returns typed decisions or
  value objects, not HTTP responses. It owns issuer, audience, TTL, capability,
  route, target, policy-version, and owner-digest derivation.
- Artifact lease policy: evaluate whether one lease authorizes one requested
  artifact for one public-grant-owned job. It must be a small policy with named
  predicates or decision cases; no long checklist function that mixes token
  shape, config, persisted job state, parent grant state, and HTTP error codes.
- Application use case: orchestrate transport API-key authentication, grant
  verification, route policy, job owner scope, idempotency key construction,
  lease issuing, and decision-to-`ServiceError` mapping.
- HTTP routes: remain thin. They extract headers and files, call the application
  use case, and add public lease fragments to JSON responses where required.

Configuration should be grouped as a public Exam Converter access profile
rather than scattered as many unrelated `ServiceConfig` fields. Tests should be
able to inject the profile directly without relying on ambient environment
state.

## Non-Goals

- Do not move grant minting into Sir Convert.
- Do not return browser-usable Sir Convert service credentials.
- Do not widen anonymous public conversion beyond the Exam Converter route.
- Do not create user, org, tenant, service, or operator ownership for public
  Exam Converter jobs.
- Do not weaken the Task 282 DigiExam result-PDF privacy boundary.

## Deliverables

- [x] Public Exam Converter contract DTOs for HuleEdu grants, Sir Convert
  artifact-read leases, and server-to-server response fragments.
- [x] Public token codec infrastructure for compact RS256 verification and
  HS256 artifact-read lease signing/verification.
- [x] Pure public grant and artifact-read lease policy module with explicit
  profile input and typed decision objects.
- [x] HTTP adapter/use-case boundary that maps public grant and lease decisions
  to existing `ServiceError` semantics without expanding route responsibilities.
- [x] Existing v2 DigiExam migration routes wired to public grant ownership,
  manifest lease issuance, and exact artifact-key lease enforcement.
- [x] Focused runtime tests for the positive submit/poll/result/manifest/
  download flow plus wrong-target, untrusted-key, missing manifest-lease, and
  wrong artifact-lease failures.

## Acceptance Criteria

- [x] Public submit with a valid HuleEdu grant creates exactly one
  public-grant-owned job for the DigiExam migration route.
- [x] API-key-only submit for the public lane still fails closed.
- [x] Wrong issuer, audience, capability, route, target, timestamp, or signing
  key is rejected deterministically.
- [x] Status/result reads for public jobs require the matching public grant and
  owner digest; they do not fall back to API-key ownership.
- [x] Manifest reads require a valid `bundle_manifest` artifact-read lease.
- [x] Named artifact downloads require a valid exact artifact-key read lease.
- [x] Public grant and read lease secrets/signing material are configurable
  server-side only and are not exposed in product-visible outputs.
- [x] Focused runtime tests cover positive submit/poll/result/manifest/download
  and negative no-grant, wrong-target, forged-key, and wrong-lease cases.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized

## Verification

- `pdm run test tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py -q`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if public work requires `InternalIdentityContextV1` claims.
- Stop if artifact reads cannot be bounded by exact job, owner digest, parent
  grant, and artifact key.
- Stop if the implementation would need to expose Sir Convert API keys or
  HuleEdu signing material to the browser.

## Implementation Evidence

Implemented on 2026-05-13 as a split runtime slice:

- Contract DTOs live in
  `scripts/sir_convert_a_lot/application/public_exam_converter_contract_v2.py`.
- Pure grant/lease policy decisions live in
  `scripts/sir_convert_a_lot/application/public_exam_converter_access_policy_v2.py`.
  Lease authorization is split into policy contexts plus token-identity,
  job-binding, route-policy, and lifetime decision helpers; HTTP adapters only
  decode, call policy, and map denials.
- Compact JWS/JWT cryptographic mechanics live in
  `scripts/sir_convert_a_lot/infrastructure/public_token_codec_v2.py`.
- HTTP boundary adaptation lives in
  `scripts/sir_convert_a_lot/interfaces/http_public_exam_converter_access_v2.py`
  and
  `scripts/sir_convert_a_lot/interfaces/http_public_exam_converter_artifacts_v2.py`.

Focused verification passed:

- `pdm run pytest tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py -q`
- `pdm run pytest tests/sir_convert_a_lot/test_public_exam_converter_access_policy_v2.py -q`
- `pdm run pytest tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py -q`
- `pdm run ruff check ...` for the changed runtime and test modules.
- `pdm run mypy ...` for the changed runtime and test modules.
