---
id: task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke
title: Consume HuleEdu InternalIdentityContextV1 trust profile and acceptance smoke
type: task
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/reviews/review-task-0676-01-ruthless-review-task-0676-internalidentitycontextv1-trust-profile.md
labels:
  - auth
  - gateway
  - internal-identity
  - trust-profile
  - acceptance-smoke
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Consume HuleEdu's sanitized `InternalIdentityContextV1` trust profile in Sir
Convert runtime configuration, bind it to the existing signed internal identity
verifier, and prove a content-safe acceptance smoke before downstream product
proofs rely on the verifier.

## PR Scope

- Add typed Sir Convert runtime config for the HuleEdu trust profile fields:
  environment id, issuer, audience, key id, trusted public key source, canonical
  DER SPKI SHA-256 fingerprint, TTL, and allowed clock skew.
- Load the profile from a governed environment surface and load active PEM
  public key material from the existing public-key env/path surface.
- Compare the active key's canonical DER SPKI fingerprint with the profile
  fingerprint during runtime config load; fail closed on missing key material
  or fingerprint mismatch.
- Ensure the existing `InternalIdentityContextV1` verifier uses the profile
  issuer, audience, key id, TTL, and skew when a trust profile is configured.
- Preserve direct explicit `ServiceConfig(...)` test construction without
  adding API-key identity fallback, Sir-local signed identity, shims, or loose
  untyped config.
- Add a content-safe acceptance smoke using a HuleEdu-contract signed probe
  generated from test key material because the upstream retained artifact is a
  sanitized profile, not a retained live signed payload.
- Retain only sanitized acceptance evidence: profile metadata, pass/fail
  status, and red/green command outcomes; no private keys, signed headers,
  credentials, or conversion payloads.

## Deliverables

- [x] Typed trust-profile config model and env loader.
- [x] Existing verifier path consumes the configured trust profile.
- [x] Focused tests for acceptance smoke and fail-closed drift/mismatch cases.
- [x] Local/prod env surfaces documented or wired for sanitized profile input.
- [x] Sanitized implementation evidence recorded in this task and handoff.

## Acceptance Criteria

- [x] Runtime config accepts HuleEdu's sanitized local/prod profile shape and
  derives verifier issuer, audience, key id, TTL, and skew from typed config.
- [x] Runtime config fails closed when the configured public key is missing or
  its canonical DER SPKI SHA-256 fingerprint differs from the trust profile.
- [x] A signed content-safe probe that matches the profile verifies through
  `require_verified_internal_identity_v2`.
- [x] Unknown key id, invalid signature, wrong issuer, wrong audience, and
  expired contexts fail closed through the existing verifier path.
- [x] No API-key-only identity, Sir-local signed identity, shims, `Any`,
  casts, type ignores, or lint ignores are introduced.
- [x] Focused tests plus docs, skills, handoff, diff, lint, and type gates pass.

## Test Requirements

- [x] Red-first focused profile/config/verifier tests before production code.
- [x] Green focused auth/config/smoke tests after implementation.
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`
- [x] Type/lint gates required by touched Python code.

## Implementation Evidence

- Added `internal_identity_trust_config.py` with typed profile parsing for
  `local-auth-integration` and `hemma-production`, exact issuer/audience/key id
  profile fields, TTL/skew binding, JSON/path env loading, legacy override
  drift checks, active public-key lookup, and canonical DER SPKI SHA-256
  fingerprint comparison.
- Added `pem_public_key_config.py` for shared PEM normalization, file loading,
  RSA public-key parsing, and DER SPKI fingerprinting.
- `service_config_from_env()` now produces profile-derived
  `internal_identity_public_keys`, expected issuer, expected audience, TTL,
  skew, and `internal_identity_trust_profile` when the sanitized profile is
  configured. Direct explicit `ServiceConfig(...)` tests remain supported.
- `require_verified_internal_identity_v2()` now uses the profile key id,
  issuer, audience, TTL, and skew when a trust profile is present; unknown key
  ids, invalid signatures, wrong issuer/audience, exceeded TTL, future `iat`,
  and expired contexts still fail through the existing verifier path.
- Local and production compose services now require
  `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON` beside the existing public-key
  path, so a HuleEdu profile fingerprint drift fails during runtime config load.
- Updated
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
  with the JSON/path env surfaces, typed fields, canonical DER SPKI rule, and
  acceptance-smoke evidence boundary.

## Red-First Evidence

- Red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py -q`
  failed with `4 failed, 5 passed` before production changes. The failures
  showed no `internal_identity_trust_profile` config field, no fail-closed
  missing-key behavior when a profile was configured, and ignored fingerprint
  mismatch / PEM file-byte fingerprint drift.

## Green Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py -q`
  passed with `9 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  passed with `39 passed`.
- `pdm run typecheck-all` passed with `Success: no issues found in 878 source
  files`.
- `pdm run format-all` passed.
- `pdm run lint-fix` passed and ran the embedded docs validators.
- `pdm run docs-sync` passed and refreshed generated indexes.
- `pdm run docs-validate` passed with `Validated 477 backlog files` and
  `Validated docs=552 rules=11`.
- `pdm run skills-validate` passed with `skills-validate: ok`.
- `pdm run handoff-validate` passed with `handoff-validate: ok`.
- `git diff --check` passed with no whitespace errors.

## Acceptance Smoke Boundary

The acceptance smoke is not a retained live HuleEdu header proof. HuleEdu's
upstream retained artifact is a sanitized trust profile, so Sir Convert proves
the closest truthful downstream boundary by loading a sanitized HuleEdu-shaped
profile and configured test public key, generating a content-safe
HuleEdu-contract probe with ephemeral test private key material, and verifying
that probe through `require_verified_internal_identity_v2`.

Retained evidence is sanitized: environment id, issuer, audience, key id,
trusted public key source, canonical DER SPKI fingerprint, TTL/skew, and command
outcomes. No private key, signed identity context header, signature header,
credentials, conversion payload, or real HuleEdu user/org/tenant content is
retained.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
