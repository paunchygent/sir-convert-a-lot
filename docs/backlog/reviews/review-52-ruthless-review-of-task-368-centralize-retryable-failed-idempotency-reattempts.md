---
id: review-52-ruthless-review-of-task-368-centralize-retryable-failed-idempotency-reattempts
title: Ruthless review of Task 368 centralize retryable failed idempotency reattempts
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - approved
  - task-368
  - v2
  - idempotency
  - retry
  - service-boundary
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 368. This reviewer did not author the
implementation or tests and did not modify production or test files. The only
intentional mutation from this pass is this retained review artifact plus any
generated docs index refresh required by docs-as-code validation.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/035-docling-pdf-conversion.md`
- `.codex/rules/046-docker-compose-v2-and-debugging.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/081-pdm-and-dependency-management.md`
- `.codex/rules/085-postgresql-and-migrations.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/README.md`
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- Context7 `/pydantic/pydantic` query for Pydantic v2 optional nullable fields,
  generated JSON schema, and `ConfigDict(extra="forbid")` behavior.

Implementation and test files reviewed:

- `scripts/sir_convert_a_lot/infrastructure/idempotency_store.py`
- `scripts/sir_convert_a_lot/application/contracts_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_structured_llm_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
- `tests/sir_convert_a_lot/test_api_contract_v2.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- Task and converter-contract docs changed in the working tree.

Public/operator surfaces affected:

- `POST /v2/convert/jobs` idempotency replay and reattempt policy.
- Create-job JSON response body metadata under `idempotency`.
- `X-Idempotent-Replay` header accuracy, with JSON body as the authoritative
  caller signal.
- Failed/canceled result, singular artifact, named artifact, partial artifact,
  and checkpoint terminal error details for safe `failure_retryable` exposure.
- Converter and downstream integration contract documentation.

Compatibility posture:

- The change is additive at the Service API v2 response body: existing job
  response fields remain, and create-job responses now include service-owned
  idempotency metadata.
- Strict replay remains the preserved behavior for active, succeeded,
  non-retryable failed, canceled, same-key/different-fingerprint, and missing
  old-job cases.
- The Task 63 CLI-side retry wrapper remains present only as preexisting Task
  369 cleanup debt. This review did not treat it as implemented or approved for
  long-term retention.
- No database, durable queue migration, Gateway/Skriptoteket shortcut, pointer
  deletion/quarantine, or Task 369 code removal was found in the Task 368 patch.

## Findings

No blocking findings.

The patch correctly moves retryable-failed create-job replay handling to the
Service API v2 admission boundary. `POST /v2/convert/jobs` now delegates one
scoped decision through `admit_create_job_with_idempotency_v2()`
(`scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:311`), and the
policy creates a fresh attempt only when the currently pointed job is
`failed` with `failure_retryable=true`
(`scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py:83`).
Non-retryable failed, active, succeeded, and canceled jobs fall through to
strict replay (`scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py:111`).

Lineage and metadata are service-owned and sanitized. The store retains
`active_job_id`, `attempt_count`, and previous attempt summaries
(`scripts/sir_convert_a_lot/infrastructure/idempotency_store.py:130`), while
the public response model exposes only job id, status, retryability, replayed
job id, and reattempt-of job id
(`scripts/sir_convert_a_lot/application/contracts_v2.py:99`).
Result/artifact failure details add `failure_retryable` only for failed jobs,
with no artifact bytes or unsafe content exposed
(`scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py:93`).

Race safety is acceptable for the current Hemma/API process model. The reviewed
runtime starts uvicorn without `--workers` in the packaged image and production
compose command (`Dockerfile:30`, `compose.yaml:56`), and the create-job route
uses one process-local scope lock around the read/decision/write sequence
(`scripts/sir_convert_a_lot/infrastructure/idempotency_store.py:74`). Atomic
JSON replacement prevents torn records but is not an inter-process lock; if a
future deployment adds uvicorn workers, replicas, or a second public API process
against the same idempotency volume, a new governed task must add file/OS-level
or database-backed compare-and-swap locking before claiming the same race
guarantee.

The tests are behavioral rather than helper-only. The focused regression proves
the old poisoned replay becomes a new active attempt with service metadata
(`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py:577`).
The same file covers non-retryable failed strict replay, active/succeeded/
canceled strict replay, same-key/different-fingerprint conflicts, missing old
job behavior, and concurrent same-scope replay convergence
(`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py:626`,
`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py:660`,
`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py:721`,
`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py:768`).
The read/cancel tests preserve fail-closed terminal result/artifact behavior
with safe retryability metadata
(`tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py:40`).

The generated OpenAPI surface includes the new idempotency components and the
converter/downstream/audio docs describe JSON `idempotency.state` as the
authoritative caller signal. Headers remain accurate but non-authoritative.

Working-tree note: Task 367 review/task docs contain whitespace/list-format
churn, and Task 370/Qwen checkpoint-policy files are present in the working
tree. I did not treat those files as Task 368 implementation evidence and did
not classify them as Task 368 blockers.

## Follow-up Actions

1. Task 369 remains required after Task 368 is deployed and live-proved: remove
  the historical CLI/client failed-replay auto-rerun wrapper so retry policy is
  not preserved outside the service boundary.
1. If the API deployment ever moves beyond the current single-process uvicorn
  shape for create-job traffic, add a governed race-safety task for
  inter-process idempotency locking before enabling that process model.
1. Separately track the full-suite timing failure observed in
  `tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py::test_parallel_resume_requires_valid_retained_checkpoint_and_returns_new_job_id`.
  The node passed in isolation and is not attributed to Task 368, but
  `coverage-gate` did not exit green in this review run.

## Decision

approved

## Response

Task 368 is approved for deploy/live-proof. This approval is scoped to the
Service API v2 central retryable-failed reattempt implementation and contract
updates. It does not approve Task 369 cleanup as complete and does not replace
the required Hemma live-proof gate in the Task 368 acceptance criteria.

## Completion

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py::test_retryable_failed_idempotency_replay_admits_new_attempt -q`
  passed: `1 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed: `90 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py -q`
  passed: `10 passed`.
- `pdm run typecheck-all` passed:
  `Success: no issues found in 896 source files`.
- `pdm run coverage-gate` did not exit green because the full suite had one
  timing-sensitive failure in
  `tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py::test_parallel_resume_requires_valid_retained_checkpoint_and_returns_new_job_id`.
  Coverage itself passed the configured threshold: total coverage `95.53%`,
  required `90.0%`, with `1747 passed`, `6 skipped`, and `1 failed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py::test_parallel_resume_requires_valid_retained_checkpoint_and_returns_new_job_id -q`
  passed in isolation: `1 passed`.
- `git diff --check` passed before this retained review artifact was created.

## Checklist

- [x] Scope reviewed
- [x] Findings recorded
- [x] Decision recorded
- [x] Verification recorded
