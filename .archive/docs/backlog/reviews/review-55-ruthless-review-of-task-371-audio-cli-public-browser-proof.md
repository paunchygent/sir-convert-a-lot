---
id: review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof
title: Ruthless review of Task 371 audio CLI public browser proof
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - approved
  - task-371
  - cli
  - audio
  - idempotency
  - gateway-proof
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 371. This reviewer did not author the
implementation or tests, did not create a worktree, stayed on `main`, did not
deploy or live-proof, and did not modify production/test implementation files.
The only intentional mutation from this review pass is this retained review
artifact.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`

Task 371 files reviewed:

- `.codex/handoff.md`
- `docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `scripts/sir_convert_a_lot/application/contracts.py`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- `scripts/sir_convert_a_lot/interfaces/cli_helpers.py`
- `scripts/sir_convert_a_lot/interfaces/cli_manifest_writer_v2.py`
- `scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2_models.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2_upload_helpers.py`
- `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`
- `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py`
- `tests/sir_convert_a_lot/test_cli_v2_routes.py`
- `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py`

Public/operator surfaces affected:

- `convert-a-lot routes` and `convert-a-lot convert` route selection for local
  audio/video inputs to `audio -> transcript_bundle`.
- Service API v2 CLI job-spec construction for audio transcription options,
  execution policy, idempotency-key derivation, artifact download, and manifest
  entries.
- Public browser proof plan for the HuleEdu Gateway
  `/sir-convert/v2/convert/jobs` surface and correlated downstream Sir Convert
  create-job evidence.

Compatibility posture:

- Task 371 is additive route exposure for an already-governed Service API v2
  audio route.
- Task 369 remains normative: the CLI/client must not synthesize retryable
  failed remediation by salting idempotency keys, submitting a second job, or
  hiding lineage in the manifest.
- `--new-job` remains explicit independent user intent only.

Dirty-tree boundaries:

- Unrelated Task 367 and Task 370/Qwen dirty files exist in this checkout. I did
  not edit, revert, normalize, or treat those files as Task 371 implementation
  evidence.
- `docs/backlog/INDEX.md` remains generated-index drift outside this review
  artifact. I did not hand-edit it and did not run `docs-sync`.

## Findings

No remaining blocking findings.

Pass 1 requested changes because Task 371's browser proof shape pointed at
direct `https://convert.hule.education` / `POST /v2/convert/jobs` evidence,
while the governed audio contract requires browser/product traffic to enter
through HuleEdu Gateway `/sir-convert/v2/convert/...` unless a separate accepted
decision changes that posture.

James's narrow correction resolves that finding. The task now requires the
HuleEdu Gateway public browser surface `/sir-convert/v2/convert/jobs`
(`docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:167`),
forbids direct `convert.hule.education` browser traffic for the proof
(`docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:173`),
requires exactly one browser-visible
`POST /sir-convert/v2/convert/jobs`
(`docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:178`),
and requires Gateway plus downstream Sir Convert correlation ids for the same
request
(`docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:179`).
The evidence bundle also now requires downstream Sir Convert create-job
correlation evidence
(`docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:196`).

The operator CLI docs now make the direct public host example non-closing
evidence only: direct `https://convert.hule.education` can be operator/service
evidence, but cannot close Task 371 public browser proof or the Task 369 live
gate
(`docs/converters/sir_convert_a_lot.md:336`).

The implementation remains aligned with Task 369. The route submission path
performs one `convert_upload_to_artifact` call for each submitted file and builds
the manifest entry from the service-returned `job_id` and idempotency metadata
(`scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py:399`). Focused
tests prove audio route visibility, audio source inference, job-spec shape,
one-submit behavior, `service_reattempt` metadata preservation, and absence of a
caller-side second submit.

## Follow-up Actions

1. Public live proof is still pending. After deploy, the proof must use the
   HuleEdu Gateway browser surface `/sir-convert/v2/convert/jobs`, capture one
   browser-visible POST for the replay invocation, correlate the downstream Sir
   Convert create-job request, show service idempotency state
   `service_reattempt`, fetch the terminal artifact, and retain bounded logs.
1. Final overseer close-out should regenerate generated docs indexes only when
   unrelated Task 367/370 drift can be accepted or isolated. This review did not
   run `docs-sync` or hand-edit `docs/backlog/INDEX.md`.
1. Before commit/deploy, run any remaining non-mutating/mutating quality gates
   in a way that does not normalize unrelated dirty work.

## Decision

approved

## Response

Task 371 is approved for local implementation/proof-plan close-out. The reviewed
patch exposes the audio `transcript_bundle` route through the CLI/client, keeps
Task 369's one-submit and no-salting invariant intact, records only
service-returned job/idempotency metadata in manifests, and corrects the retained
public browser proof plan to the Gateway-owned `/sir-convert/v2/convert/jobs`
surface with downstream Sir Convert correlation evidence.

This approval does not claim the public live proof has been run. It approves the
implementation and retained proof shape before deploy/live proof.

## Completion

Reviewer-run evidence from pass 1:

- `pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed: `21 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py::test_routes_command_lists_supported_routes_in_stable_order -q`
  passed: `1 passed`.
- `git diff --check -- docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`
  passed after pass-1 artifact creation.

Reviewer-run evidence from pass 2:

- Read-only inspection confirmed the proof shape now targets
  `/sir-convert/v2/convert/jobs`, requires Gateway plus downstream Sir Convert
  correlation, and explicitly prevents direct `convert.hule.education` evidence
  from closing Task 371 public browser proof or the Task 369 live gate.
- Focused Task 371 tests were rerun because the pass-2 correction touched only
  docs, but the task still depends on the same CLI/client one-submit behavior:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`.
  Result: passed, `21 passed in 1.68s`.
- Required validation was rerun after updating this review artifact:
  `pdm run validate-tasks`.
  Result: passed, `Validated 498 backlog files`.
- Scoped whitespace validation was rerun after updating this review artifact:
  `git diff --check -- docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`.
  Result: passed.

Skipped in this review pass:

- No deploy or live proof, by instruction.
- No implementation, test, generated-index, Gateway, Skriptoteket, or runtime
  edits, by instruction.
- No `docs-sync`, because generated `docs/backlog/INDEX.md` is already dirty
  from unrelated Task 367/370 work and this review must not mix generated-index
  normalization into Task 371.

## Checklist

- [x] Scope reviewed
- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up actions recorded
- [x] Completion evidence recorded
- [x] Review closed
