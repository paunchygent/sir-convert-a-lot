# Session Handoff

## Session Handoff Contract (Mandatory)

- `handoff.md` is session-scoped working handoff, not long-term memory.
- At the end of each session, update handoff with:
  - completed work in this session,
  - validation evidence,
  - next-session goals.
- Before clearing/pruning this file, archive completed session summaries into
  `docs/backlog/current.md` (canonical long-term memory index).
- Status/checkoff synchronization is strict:
  - task file status must be terminal (`completed` or `done`) before task checkbox is checked in story/epic trackers,
  - all linked task statuses must be terminal before story status/checkbox can be terminal,
  - all linked story statuses must be terminal before epic status/checkbox can be terminal.

## 2026-03-01: Task 61 Completed (Pandoc Sandbox + Bounded Stderr)

### Completed

- Closed critical Pandoc SSRF/LFI attack surface by enforcing `--sandbox` across:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_docx_to_markdown.py`,
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_markdown.py`,
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_docx.py`,
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_markdown_to_html.py`.
- Added bounded-memory subprocess execution helper:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_subprocess.py`.
  - execution now discards stdout, captures bounded stderr only, and performs timeout-safe cleanup.
- Hardened executor error detail handling:
  - sanitized traversal-error filename echo in
    `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`.
- Extended wrapper tests to assert sandbox flags and timeout/error invariants:
  - `tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py`,
  - `tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py`,
  - `tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`.
- Terminalized planning artifact:
  - `docs/backlog/tasks/task-61-enforce-pandoc-sandbox-and-bounded-subprocess-stderr-handling.md`
    -> `status: completed`.
- Archived long-term memory entry in:
  - `docs/backlog/current.md` (2026-03-01 worklog section).

### Validation Evidence

- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 157 source files`)
- `pdm run run-local-pdm coverage-gate` (pass: `392 passed, 5 skipped`; coverage `95.39%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 86 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=108 rules=9`)

### Next Session Goals

- Run a focused ruthless review on task-60/task-61 changed files and ensure no residual
  conversion-surface security gaps remain.
- Decide whether to harden `specs_v2` strictness policy (`ConfigDict(strict=True)`) as a
  separate scoped task to avoid unintended API coercion breakage.

## 2026-03-01: Task 65 Completed (v2 PDF Layout Presets)

### Completed

- Landed ADR-0004 contract alignment (Task 64) and implemented `conversion.pdf_layout` for PDF outputs
  (Task 65):
  - v2 spec now supports typed PDF layout presets (paper size, orientation, margins).
  - v2 executor applies presets by writing deterministic CSS under the job workdir and passing it to
    WeasyPrint (authoritative page setup).
  - Updated normative v2 API and downstream integration docs for `pdf_layout` and the `docx -> pdf` route.
- Completed Task 66 (`docx -> pdf`):
  - added sandboxed Pandoc DOCX->HTML wrapper (`pandoc_docx_to_html.py`) with extracted media under workdir,
  - added executor branch (`pipeline_used="docx_to_pdf_v2"`) and CLI route registry entry (`docx -> pdf`),
  - added contract and unit tests, and updated normative converter docs.
- Fixed a strict file-size hygiene issue by splitting executor tests so all `test_v2_conversion_executor_*`
  modules remain \<500 LoC.

### Validation Evidence

- `pdm run run-local-pdm lint-fix` (pass: `All checks passed!`)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 167 source files`)
- `pdm run run-local-pdm coverage-gate` (pass: `416 passed, 5 skipped`; coverage `95.29%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 92 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=115 rules=9`)

### Next Session Goals

- Proceed with Skriptoteket curated conversion app cutover planning and execution (downstream work),
  now that `conversion.pdf_layout` and `docx -> pdf` exist in v2.

## 2026-02-28: Task 60 Completed (v2 Security/Resilience Hardening)

### Completed

- Implemented strict WeasyPrint resource sandboxing in
  `scripts/sir_convert_a_lot/infrastructure/weasyprint_html_to_pdf.py`:
  - blocks external URL fetching (`http/https/...`) and file URLs outside allowed workdir,
  - permits only local resources resolved under allowed root.
- Hardened path resolution in
  `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`:
  - rejects traversal for `conversion.css_filenames` (`css_invalid`),
  - rejects traversal for `conversion.reference_docx_filename` (`reference_docx_invalid`).
- Added deterministic Pandoc subprocess timeout handling across wrappers:
  - `pandoc_docx_to_markdown.py`,
  - `pandoc_html_to_markdown.py`,
  - `pandoc_html_to_docx.py`,
  - `pandoc_markdown_to_html.py`.
- Enforced HTML local-resource validation parity for all HTML source routes:
  - `html -> md`, `html -> pdf`, `html -> docx`.
- Added/updated security and timeout tests:
  - new `tests/sir_convert_a_lot/test_weasyprint_html_to_pdf.py`,
  - new `tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`,
  - expanded v2 executor and pandoc wrapper tests.
- Added and terminalized planning artifact:
  - `docs/backlog/tasks/task-60-harden-v2-converter-security-for-ssrf-traversal-and-timeout-enforcement.md` -> `status: completed`.

### Validation Evidence

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_weasyprint_html_to_pdf.py tests/sir_convert_a_lot/test_v2_conversion_executor_general.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_paths.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_pdf_to_docx.py tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py` (pass: `62 passed`)
- `pdm run run-local-pdm coverage-gate` (pass: `388 passed, 5 skipped`; coverage `95.53%`)
- `rm -rf .mypy_cache && pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 156 source files`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 85 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=107 rules=9`)

### Next Session Goals

- Commit and push the pending async-push + Task 60 remediation slice as one coherent checkpoint.
- Run a final ruthless review pass on changed files only (security + contracts + regressions).

## 2026-02-28: T15 + T16 Completed (Webhook Delivery + Push Runbook) and Epic 05 Closeout

### Completed

- Implemented Task 58 (`T15`) webhook delivery lane:
  - added queue-backed delivery worker with retry schedule and DLQ handoff:
    - `scripts/sir_convert_a_lot/infrastructure/webhook_delivery_v2.py`
  - wired runtime event enqueue hooks for queued/running/terminal lifecycle events:
    - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - added security helper enforcement for signature mismatch, stale timestamp, and replay detection.
- Added Task 58 test coverage:
  - `tests/sir_convert_a_lot/test_webhook_delivery_v2.py` (success/retry/DLQ/security cases),
  - updated adapter non-GPU E2E in same push-logic slice:
    - `tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime`.
- Completed Task 56 (`T16`) operational sign-off docs:
  - added `docs/runbooks/runbook-v2-async-push-delivery.md` with canary/rollback, triage, alert thresholds,
    and KPI formula/report templates.
  - linked async-push runbook from `docs/runbooks/runbook-hemma-devops-and-gpu.md`.
- Status/checkoff synchronization completed in strict order:
  - Task 58 -> `completed` -> Epic `T15` checked,
  - Task 56 -> `completed` -> Epic `T16` checked,
  - Story 15 -> `completed` -> Epic `S05` checked,
  - Epic 05 -> `completed`.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 153 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_api_contract_v2_webhook_onboarding.py tests/sir_convert_a_lot/test_webhook_delivery_v2.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py::test_adapter_integration_smoke_submit_poll_fetch_without_gpu_runtime` (pass: `31 passed`)
- `pdm run run-local-pdm coverage-gate` (pass: `373 passed, 5 skipped`; coverage `93.03%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=106 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Session Goals

- Run post-implementation ruthless review and release-readiness verification for Epic 05 completion.
- Prepare the next backlog slice after Epic 05 closeout.

## 2026-02-28: T14 Task 57 Completed (Webhook Onboarding + Secret Lifecycle)

### Completed

- Completed Task 57 (`T14`) in Epic 05 and moved task status to `completed`.
- Fixed webhook onboarding runtime/store integration mismatches:
  - aligned runtime webhook error mapping with concrete store/model error classes,
  - normalized rotate/revoke return semantics with deterministic service errors,
  - fixed overlap payload evaluation to use redacted `next_secret_present` state.
- Implemented onboarding capability checks:
  - `push:read` enforced for list/get,
  - `push:write` enforced for create/update/rotate/revoke/delete,
  - deterministic `403 insufficient_scope` details for missing capability.
- Expanded test coverage:
  - route contract tests for invalid API key and missing-scope cases,
  - store lifecycle tests for owner isolation, overlap expiry promotion, revoke behavior,
    and disabled/deleted delivery-target exclusion.
- Status synchronization in strict order:
  - Task 57 -> `completed` -> Epic `T14` checked.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 151 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_api_contract_v2_webhook_onboarding.py tests/sir_convert_a_lot/test_webhook_subscriptions_v2_store.py` (pass: `28 passed`)
- `pdm run run-local-pdm coverage-gate` (pass: `368 passed, 5 skipped`; coverage `93.32%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=105 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Session Goals

- Start Task 58 (`T15`) implementation slice for webhook delivery worker, retries/DLQ, and callback
  signing/timestamp/replay protection.
- Keep strict order: do not check Epic `T15` before Task 58 is terminal with evidence.

## 2026-02-28: T13 Task 55 Completed (Event Emission + SSE)

### Completed

- Implemented v2 lifecycle event persistence and replay primitives:
  - `scripts/sir_convert_a_lot/infrastructure/job_events_v2.py`
  - manifest-backed `event_id` (ULID), monotonic `sequence`, replay cursor handling, and pruning.
- Wired event emission into v2 lifecycle transitions and extracted store responsibilities to preserve
  `<500` LoC module limits:
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2_core.py`
  - `scripts/sir_convert_a_lot/infrastructure/job_store_v2.py`
- Added SSE stream route with replay + `410 cursor_expired` behavior and feature-flag gating:
  - `scripts/sir_convert_a_lot/interfaces/http_routes_job_events_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_api.py` (router registration)
- Added typed event contracts and SSE metrics payload fields:
  - `scripts/sir_convert_a_lot/application/contracts_v2.py`
- Updated required tests in the same implementation slice:
  - new `tests/sir_convert_a_lot/test_api_contract_v2_sse.py`
  - updated polling fallback regression in `tests/sir_convert_a_lot/test_api_contract_v2.py`
  - updated adapter non-GPU E2E lane in
    `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`.
- Status synchronization in strict order:
  - Task 55 -> `completed` -> Epic `T13` checked.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 145 source files`)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_sse.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py` (pass: `22 passed, 3 skipped`)
- `pdm run run-local-pdm coverage-gate` (pass: `352 passed, 5 skipped`; coverage `94.76%`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=105 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Session Goals

- Start Task 57 (`T14`) implementation slice for webhook onboarding CRUD + secret lifecycle.
- Keep strict order: do not check Epic `T14` before Task 57 is terminal with evidence.

## 2026-02-28: T02 -> T03 Async Push Docs Slice Completed

### Completed

- Task 53 (`T02`) confirmed terminal with ADR acceptance:
  - `docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md` set to
    `status: accepted`, with deterministic event/replay/signature/retry/DLQ constants.
- Task 54 (`T03`) implemented and terminalized:
  - created/published `docs/converters/multi_format_conversion_service_api_v2_async_push.md`
    covering SSE, webhook onboarding, delivery headers/signing, retries, replay, error taxonomy,
    polling fallback, and downstream integration patterns.
  - linked async contract from `docs/converters/multi_format_conversion_service_api_v2.md`.
- Status synchronization in strict order:
  - Task 54 moved to `completed`,
  - Epic 05 `T02` and `T03` checkboxes checked,
  - Story 15 moved to `in_progress` with first two acceptance criteria checked.
- Long-term memory updated:
  - archived this slice in `docs/backlog/current.md` and updated Next Actions to start at Task 55.

### Validation Evidence

- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=105 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- `rg -n "event_id|event_type|sequence|occurred_at|cursor_expired|X-SCAL-Webhook|retry|DLQ|polling fallback" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "multi_format_conversion_service_api_v2_async_push\\.md" docs/converters/multi_format_conversion_service_api_v2.md` (pass)
- `rg -n "status: accepted|task-54|task-55|task-56|task-57|task-58|story-15" docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md` (pass)

### Next Session Goals

- Start Task 55 (`T13`) implementation slice for event emission + SSE stream/replay behavior.
- Keep order gates strict: do not check `T13` before terminal Task 55 status and evidence updates.
- Update adapter non-GPU E2E in the same push-logic PR, per Story 15 requirements.

## 2026-02-28: Ruthless-Review Remediation (T03 Contract Hardening)

### Completed

- Closed review findings 1-4 for Task 54 contract completeness and KPI consistency:
  - expanded async push contract with onboarding update/rotate/delete examples,
  - added deterministic callback verification error codes
    (`webhook_signature_invalid`, `webhook_timestamp_outside_window`, `webhook_replay_detected`),
  - added explicit push auth capability and rate-limit semantics with deterministic
    `429 rate_limited` + `Retry-After` behavior for SSE/onboarding surfaces,
  - normalized webhook success KPI target to `>=100% within first 3 attempts` across Story 15,
    Epic 05, ADR 0003, async contract doc, and Task 56 acceptance text.

### Validation Evidence

- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=105 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- `rg -n "Update request example|Rotate-secret request example|Delete response semantics" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "webhook_signature_invalid|webhook_timestamp_outside_window|webhook_replay_detected" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)
- `rg -n "Authorization requirements|jobs:read|push:read|push:write|rate_limited|Retry-After|429 Too Many Requests" docs/converters/multi_format_conversion_service_api_v2_async_push.md` (pass)

### Next Session Goals

- Begin Task 55 (`T13`) implementation slice with SSE stream/replay behavior and event emission tests.

## 2026-02-28: T10 -> T11 -> T12 Completed in Order

### Completed

- Task 52 (`T10`) terminalized with downstream v2 integration contract publication:
  - added `docs/converters/downstream_integration_contract_v2.md`,
  - linked active converter/runbook docs to downstream contract authority.
- Task 50 (`T11`) terminalized with single-runtime cutover:
  - removed eval container/runtime overlays from `compose.yaml`, `Dockerfile`, and `pyproject.toml`,
  - deleted `scripts/sir_convert_a_lot/service_eval.py`,
  - removed eval-root readiness branches in app-state/health routes,
  - updated `scripts/devops/verify-hemma-gpu-runtime.sh` to v2 single-runtime probing,
  - updated compose/import-side-effect tests for single-runtime invariants.
- Task 51 (`T12`) terminalized with v2-only active-surface cleanup:
  - deleted inactive `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py`,
  - converted `scripts/sir_convert_a_lot/interfaces/http_client.py` transport to v2 endpoints,
  - simplified `scripts/sir_convert_a_lot/interfaces/cli_routes.py` to service-only route kind,
  - removed path-based v1 envelope fallback in `scripts/sir_convert_a_lot/interfaces/http_api.py`,
  - updated `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py` to v2-only route evidence,
  - rewrote stale v1 README narratives in `README.md` and `scripts/sir_convert_a_lot/README.md`.
- Status synchronization completed in strict order:
  - Task 50 -> `completed` -> Epic `T11` checked,
  - Task 51 -> `completed` -> Epic `T12` checked,
  - Story 12 -> `completed` -> Epic `S04` checked.

### Validation Evidence

- T11 targeted matrix:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_service_import_side_effects.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
  - pass: `17 passed`
- T12 targeted matrix:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
  - pass: `37 passed, 3 skipped`
- Full gates:
  - `pdm run run-local-pdm format-all` (pass)
  - `pdm run run-local-pdm lint-fix` (pass)
  - `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 142 source files`)
  - `pdm run run-local-pdm coverage-gate` (pass: `347 passed, 5 skipped`; coverage `94.94%`)
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Session Goals

- Start Epic 05 async-push slice in order:
  - Task 53 (`docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md`)
  - Task 54 (`docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md`)
- Keep strict completion ordering:
  - do not check Task 53/54 in epic until each task file status is terminal,
  - do not check Story 15 until all mapped async-push tasks are terminal.

## 2026-02-28: Async Push Planning Hardening

### Completed

- Hardened Story 15 + Tasks 53/54/55/57/58/56 planning docs for execution-readiness:
  - sequencing/dependency gates,
  - execution-plan slices,
  - risk controls,
  - minimum test matrix + validation command/evidence blocks.
- Updated ADR `0003` with deterministic constants for event types, replay, signature headers,
  replay window, retry schedule, and DLQ handoff policy.

### Validation Evidence

- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Session Goals

- Execute `T02` Task 53 by finalizing ADR `0003` and moving status to `accepted`.
- Execute `T03` Task 54 by publishing the normative async push contract doc.
