---
id: task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor
title: Publish downstream integration contract for Skriptoteket Hule and Projektveckor
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - integration
  - downstream
  - api
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish a clear API integration contract for downstream GUI consumers in Skriptoteket, HuleEdu, and Projektveckor.

## PR Scope

- Publish a dedicated normative converter contract doc:
  - `docs/converters/downstream_integration_contract_v2.md`
- Define canonical API request/response examples for v2 routes used by downstream GUIs:
  - `pdf -> md`
  - `docx -> md`
  - `html -> md` (with `resources` bundle support)
  - template-selected DOCX output (`md -> docx` using `conversion.template`)
- Define deterministic lifecycle handling patterns:
  - create (`POST /v2/convert/jobs`)
  - poll (`GET /v2/convert/jobs/{job_id}`)
  - result (`GET /v2/convert/jobs/{job_id}/result`)
  - artifact download (`GET /v2/convert/jobs/{job_id}/artifact`)
  - cancel (`POST /v2/convert/jobs/{job_id}/cancel`)
- Define template discovery and selector behavior for GUI integrations:
  - `GET /v2/templates/docx`
  - `GET /v2/templates/docx/{template_id}`
  - `GET /v2/templates/docx/{template_id}/versions/{version}`
- Define deterministic error-handling guidance (auth, validation, route constraints, idempotency, pending
  state, terminal non-success state).
- Add explicit downstream integration patterns for:
  - HuleEdu/Skriptoteket thin adapter usage (`scripts/sir_convert_a_lot/integrations/adapter_profiles.py`)
  - Projektveckor backend usage through canonical HTTP v2 contract and mirrored API key policy.
- Link the new contract from active converter docs and relevant runbook sections so downstream teams do not
  reverse-engineer behavior from tests/code.

## Deliverables

- [x] `docs/converters/downstream_integration_contract_v2.md` with frontmatter, normative links, and
  downstream audience framing.
- [x] Required example set (API + CLI + adapter) aligned to active v2 behavior.
- [x] Deterministic error and lifecycle guidance for polling/result/artifact/cancel flows.
- [x] Explicit template discovery + selection guidance for DOCX outputs.
- [x] Cross-links added from:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Acceptance Criteria

- [x] Downstream teams can implement conversion GUI flows without reverse-engineering backend assumptions.
- [x] Contract is explicitly v2-only and does not reintroduce v1 coexistence language.
- [x] Contract covers Markdown ingress pathways (`pdf/docx/html -> md`) and template-selected DOCX flows.
- [x] Every normative behavior statement in the new contract is linked to at least one active source doc
  and at least one active test file.
- [x] Projektveckor integration lane is documented with the same API invariants and secret-mirroring policy
  used by HuleEdu/Skriptoteket.
- [x] Story 11 downstream integration acceptance remains traceable via linked examples and evidence.

## Sequencing and Dependencies

1. This is `T10` in Epic 05 and should be completed before Story 12 cleanup tasks (`T11-T12`).
1. Task 52 output is an explicit replacement target for legacy adapter/v1 docs that Task 51 purges.
1. Contract examples must stay aligned with already shipped route slices:
   - Task 44 (`pdf -> md` v2 lock + v1 absence),
   - Task 48 (`docx -> md`),
   - Task 49 (`html -> md` with resources).

## Execution Plan (Slice 52A, 2026-02-28)

1. Establish canonical contract location and authority.
1. Create `docs/converters/downstream_integration_contract_v2.md` as the downstream integrator-facing
   contract and keep service API v2 doc as transport/schema authority.
1. Define the contract structure (required sections):
   - Purpose and audience (Skriptoteket, HuleEdu, Projektveckor backend integrators).
   - Contract authority and version policy (v2-only, links to API/CLI/template docs).
   - Route capability matrix (implemented routes and route-specific constraints).
   - Submission contract (`X-API-Key`, `Idempotency-Key`, `X-Correlation-ID`, multipart fields).
   - Lifecycle contract (create/poll/result/artifact/cancel with status matrix).
   - Template discovery and selector contract (`/v2/templates/docx*`, selector semantics).
   - Error contract (standard envelope + deterministic code families and downstream UX guidance).
   - CLI parity contract (`convert-a-lot routes`, `--dry-run`, manifest fields).
   - Adapter contract for HuleEdu/Skriptoteket and Projektveckor integration notes.
   - Evidence matrix (source docs + test files for each section).
1. Add required examples (must be copy-paste ready and source-linked):
   - `POST /v2/convert/jobs` for `pdf -> md` (with `pdf_options` + `execution`).
   - `POST /v2/convert/jobs` for `docx -> md`.
   - `POST /v2/convert/jobs` for `html -> md` with `resources` upload.
   - `GET /v2/templates/docx` + `GET /v2/templates/docx/{template_id}` +
     `GET /v2/templates/docx/{template_id}/versions/{version}`.
   - Template-selected `md -> docx` request using `conversion.template`.
   - Idempotency replay and collision outcomes (`X-Idempotent-Replay: true`, `409` conflict).
   - Pending/failed terminal retrieval behavior (`202` and `409 job_not_succeeded`).
   - CLI route discovery + dry-run outputs for `docx -> md` and `html -> md`.
   - CLI manifest sample entry showing `source_format`, `target_format`, `pipeline_used`, and `job_id`.
   - Adapter usage sample (`prepare_submission` + `submit_pdf_for_profile`) for HuleEdu/Skriptoteket.
   - Projektveckor backend request pattern using canonical v2 headers and mirrored API key.
1. Synchronize existing docs to point at the new downstream contract.
1. Validate with targeted tests and docs-as-code gates.

## Normative Source Set (Must Be Linked in New Contract)

Primary source docs:

- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/docx-template-catalog-contract-v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

Implementation sources for contract precision:

- `scripts/sir_convert_a_lot/domain/specs_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_templates_v2.py`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- `scripts/sir_convert_a_lot/integrations/adapter_profiles.py`

Test evidence set:

- `tests/sir_convert_a_lot/test_api_contract_v2.py`
- `tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py`
- `tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py`
- `tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py`
- `tests/sir_convert_a_lot/test_api_contract_v2_docx_templates.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_templates.py`
- `tests/sir_convert_a_lot/test_http_routes_templates_v2.py`
- `tests/sir_convert_a_lot/test_specs_v2.py`
- `tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py`
- `tests/sir_convert_a_lot/test_cli_v2_routes.py`
- `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

## Validation Commands

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py tests/sir_convert_a_lot/test_api_contract_v2_docx_to_md.py tests/sir_convert_a_lot/test_api_contract_v2_html_to_md.py tests/sir_convert_a_lot/test_api_contract_v2_docx_templates.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_read_cancel.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_templates.py tests/sir_convert_a_lot/test_http_routes_templates_v2.py tests/sir_convert_a_lot/test_specs_v2.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Execution Outcome (Slice 52A, 2026-02-28)

- Published new downstream contract:
  - `docs/converters/downstream_integration_contract_v2.md`
- Added v2-only route/lifecycle/error guidance with copy-paste examples for:
  - `pdf -> md`
  - `docx -> md`
  - `html -> md` (+ `resources`)
  - template-selected `md -> docx`
- Added template discovery and selector contract usage examples:
  - `/v2/templates/docx`
  - `/v2/templates/docx/{template_id}`
  - `/v2/templates/docx/{template_id}/versions/{version}`
- Added idempotency replay/collision and pending/non-success retrieval behavior examples.
- Added CLI parity and manifest field contract section.
- Added adapter integration guidance for HuleEdu/Skriptoteket and explicit Projektveckor HTTP lane
  with mirrored secret policy.
- Wired cross-links from active docs:
  - `docs/converters/multi_format_conversion_service_api_v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

### Validation Evidence

- `pdm run run-local-pdm pytest-root ...` (pass: `91 passed, 3 skipped`)
- `pdm run run-local-pdm validate-tasks` (pass: `Validated 84 backlog files`)
- `pdm run run-local-pdm validate-docs` (pass: `Validated docs=104 rules=9`)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
