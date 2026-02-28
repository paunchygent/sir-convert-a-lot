---
id: review-01-brutal-review-service-api-v2-multi-format-pivot
title: 'Brutal review: service API v2 multi-format pivot'
type: review
status: responded
priority: critical
created: '2026-02-18'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - v2
  - clean-break
  - prototype-to-prod
---
Structured review artifact for implementation or readiness checks.

## Review Scope

- Surfaces reviewed:
  - `scripts/sir_convert_a_lot/interfaces/http_api.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_routes.py`
  - `scripts/sir_convert_a_lot/interfaces/http_client.py`
  - `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
  - `scripts/sir_convert_a_lot/domain/specs.py`
  - `scripts/sir_convert_a_lot/domain/specs_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
  - `scripts/sir_convert_a_lot/infrastructure/resources_zip.py`
  - `scripts/sir_convert_a_lot/README.md`
  - `docs/converters/*.md` (v1/v2 + CLI usage)
  - `docs/reference/ref-html-to-pdf-handout-templates-conversion-capability-matrix-2026-02-18.md`
- Validation evidence captured:
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
  - `pdm run run-local-pdm convert-a-lot routes`
  - `pdm run run-local-pdm convert-a-lot convert --help`

## Findings

### Scope B Exploration Lanes

- Lane A (planning/docs contract): Epic 05 + stories 11/13/14 + tasks 46/47/48/49/52.
- Lane B (runtime/domain): `specs_v2.py` + `v2_conversion_executor.py`.
- Lane C (interface/API): `cli_routes.py` + `multi_format_conversion_service_api_v2.md`.

### Severity-Ordered Findings With Exact Fix Proposals

#### F1 `blocker` Markdown ingress matrix is not implemented on v2

Evidence:
- `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md:37`
- `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md:29`
- `scripts/sir_convert_a_lot/domain/specs_v2.py:118`
- `docs/converters/multi_format_conversion_service_api_v2.md:90`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:69`

Why this matters:
- The required `pdf -> md`, `docx -> md`, `html -> md` pathways are not expressible as first-class v2 routes today.
- Downstream GUIs cannot rely on one stable route graph for markdown ingress.

Exact fix proposal:
1. Extend `SourceFormatV2` and `OutputFormatV2` in `specs_v2.py` to cover DOCX source and MD output.
2. Replace hardcoded `allowed_routes` with a single canonical v2 route registry reused by API docs, CLI route listing, and executor dispatch.
3. Implement executor branches for `pdf -> md`, `docx -> md`, and `html -> md` with deterministic normalization/warnings semantics.
4. Update API v2 route tables and CLI route output to show these as v2-only routes.

Proof requirement:
- Add contract tests for each markdown ingress route across `queued/running/succeeded/failed`.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "v2 and markdown and route"`.

#### F2 `blocker` v2 execution still bridges through v1 job-spec logic

Evidence:
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:21`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:99`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:319`

Why this matters:
- The architecture is not a true clean break while v2 builds a v1 `JobSpec` internally for PDF stage execution.
- Policy/validation drift risk remains because v1 and v2 invariants can diverge.

Exact fix proposal:
1. Introduce v2-native PDF ingress policy validators (backend strategy + acceleration policy) and remove `_validate_*_v1` helpers.
2. Replace `v1_spec` construction with v2-native conversion stage call(s).
3. Delete v1 imports from `v2_conversion_executor.py` and keep only typed v2 surfaces.

Proof requirement:
- Regression tests proving identical behavior for GPU policy violations and unreadable PDFs after v1 dependency removal.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "v2 and pdf and policy"`.

#### F3 `high` DOCX template product contract is incomplete and ambiguous

Evidence:
- `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md:28`
- `docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md:25`
- `scripts/sir_convert_a_lot/domain/specs_v2.py:66`
- `docs/converters/multi_format_conversion_service_api_v2.md:152`

Why this matters:
- Story/task require governed template IDs, versions, status, and metadata, but v2 spec only exposes `reference_docx_filename`.
- The API doc allows implementation-defined reference resolution, which is non-deterministic for productized template usage.

Exact fix proposal:
1. Add a typed selector in `ConversionSpecV2`, e.g. `template: {template_id, version, strict}`.
2. Keep raw `reference_docx` upload as explicit override lane only (optional), with deterministic precedence rules.
3. Replace implementation-defined text with normative selection/precedence/error semantics.
4. Include template provenance in result metadata (`template_id`, `template_version`, `template_sha256`).

Proof requirement:
- Add model validation tests for selector precedence and conflict detection (`template + reference_docx`).
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "template and v2"`.

#### F4 `high` Template API surfaces required by Story 13/Task 47 are missing

Evidence:
- `docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md:25`
- `docs/converters/multi_format_conversion_service_api_v2.md:175`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:111`

Why this matters:
- Downstream apps cannot discover available templates or supported versions through API, forcing hardcoded IDs and brittle releases.

Exact fix proposal:
1. Add `GET /v2/templates` and `GET /v2/templates/{template_id}` with typed payloads.
2. Return domain tags, status, version set, checksum, and compatibility hints for route/output usage.
3. Add deterministic errors: `template_not_found`, `template_inactive`, `template_version_unsupported`.

Proof requirement:
- Contract tests for list/get and unknown/inactive/version-mismatch cases.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "templates and contract"`.

#### F5 `high` Downstream API usability gap for Skriptoteket/Hule/Projektveckor

Evidence:
- `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md:34`
- `docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md:29`
- `scripts/sir_convert_a_lot/application/contracts_v2.py:91`
- `docs/converters/multi_format_conversion_service_api_v2.md:177`

Why this matters:
- Story 11 requires explicit route metadata for orchestration, but response contracts only expose `pipeline_used` string and no explicit route key/capability object.
- There is no capability discovery endpoint for GUIs to drive dynamic forms safely.

Exact fix proposal:
1. Add `GET /v2/capabilities` returning route keys, required fields, optional artifacts/resources, and template support flags.
2. Extend result/job metadata with explicit `route_key` (for example `html_to_md_v2`) and normalized source/target contract hints.
3. Publish task-52 integration examples directly against these endpoints and schema objects.

Proof requirement:
- API contract tests for capability schema stability and route metadata presence.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "capabilities or route_key"`.

#### F6 `medium` Reference DOCX resolution is fail-open and hides configuration errors

Evidence:
- `docs/converters/multi_format_conversion_service_api_v2.md:154`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:89`

Why this matters:
- If `reference_docx_filename` is provided but not found, current code can silently proceed with `None`, producing output without intended styling and no clear error.

Exact fix proposal:
1. Fail with `422 reference_docx_not_found` when a reference filename is declared but cannot be resolved.
2. Make precedence explicit (`template` selection first, override upload second, no implicit fallback).
3. Add warning only when fallback is explicitly requested in spec.

Proof requirement:
- Add tests for missing filename and ambiguous multi-source reference collisions.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "reference_docx"`.

#### F7 `medium` CLI route registry is stale versus v2-only target state

Evidence:
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:38`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:75`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:27`

Why this matters:
- CLI still labels `pdf -> md` as v1 and advertises non-active execution kinds (`LOCAL`, `HYBRID`), while also exposing DOCX source without route coverage.
- This creates operator confusion and drifts from API contract.

Exact fix proposal:
1. Remove stale pipeline kinds or mark them legacy-internal only.
2. Generate CLI route list from canonical v2 route registry to eliminate drift.
3. Ensure all route labels are version-accurate (`v2`) and completeness-checked in tests.

Proof requirement:
- Snapshot tests for `convert-a-lot routes` output matching canonical route matrix.
- Run: `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "cli routes"`.

#### F8 `medium` Contract documents still encode v1/v2 coexistence, weakening clean-break governance

Evidence:
- `docs/converters/multi_format_conversion_service_api_v2.md:25`
- `docs/converters/multi_format_conversion_service_api_v2.md:37`
- `docs/converters/multi_format_conversion_service_api_v2.md:96`

Why this matters:
- Epic 05 is defined as strict v2-only clean break, but normative converter doc still frames v1 as active surface and v2 as draft.

Exact fix proposal:
1. Promote v2 converter contract doc to active and v2-only normative language.
2. Remove coexistence assumptions from v2 doc and archive compatibility policy as historical context only.
3. Add explicit migration note with fixed cutover date and v1 removal statement.

Proof requirement:
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm validate-tasks`

## Scope C Addendum (Ops/Runtime Topology)

Brutal review scope C inspected:

- `compose.yaml`
- `pyproject.toml`
- `scripts/sir_convert_a_lot/service.py`
- `scripts/sir_convert_a_lot/service_eval.py`
- `scripts/devops/dev-compose.sh`
- `scripts/devops/verify-hemma-gpu-runtime.sh`
- `scripts/devops/verify-hemma-v2-conversions.sh`
- `scripts/sir_convert_a_lot/benchmark_scientific_corpus.py`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
- `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`

### Scope C Findings (Severity-Ordered)

#### C1 `blocker` eval removal currently breaks canonical docker-lane GPU verification

Evidence:

- `scripts/devops/verify-hemma-gpu-runtime.sh:31`
- `scripts/devops/verify-hemma-gpu-runtime.sh:66`
- `compose.yaml:54`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md:156`

Why this matters:

- The verifier hard-requires `sir_convert_a_lot_eval` in docker lane today.
- Removing eval topology first will fail ops verification before conversion checks execute.

Exact fix proposal:

1. Make `hemma-verify-gpu-runtime` single-runtime by default.
1. Remove hard check on eval container.
1. Keep optional legacy eval probe only behind explicit opt-in flag during migration.

Proof requirement:

- `pdm run run-local-pdm hemma-verify-gpu-runtime`
- `SIR_CONVERT_A_LOT_VERIFY_LANE=docker pdm run run-local-pdm hemma-verify-gpu-runtime`

#### C2 `blocker` Task 12 benchmark depends on eval endpoint plus CPU-only policy unlock

Evidence:

- `scripts/sir_convert_a_lot/benchmark_scientific_corpus.py:52`
- `scripts/sir_convert_a_lot/benchmark_scientific_corpus.py:81`
- `scripts/sir_convert_a_lot/service_eval.py:33`
- `scripts/sir_convert_a_lot/infrastructure/backend_routing.py:35`
- `scripts/sir_convert_a_lot/infrastructure/backend_routing.py:71`
- `docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md:115`

Why this matters:

- `pymupdf + cpu_only` is currently an evaluation-lane behavior and is blocked in production runtime policy.
- Removing eval without redesigning benchmark mode breaks reproducibility for historical acceptance/evaluation evidence.

Exact fix proposal:

1. Decide explicitly: archive Task 12 dual-lane harness as historical evidence, or redesign benchmark A/B execution without service eval endpoint dependency.
1. Do not delete `service_eval` until benchmark path is reworked and documented.

Proof requirement:

- `pdm run run-local-pdm benchmark:task-12 --api-key "$SIR_CONVERT_A_LOT_API_KEY"`
- Evidence output under `build/benchmarks/task-12-scientific-corpus/` with updated topology notes.

#### C3 `high` test suite locks dual-service topology as required behavior

Evidence:

- `tests/sir_convert_a_lot/test_compose_contract.py:61`
- `tests/sir_convert_a_lot/test_compose_contract.py:175`
- `tests/sir_convert_a_lot/test_service_import_side_effects.py:69`
- `tests/sir_convert_a_lot/test_api_contract_v1.py:734`

Why this matters:

- Single-runtime cleanup will fail CI unless tests migrate in the same sequence.

Exact fix proposal:

1. Rewrite compose/runtime tests to assert one canonical service.
1. Replace `service_eval` import tests with single-entrypoint lifecycle tests.
1. Keep readiness coverage but remove eval-profile assumptions.

Proof requirement:

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_service_import_side_effects.py tests/sir_convert_a_lot/test_api_contract_v1.py`

#### C4 `high` runbook/backlog docs still codify prod/eval as normative runtime

Evidence:

- `docs/runbooks/runbook-hemma-devops-and-gpu.md:124`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md:182`
- `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md:25`
- `docs/backlog/tasks/task-22-docker-compose-service-packaging-and-readiness-gated-startup.md:25`

Why this matters:

- Operators will follow stale instructions post-removal and misdiagnose healthy single-runtime systems as misconfigured.

Exact fix proposal:

1. Rewrite runbook/runtime topology sections to one canonical service.
1. Mark prod/eval architecture references in historical task docs as superseded by Task 50/51 outcomes.

Proof requirement:

- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm validate-tasks`

#### C5 `medium` readiness/app-state semantics keep eval-specific branches after cleanup

Evidence:

- `scripts/sir_convert_a_lot/interfaces/http_app_state.py:73`
- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:104`
- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:123`

Why this matters:

- Even if runtime is single-lane, readiness still carries dead conceptual branches and extra failure modes.

Exact fix proposal:

1. Remove eval-root resolver dependency from active readiness checks.
1. Keep fail-closed revision/profile/data-root checks with single-runtime invariants.

Proof requirement:

- `curl -fsS http://127.0.0.1:8085/readyz`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "readyz"`

#### C6 `medium` ops tooling still depends on v1 endpoints during a v2-only epic

Evidence:

- `scripts/devops/verify-hemma-gpu-runtime.sh:201`
- `scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py:7`

Why this matters:

- Task 50/51 can land while ops scripts remain incompatible with the mandated v2 clean-break sequence.

Exact fix proposal:

1. Move `hemma-verify-gpu-runtime` request path from `/v1/*` to `/v2/*`.
1. Convert v2 smoke verifier to v2-only assertions for markdown routes once implemented.

Proof requirement:

- `pdm run run-local-pdm hemma-verify-v2-conversions`
- Contract tests for verifier helpers against v2 client-only paths.

### Safe Rollout Sequence (Task 50/51)

1. Patch verification scripts first (`hemma-verify-gpu-runtime`, v2 smoke verifier).
1. Resolve Task 12 benchmark dependency decision (archive or redesign eval lane usage).
1. Remove compose eval service/volume and `serve:sir-convert-a-lot-eval`.
1. Remove `service_eval.py` and eval-specific readiness branches.
1. Update tests and runbook/docs in same PR wave.
1. Close with docs/index validators and grep-based stale-path sweeps.

### Required Evidence Commands

```bash
pdm run run-local-pdm dev-config | rg -n "sir_convert_a_lot_eval|8086|SIR_CONVERT_A_LOT_EVAL"
pdm run run-local-pdm dev-start
curl -fsS http://127.0.0.1:8085/readyz
curl -fsS http://127.0.0.1:8085/healthz
pdm run run-local-pdm dev-stop
```

```bash
pdm run run-local-pdm hemma-verify-gpu-runtime
pdm run run-local-pdm hemma-verify-v2-conversions
pdm run run-local-pdm run-hemma --shell 'sudo docker ps --format "{{.Names}}\t{{.Ports}}" | rg "sir_convert_a_lot"'
pdm run run-local-pdm run-hemma -- curl -fsS http://127.0.0.1:28085/readyz
```

```bash
pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_service_import_side_effects.py tests/sir_convert_a_lot/test_api_contract_v1.py
pdm run run-local-pdm validate-tasks
pdm run run-local-pdm validate-docs
pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing
rg -n "service_eval|serve:sir-convert-a-lot-eval|sir_convert_a_lot_eval|28086|8086|SIR_CONVERT_A_LOT_EVAL" docs scripts tests compose.yaml pyproject.toml
```

### Scope A (Code Contracts) Current Pass

#### A1 `blocker` v1 + v2 job routes are both active in the canonical app

Evidence:
- `scripts/sir_convert_a_lot/interfaces/http_api.py:171`
- `scripts/sir_convert_a_lot/interfaces/http_api.py:172`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs.py:92`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:111`

Why this matters:
- Epic-05 mandates a clean break. Registering both routers preserves split-brain API contracts and blocks v1 removal.

Concrete fix:
1. Remove `build_job_router(...)` from `http_api.py`.
1. Delete v1 route module and `/v1/convert/jobs*` contract tests/docs in the same migration slice.
1. Keep only `/v2/convert/jobs*` lifecycle endpoints.

Proof tests/commands:
- Current route graph evidence:
  - `pdm run run-local-pdm python -c "from scripts.sir_convert_a_lot.interfaces.http_api import create_app; app=create_app(); print('\n'.join(sorted({r.path for r in app.routes if r.path.startswith('/v')})))"`
- Post-fix expectation:
  - Command above returns only `/v2/convert/jobs*`.

#### A2 `blocker` CLI still hard-wires `pdf -> md` through v1 client/spec path

Evidence:
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:75`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py:236`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py:242`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py:245`
- `scripts/sir_convert_a_lot/interfaces/http_client.py:209`

Why this matters:
- As long as CLI has a v1-only branch, v1 client and v1 request contract remain required runtime dependencies.

Concrete fix:
1. Route `pdf -> md` through `SirConvertALotClientV2`.
1. Remove `default_job_spec_v1` branch from CLI command flow.
1. Delete v1 client usage from `cli_app.py` and relabel route list as v2-only.

Proof tests/commands:
- Current behavior evidence:
  - `pdm run run-local-pdm convert-a-lot routes`
  - `pdm run run-local-pdm convert-a-lot convert --help`
- Post-fix expectation:
  - No `v1` route/help text and no v1 client import path in `cli_app.py`.

#### A3 `blocker` v2 spec cannot represent required Markdown-target routes

Evidence:
- `scripts/sir_convert_a_lot/domain/specs_v2.py:36`
- `scripts/sir_convert_a_lot/domain/specs_v2.py:44`
- `scripts/sir_convert_a_lot/domain/specs_v2.py:118`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:96`

Why this matters:
- `OutputFormatV2` excludes `md` and `SourceFormatV2` excludes `docx`, making `docx -> md`, `html -> md`, and `pdf -> md` impossible under v2.

Concrete fix:
1. Add `DOCX` to `SourceFormatV2` and `MD` to `OutputFormatV2`.
1. Expand `allowed_routes` in `JobSpecV2` validator for all required `* -> md` routes.
1. Extend upload format inference/content-type mapping for DOCX and Markdown outputs.

Proof tests/commands:
- Current enum evidence:
  - `pdm run run-local-pdm python -c "from scripts.sir_convert_a_lot.domain.specs_v2 import SourceFormatV2, OutputFormatV2; print('source_formats=', [v.value for v in SourceFormatV2]); print('output_formats=', [v.value for v in OutputFormatV2])"`
- Current validation rejection evidence:
  - `pdm run run-local-pdm python - <<'PY'\nfrom pydantic import ValidationError\nfrom scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2\nspec={\"api_version\":\"v2\",\"source\":{\"kind\":\"upload\",\"filename\":\"x.html\",\"format\":\"html\"},\"conversion\":{\"output_format\":\"md\",\"css_filenames\":[],\"reference_docx_filename\":None},\"retention\":{\"pin\":False}}\ntry:\n  JobSpecV2.model_validate(spec)\n  print(\"accepted\")\nexcept ValidationError as exc:\n  print(\"rejected\", exc.errors()[0][\"msg\"])\nPY`

#### A4 `blocker` v2 executor still constructs a synthetic v1 job spec and runs v1 conversion entrypoint

Evidence:
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:319`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:320`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:349`

Why this matters:
- This is a direct clean-break blocker: removing v1 contract/executor code would break v2 PDF-source conversion.

Concrete fix:
1. Extract shared PDF-stage validation/execution primitives into version-agnostic modules.
1. Replace synthetic `JobSpec(api_version="v1")` construction with v2-native stage config.
1. Remove direct dependency on v1 `execute_job_conversion(...)`.

Proof tests/commands:
- Current coupling evidence:
  - `rg -n "api_version=\"v1\"|execute_job_conversion\\(" scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
- Post-fix expectation:
  - No `api_version=\"v1\"` usage in v2 executor.

#### A5 `high` v2 stack still imports v1 domain module as a foundational dependency

Evidence:
- `scripts/sir_convert_a_lot/domain/specs_v2.py:20`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py:37`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2.py:28`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py:25`
- `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py:22`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:21`

Why this matters:
- Deleting `domain/specs.py` (required by v1 removal) currently breaks v2 code paths immediately.

Concrete fix:
1. Move shared enums/status primitives into a version-agnostic module (for example `domain/specs_shared.py`).
1. Migrate all v2 imports to shared primitives.
1. Keep v1-only models isolated for deletion.

Proof tests/commands:
- Import graph evidence:
  - `rg -n "from scripts\\.sir_convert_a_lot\\.domain\\.specs import" scripts/sir_convert_a_lot/domain/specs_v2.py scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py scripts/sir_convert_a_lot/interfaces/http_client_v2.py scripts/sir_convert_a_lot/interfaces/cli_app.py scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`

#### A6 `high` v2 HTTP client depends on v1 HTTP client module for error type

Evidence:
- `scripts/sir_convert_a_lot/interfaces/http_client_v2.py:29`

Why this matters:
- Removing `http_client.py` as part of v1 clean-break breaks `http_client_v2.py` because `ClientError` is imported from v1 module.

Concrete fix:
1. Extract `ClientError` into a shared `interfaces/http_client_errors.py`.
1. Update both clients to import from shared error module.
1. Delete v1 client after CLI migration completes.

Proof tests/commands:
- Coupling evidence:
  - `rg -n "from scripts\\.sir_convert_a_lot\\.interfaces\\.http_client import ClientError" scripts/sir_convert_a_lot/interfaces/http_client_v2.py`

#### A7 `high` CLI route matrix remains incomplete for required Markdown ingress contract

Evidence:
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:69`
- `scripts/sir_convert_a_lot/interfaces/cli_routes.py:112`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py:81`
- `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py:224`

Why this matters:
- Downstream API-driven GUIs cannot depend on CLI/API parity while `html -> md` and `docx -> md` are absent from route registry and runtime dispatch.

Concrete fix:
1. Add `html -> md`, `docx -> md`, and `pdf -> md (v2)` to canonical route registry.
1. Update CLI help/defaults and route resolution to use this canonical matrix.
1. Add route completeness tests asserting parity between specs, executor branches, and CLI list output.

Proof tests/commands:
- Current matrix evidence:
  - `pdm run run-local-pdm convert-a-lot routes`
- Current executor branch evidence:
  - `rg -n "job\\.source_format == SourceFormatV2" scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`

#### A8 `medium` `http_api.py` still describes/versions the service as v1-first

Evidence:
- `scripts/sir_convert_a_lot/interfaces/http_api.py:5`
- `scripts/sir_convert_a_lot/interfaces/http_api.py:79`
- `scripts/sir_convert_a_lot/interfaces/http_api.py:108`
- `scripts/sir_convert_a_lot/interfaces/http_api.py:143`

Why this matters:
- v1-first framing and path-based fallback error-version branching create contract ambiguity during the v2-only cutover.

Concrete fix:
1. Update app metadata/docstrings to v2-only semantics.
1. Remove path-based `v1` fallback envelope logic once v1 routes are deleted.
1. Set service version metadata to v2 baseline.

Proof tests/commands:
- Metadata/fallback evidence:
  - `rg -n "v1 API|version=\"1\\.0\\.0\"|api_version = \"v2\" if request\\.url\\.path\\.startswith\\(\"/v2/\"\\) else \"v1\"" scripts/sir_convert_a_lot/interfaces/http_api.py`

## Decision

Decision: `changes_requested`.

Mandatory close-out requirements:

1. Full clean break to v2. Remove v1 service/API/client/code/docs surface entirely; no deprecation bridge.
1. Introduce a complete DOCX template model (catalog + selection + validation) that supports multiple useful reference templates.
1. Add and harden all required routes to Markdown (`docx -> md`, `html -> md`, and `pdf -> md` under v2).
1. Make API routes explicit and GUI-friendly for downstream domains (Skriptoteket, HuleEdu, Projektveckor).
1. Remove legacy/conflicting paths and docs, including eval container topology.
1. Deliver as a prototype-to-prod execution track with one epic, linked stories, and PR-sized tasks.

## Response

Accepted in full. This review now sets the normative execution direction for a v2-only hardened core.

Prototype-to-prod planning has been scaffolded and linked:

- Epic:
  - `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
- Stories:
  - `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
  - `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
  - `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
  - `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
- Tasks:
  - `docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md`
  - `docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md`
  - `docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md`
  - `docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md`
  - `docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md`
  - `docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md`
  - `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
  - `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`
  - `docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md`

Prior recommendations from this review are integrated into the above task set: single route contract, route-aware option semantics, manifest hardening, template governance, and stale-path removal.

## Follow-up Actions

1. `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
1. `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
1. `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
1. `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
1. `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
1. `docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md`
1. `docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md`
1. `docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md`
1. `docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md`
1. `docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md`
1. `docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md`
1. `docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md`
1. `docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md`
1. `docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md`

## Completion

Status lifecycle for this review:

- `pending`: findings recorded; response pending.
- `responded`: owner directive accepted and tracked via epic/stories/tasks.
- `completed`: all linked mandatory tasks are complete with validation evidence and docs/rules sync.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [ ] Review closed
