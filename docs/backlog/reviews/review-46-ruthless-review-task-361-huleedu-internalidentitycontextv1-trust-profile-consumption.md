---
id: review-46-ruthless-review-task-361-huleedu-internalidentitycontextv1-trust-profile-consumption
title: Ruthless review Task 361 HuleEdu InternalIdentityContextV1 trust profile consumption
type: review
status: completed
priority: high
created: '2026-06-13'
last_updated: '2026-06-13'
related:
  - docs/backlog/tasks/task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke.md
  - docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - /Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/reviews/review-task-0676-01-ruthless-review-task-0676-internalidentitycontextv1-trust-profile.md
labels:
  - review
  - approved
  - task-361
  - huleedu
  - internal-identity
  - trust-profile
---
Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 361, using the current uncommitted Sir
Convert-a-Lot diff as the implementation under review. This pass did not
implement production fixes. The only intentional mutation from this reviewer
is this retained review artifact plus generated docs index refreshes.

Existing retained-review search found no prior Task 361 review under
`docs/backlog/reviews/`, so this artifact uses `review-46`.

Required instructions and references read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/046-docker-compose-v2-and-debugging.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-planning/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-planning/references/sir-convert-a-lot.md`
- Context7 `/pyca/cryptography` docs for `serialization.load_pem_public_key`
  and DER `SubjectPublicKeyInfo` public-key serialization.

Governing docs:

- `docs/index.md`
- `.codex/handoff.md`
- `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
- `docs/backlog/stories/story-35-preserve-internal-service-and-local-operator-sir-convert-lanes.md`
- `docs/backlog/tasks/task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke.md`
- HuleEdu approved upstream review:
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/reviews/review-task-0676-01-ruthless-review-task-0676-internalidentitycontextv1-trust-profile.md`

Authored files reviewed:

- `compose.local.yaml`
- `compose.yaml`
- `.codex/handoff.md`
- `docs/backlog/tasks/task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke.md`
- `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
- `scripts/sir_convert_a_lot/infrastructure/runtime_config.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_models.py`
- `scripts/sir_convert_a_lot/interfaces/http_internal_identity_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/internal_identity_trust_config.py`
- `scripts/sir_convert_a_lot/infrastructure/pem_public_key_config.py`
- `tests/sir_convert_a_lot/test_compose_contract.py`
- `tests/sir_convert_a_lot/test_local_compose_contract.py`
- `tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py`

Generated docs surfaces reviewed separately:

- `docs/backlog/INDEX.md`

Public and operational surfaces affected:

- `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON`
- `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_PATH`
- `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY`
- `HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH`
- Existing legacy drift-checked internal identity env overrides:
  issuer, audience, signing key id, TTL, and clock skew.
- `service_config_from_env()` internal identity config resolution.
- `require_verified_internal_identity_v2()` signed context verification.
- Local and production Docker Compose runtime env requirements.

Compatibility posture:

- Production and local compose now require a sanitized HuleEdu trust profile and
  fail closed if it is missing. This is an intentional operational break under
  Task 361.
- Direct explicit `ServiceConfig(...)` construction remains available for
  tests and local controlled setup.
- No compatibility shim, Sir-local identity signer, or API-key-only ownership
  path is approved for protected user-originated work.

## Findings

None.

## Review Notes

Docs-as-code authority is present and correctly shaped. Task 361 is a
completed PR-sized task linked to Story 35 and the Sir Convert
`InternalIdentityContextV1` authorization reference. The reference now records
the trust-profile env surfaces, exact HuleEdu profile fields, DER SPKI
fingerprint requirement, and sanitized acceptance-smoke boundary.

The consumed profile shape matches the approved upstream HuleEdu contract:
`environment_id`, `issuer`, `audience`, `key_id`,
`trusted_public_key_source`, `spki_sha256_fingerprint`, `ttl_seconds`, and
`skew_seconds`. The Pydantic profile forbids extra fields, restricts
environment ids to `local-auth-integration` and `hemma-production`, restricts
issuer/audience/key id to the HuleEdu values, bounds TTL and skew, and rejects
non-canonical fingerprint strings.

Runtime config binds the trust profile into the active verifier path. When a
profile is configured, legacy duplicate env values for issuer, audience, key
id, TTL, and skew must match the profile or config load fails. The active PEM
public key is loaded, converted to DER SubjectPublicKeyInfo, hashed with
SHA-256, and compared to the profile fingerprint before the verifier can
accept contexts. The verifier key map is narrowed to the trusted profile key
id, so an unknown header key id fails before signature acceptance.

The old fingerprint drift class is covered: a PEM file-byte SHA-256 digest is
rejected as a profile fingerprint, and a mismatched active public key fails
closed during runtime config load. The implementation does not normalize the
old Sir Convert production trusted-key drift away.

The verifier still fails closed for missing key material, unknown key id,
invalid signature, wrong issuer, wrong audience, expired context, future `iat`,
and TTL violations. Task 361's new suite directly covers the required missing
key, fingerprint mismatch, PEM-byte fingerprint mismatch, unknown key id,
invalid signature, wrong issuer, wrong audience, and expired-context cases;
the existing verifier logic retains the TTL and future-`iat` checks while now
reading the active limits from the trust profile.

The API-key review is scoped to this slice. `X-API-Key` remains transport
authentication, but protected user-originated routes still call
`require_internal_identity_auth_context_v2()`. The focused HTTP tests prove
API-key-only DigiExam migration create and structured-LLM operator mutation
fail without signed HuleEdu identity. No Task 361 code introduces a new
API-key identity fallback.

The acceptance smoke is honest enough for Task 361. HuleEdu did not provide a
retained live signed payload probe, and the Task 361 contract explicitly names
sanitized profile JSON plus a content-safe test-material signed probe as the
allowed downstream proof. The smoke exercises `service_config_from_env()` and
`require_verified_internal_identity_v2()` rather than helper internals, and
the retained evidence is metadata-only.

Line-count and SRP check:

- `scripts/sir_convert_a_lot/infrastructure/internal_identity_trust_config.py`:
  327 lines.
- `scripts/sir_convert_a_lot/infrastructure/pem_public_key_config.py`: 63
  lines.
- `scripts/sir_convert_a_lot/infrastructure/runtime_config.py`: 368 lines.
- `scripts/sir_convert_a_lot/infrastructure/runtime_models.py`: 168 lines.
- `scripts/sir_convert_a_lot/interfaces/http_internal_identity_v2.py`: 304
  lines.
- `tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py`:
  364 lines.

No reviewed production module exceeds the repo limit, and the new Python
modules include Google-style domain-purpose module docstrings.

## Decision

`approved`.

## Response

Task 361 is approved. The implementation consumes the HuleEdu
environment-scoped trust profile, binds the verifier to profile-derived trust
values, compares canonical DER SPKI fingerprints before accepting contexts,
and retains a truthful sanitized acceptance smoke. No remediation is required
by this review.

## Follow-up Actions

1. Deploy/runtime owners must provide
   `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON` for local and production
   compose lanes before product proof runs; otherwise the service is expected
   to fail closed.

## Verification

Reviewer inspection:

- Scoped the dirty worktree with `git status --short`, `git diff --stat`, and
  `git diff --name-only`.
- Searched retained reviews with `rg` and `find`; no existing Task 361 review
  was present.
- Inspected diffs and final file contents for the Task 361 changed files.
- Used Context7 for current PyCA cryptography API docs and confirmed the
  implementation matches `serialization.load_pem_public_key` plus
  `public_bytes(encoding=serialization.Encoding.DER,
  format=serialization.PublicFormat.SubjectPublicKeyInfo)`.
- Ran scoped forbidden-pattern and typing-escape searches over reviewed code,
  tests, docs, and compose files. No slice-local `Any`, `cast`, `type:
  ignore`, lint ignore, compatibility shim, deceptive catch-all, leaked
  signing material, or API-key identity fallback was found.
- Reviewed route authorization snippets for protected job/operator paths and
  existing HTTP boundary tests for API-key-only rejection.

Reviewer-run commands:

- `pdm run pytest-root tests/sir_convert_a_lot/test_huleedu_internal_identity_trust_profile_v1.py tests/sir_convert_a_lot/test_structured_llm_settings_route_v2.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`
  - passed, `39 passed`.
- `pdm run typecheck-all`
  - passed, `Success: no issues found in 878 source files`.

Post-artifact validation commands:

- `pdm run docs-sync`
  - passed and refreshed `docs/backlog/INDEX.md`,
    `docs/reference/INDEX.md`, `docs/runbooks/INDEX.md`, and `docs/index.md`.
- `pdm run docs-validate`
  - passed with `Validated 478 backlog files` and
    `Validated docs=553 rules=11`.
- `pdm run skills-validate`
  - passed with `skills-validate: ok`.
- `pdm run handoff-validate`
  - passed with `handoff-validate: ok`.
- `git diff --check`
  - passed with no whitespace errors.

## Completion

Review retained with `approved` on 2026-06-13.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
