# Session Handoff

## 2026-02-15: Task 12 In Progress (Scientific Corpus Evidence Run Executed)

### Completed This Slice

- Ran dual-lane Task 12 benchmark after Task 13 runtime gate validation:
  - `pdm run run-local-pdm benchmark:task-12 --api-key dev-only-key`
- Hemma lane topology was active during run:
  - production-lock service: `127.0.0.1:28085`
  - eval service: `127.0.0.1:28086`
- Generated evidence artifacts:
  - `docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json`
  - `docs/reference/ref-production-pdf-md-scientific-corpus-validation.md`
  - `docs/reference/artifacts/task-12-scientific-corpus/` (acceptance + docling + pymupdf markdown/meta)
- Run outcome:
  - acceptance lane: `10/10` succeeded
  - decision quality winner: `pymupdf`
  - governance-compatible production recommendation: `docling`

### Validation Evidence (local)

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass; 87 passed)

### Remaining for Task 12 Close-Out

- Complete manual quality review pass for generated markdown outputs, then close Task 12.

## 2026-02-15: Task 13 Completed (GPU Runtime Compliance Gate + Hemma ROCm Verification)

### Completed

- Created and activated Task 13:
  - `docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md`
- Added typed GPU runtime probe:
  - `scripts/sir_convert_a_lot/infrastructure/gpu_runtime_probe.py`
- Enforced fail-closed Docling behavior when GPU runtime probe is unavailable:
  - `scripts/sir_convert_a_lot/infrastructure/conversion_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Added deterministic error mapping:
  - `503 gpu_not_available` with
    `details.reason="backend_gpu_runtime_unavailable"` and runtime probe fields.
- Added Hemma operational scripts + PDM surfaces:
  - `scripts/devops/verify-hemma-gpu-runtime.sh`
  - `scripts/devops/repair-hemma-rocm-runtime.sh`
  - `pyproject.toml` scripts:
    - `hemma-verify-gpu-runtime`
    - `hemma-repair-rocm-runtime`
- Added deterministic ROCm torch pins in project config:
  - `pyproject.toml` (`tool.sir_convert_a_lot.rocm_runtime`)
  - `torch_index_url=https://download.pytorch.org/whl/rocm7.1`
  - `torch==2.10.0+rocm7.1`
  - `torchvision==0.25.0+rocm7.1`
  - `torchaudio==2.10.0+rocm7.1`
- Updated docs and active context:
  - `docs/backlog/current.md`
  - `docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md`
  - `docs/converters/pdf_to_md_service_api_v1.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`

### Test Coverage Added/Updated

- Added:
  - `tests/sir_convert_a_lot/test_gpu_runtime_probe.py`
- Updated:
  - `tests/sir_convert_a_lot/test_docling_backend.py`
  - `tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_benchmark_scientific_corpus.py`
  - supporting test configuration updates in:
    - `tests/sir_convert_a_lot/test_benchmark_gpu_governance.py`
    - `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`
    - `tests/sir_convert_a_lot/test_job_store_persistence.py`

### Validation Evidence (local)

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass; 87 passed)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Hemma Verification Status

- Completed on patched `main` revision:
  - local commit + push: `6ee1a27`
  - remote sync: `pdm run run-local-pdm run-hemma -- git pull --ff-only`
- Runtime repair + verification evidence:
  - `pdm run run-local-pdm hemma-repair-rocm-runtime`
  - `pdm run run-local-pdm hemma-verify-gpu-runtime`
  - probe output confirms ROCm runtime:
    - `{"runtime_kind":"rocm","torch_version":"2.10.0+rocm7.1","hip_version":"7.1.25424","device_name":"AMD Radeon AI PRO R9700","is_available":true}`
  - live conversion output confirms GPU execution:
    - `{"acceleration_used":"cuda","gpu_busy_peak":97,...}`
- Service availability note:
  - verification requires service listener on `127.0.0.1:28085`; started via uvicorn on Hemma
    before the successful verification run.

## 2026-02-14: Task 11 Completed (PyMuPDF Backend + Compatibility Governance)

### Completed

- Closed Task 11 as `completed`:
  - `docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md`
- Added PyMuPDF backend implementation:
  - `scripts/sir_convert_a_lot/infrastructure/pymupdf_backend.py`
- Updated runtime routing and compatibility validation:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Updated tests for Task 11 behavior:
  - `tests/sir_convert_a_lot/test_pymupdf_backend.py`
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`
- Updated docs/context:
  - `docs/converters/pdf_to_md_service_api_v1.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `scripts/sir_convert_a_lot/README.md`
  - `docs/backlog/current.md`

### Locked Behavior

- `backend_strategy="auto"` remains Docling-first.
- PyMuPDF path is explicit-only (`backend_strategy="pymupdf"`).
- `pymupdf` compatibility constraints:
  - `ocr_mode` must be `off`,
  - `acceleration_policy in {"gpu_required","gpu_prefer"}` rejects with deterministic `422 validation_error`.

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass; 66 passed)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## 2026-02-14: Task 10 Completed (Docling Backend + Deterministic Normalization)

### Completed

- Closed Task 10 as `completed`:
  - `docs/backlog/tasks/task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100.md`
- Delivered Docling-first conversion seam and deterministic normalization stack:
  - `scripts/sir_convert_a_lot/infrastructure/conversion_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/docling_backend.py`
  - `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
  - `scripts/sir_convert_a_lot/interfaces/http_api.py`
- Persisted conversion metadata truth updates in durable store:
  - `scripts/sir_convert_a_lot/infrastructure/job_store.py`
  - `scripts/sir_convert_a_lot/infrastructure/job_store_models.py`
- Added Task 10 test coverage and fixture helpers:
  - `tests/sir_convert_a_lot/test_docling_backend.py`
  - `tests/sir_convert_a_lot/test_markdown_normalizer.py`
  - `tests/sir_convert_a_lot/pdf_fixtures.py`
  - Updated API/runtime/integration/benchmark tests to valid fixture PDFs.
- Updated user/contract documentation:
  - `docs/converters/pdf_to_md_service_api_v1.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `scripts/sir_convert_a_lot/README.md`

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass; 39 passed)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Notes

- The 12 warning events observed during tests were traced to a Docling deprecation warning in
  `standard_pdf_pipeline.py`; conversion call-site filtering now removes this third-party noise
  without suppressing unrelated warnings.

## 2026-02-14: Story 02-01 Activated (Production-Ready PDF->MD + Deterministic Line Breaks)

### Decision

- Story 02-01 is now `in_progress` to replace the runtime conversion stub with a production-grade,
  restart-durable, long-running conversion pipeline.
- Markdown output determinism includes deterministic, readable line breaks:
  - `conversion.normalize="strict"` is strong reflow at width 100 (Markdown-safe; no reflow inside fences/tables/headings).

### Docs-As-Code Updates

- Story activated:
  - `docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md`
- New PR-sized tasks created:
  - `docs/backlog/tasks/task-09-durable-filesystem-job-store-restart-recovery-retention-sweeper-story-02-01.md`
  - `docs/backlog/tasks/task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100.md`
  - `docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md`
  - `docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md`
- Acceptance gate corpus path (external, not vendored):
  - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`

### Next Focus

- Implement Task 09 first (durable job store + restart recovery + retention).
- Then implement conversion backends + normalization, and finally capture Hemma tunnel evidence (10/10).

## 2026-02-11: Story 003c Closure Gate Updated (HuleEdu Required)

### Decision

- Story 003c cannot be closed without HuleEdu adoption evidence.
- Evidence must include real, demanding scientific-paper PDF workload validation and ease-of-use confirmation.

### Docs-As-Code Updates

- New active task:
  - `docs/backlog/tasks/task-08-adopt-story-003c-thin-adapter-in-huleedu-and-validate-demanding-scientific-pdf-workload.md`
- Default corpus path locked for workload validation:
  - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- Story criteria strengthened:
  - `docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md`
- Consumer handoff closure gate added:
  - `docs/reference/ref-story-003c-consumer-integration-handoff.md`
- Active context updated:
  - `docs/backlog/current.md`

### Next Focus

- Execute Task 08 in HuleEdu repo and capture demanding scientific-paper workload evidence.
- Use Task 08 evidence to drive Story 003c final close-out decision.

## 2026-02-11: Task 07 Execution + Governance Refinement

### Completed

- Executed Task 07 and closed it as completed:
  - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`
- Confirmed canonical Hemma repo placement under `~/apps`:
  - `/home/paunchygent/apps/sir-convert-a-lot`
- Captured successful tunnel smoke evidence:
  - `http://127.0.0.1:28085/healthz` -> `200 {"status":"ok"}`
  - Adapter smoke (`submit -> poll -> result`) succeeded with
    `job_0b5fa957472441f597883644d3`.
- Updated Story 003c consumer handoff reference to remove stale failure caveat:
  - `docs/reference/ref-story-003c-consumer-integration-handoff.md`

### Lessons Learned Applied

- Runbook update:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - Added explicit `~/apps` repo placement policy + migration/verification steps.
- Skill update:
  - `.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
  - Added mandatory first-step path guard and bootstrap commands.
- Rule update:
  - `.agents/rules/030-conversion-workflows.md`
  - Added Hemma repo placement invariant for operational workflows.

### Next Focus

- Determine whether Story 003c is ready for closure now that Task 06 and Task 07 are both complete.
- If yes, update story/epic/programme checklists and close docs-as-code loop.

## 2026-02-11: Commit/Push and Task 07 Planning Kickoff

### Completed

- Committed and pushed consolidated changes on `main`:
  - Commit: `8c5bd46`
  - Push target: `origin/main`
- Activated Task 07 planning:
  - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`
  - Status updated to `in_progress`
  - Added baseline context, execution plan, command plan, and risk mitigations.

### Validation Evidence

- `pdm run run-local-pdm typecheck-all --no-incremental` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Focus

- Execute Task 07 operational steps on Hemma to obtain successful tunnel smoke evidence.
- Update Story 003c reference docs with successful `health + submit/poll/result` transcript.

## 2026-02-11: Story 003c Docs-As-Code Synchronization

### Completed

- Filled previously placeholder Story 003c docs with state-accurate content:
  - `docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md`
  - `docs/converters/internal_adapter_contract_v1.md`
  - `docs/reference/ref-story-003c-consumer-integration-handoff.md`
- Updated Story 003c tracking state:
  - `docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md` -> `status: in_progress`
- Updated active context log:
  - `docs/backlog/current.md`

### Validation Evidence

- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Follow-Up Alignment

- `docs/backlog/epics/epic-03-unified-conversion-service.md` updated from
  `status: proposed` to `status: in_progress` after docs audit.
- `docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md`
  updated to `status: completed` after recording executed Hemma/tunnel smoke evidence and
  splitting operational readiness into follow-up task:
  `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`.

### Next Focus

- Capture Story 003c tunnel/Hemma smoke evidence and add it to the task/reference docs.
- Execute consumer-repo adoption work using the published adapter contract and handoff checklist.

## 2026-02-11: Fix-01 CLI Timeout Hardening for Background Jobs

### Completed

- Implemented timeout hardening in `scripts/sir_convert_a_lot/interfaces/cli_app.py`:
  - `job_timeout` is now treated as `running` when `job_id` exists.
  - Manifest entry is preserved for async follow-up (`status`, `job_id`, `error_code`).
  - CLI exits successfully when outcomes are timeout-only (no terminal failures).
- Added regression coverage in `tests/sir_convert_a_lot/test_convert_a_lot_cli.py`:
  - `test_convert_command_timeout_marks_job_running_without_cli_failure`
- Updated user/operator docs:
  - `docs/converters/sir_convert_a_lot.md`
  - `scripts/sir_convert_a_lot/README.md`
- Logged docs-as-code fix artifact:
  - `docs/backlog/tasks/fix-01-harden-cli-timeout-handling-for-long-running-background-jobs.md`

### Validation Evidence

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run mypy --config-file pyproject.toml --no-incremental` (pass)
- `pdm run run-local-pdm typecheck-all --no-incremental` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

### Next Focus

- Continue Story 003c thin adapter execution from the current scaffold, keeping conformance harness as the primary acceptance gate.
- Preserve the new CLI timeout semantics as canonical behavior unless contract docs are explicitly revised.

## 2026-02-11: Story 004 Closure and Story 003b Completion

### Completed

- Closed Story 004 bootstrap/governance items:
  - `docs/backlog/tasks/task-04-03-migrate-canonical-converter-code-and-quality-gates.md`
  - `docs/backlog/tasks/task-04-04-prepare-docker-hemma-service-foundation.md`
  - `docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md`
- Opened Story 003b execution task:
  - `docs/backlog/tasks/task-05-enforce-gpu-first-lock-and-benchmark-evidence-for-story-003b.md`
- Completed Story 003b governance implementation:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_runtime_engine_gpu_policy.py`
  - `tests/sir_convert_a_lot/test_benchmark_gpu_governance.py`
  - `scripts/sir_convert_a_lot/benchmark_gpu_governance.py`
  - `docs/reference/benchmark-story-003b-gpu-governance-local.json`
  - `docs/reference/ref-story-003b-gpu-governance-benchmark-evidence.md`
- Validation evidence for bootstrap close-out:
  - `pdm run run-local-pdm lint`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
- Validation evidence for Story 003b completion:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Next Focus

- Start Story 003c implementation planning/tasking for internal HuleEdu/Skriptoteket integration.
- Preserve Story 003b governance lock behavior unless ADR updates explicitly authorize change.
- Keep benchmark runner and corpus as the baseline evidence tool for future policy checks.
