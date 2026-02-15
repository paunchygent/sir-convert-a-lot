---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-02-15'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100.md
  - docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md
  - docs/backlog/tasks/task-14-enforce-global-docling-gpu-only-invariant-and-remove-cpu-execution-paths.md
labels:
  - session-log
  - active-work
---

## Context

Active focus is Story 02-01 execution:

- Task 10 is completed (Docling backend + OCR policy mapping + deterministic markdown normalization).
- Task 11 is completed (PyMuPDF backend + deterministic compatibility governance).
- Task 12 is in progress (scientific-paper workload evidence harness + Hemma report).
- Task 13 is completed (GPU runtime compliance gate + ROCm verification/remediation).
- Task 14 is completed (strict global Docling GPU-only invariant enforcement).

## Worklog

- 2026-02-15 — Task 14 activated for strict global Docling GPU-only invariant:
  - Created and moved to `in_progress`:
    - `docs/backlog/tasks/task-14-enforce-global-docling-gpu-only-invariant-and-remove-cpu-execution-paths.md`
  - Locked scope:
    - remove all successful Docling CPU execution paths (service + direct backend + tests),
    - preserve deterministic `503 gpu_not_available` behavior when runtime probe fails.
- 2026-02-15 — Task 14 completed:
  - `DoclingConversionBackend` now rejects CPU execution unconditionally and requires a
    usable ROCm/CUDA probe result.
  - Added regression coverage for strict invariant (`gpu_available=False` still fail-closed or
    reports `acceleration_used="cuda"` when runtime is available).
  - Updated API/integration benchmark tests to remove Docling CPU assumptions and
    mark real Docling success-path tests as GPU-runtime-required.
- 2026-02-15 — Task 12 benchmark evidence run executed after Task 13 runtime gate close-out:
  - Hemma services confirmed on `127.0.0.1:28085` (prod-lock) and `127.0.0.1:28086` (eval).
  - Tunnel flow validated for both lanes (`/healthz` pass on local forwarded ports).
  - Ran:
    - `pdm run run-local-pdm benchmark:task-12 --api-key dev-only-key`
  - Result:
    - acceptance lane: `10/10` succeeded
    - quality winner: `pymupdf`
    - governance-compatible production recommendation: `docling`
  - Artifacts generated:
    - `docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json`
    - `docs/reference/ref-production-pdf-md-scientific-corpus-validation.md`
    - `docs/reference/artifacts/task-12-scientific-corpus/`
  - Artifacts committed on `main`:
    - `e19ec82` (`Add Task 12 scientific corpus evidence artifacts and run report`)
  - Remaining Task 12 close-out:
    - manual quality review completion for all generated markdown outputs.
- 2026-02-15 — Task 13 completed with runtime-gated Hemma evidence on patched revision:
  - Main branch commit and push:
    - `6ee1a27` (`Enforce GPU runtime compliance gate and pin ROCm torch runtime`)
  - Hemma fast-forward sync:
    - `pdm run run-local-pdm run-hemma -- git pull --ff-only`
  - Deterministic runtime verification pass:
    - `pdm run run-local-pdm hemma-verify-gpu-runtime`
    - probe evidence: `runtime_kind=rocm`, `torch_version=2.10.0+rocm7.1`,
      `device_name=AMD Radeon AI PRO R9700`
    - live conversion evidence: `acceleration_used="cuda"`, `gpu_busy_peak=97`
- 2026-02-15 — Task 13 moved to `in_progress` to unblock Task 12 with a fail-closed GPU
  runtime compliance gate:
  - Created and activated:
    - `docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md`
  - Locked implementation slices:
    - typed GPU runtime probe in infrastructure,
    - deterministic `503 gpu_not_available` mapping for backend GPU-runtime unavailability,
    - Hemma verify/repair script surfaces and runbook updates.
- 2026-02-14 — Task 12 moved to `in_progress` with decision-locked execution:
  - Added dual-lane topology lock (acceptance + evaluation A/B) to:
    - `docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md`
  - Locked quality-first ranking and artifact policy for backend selection.
  - Added execution plan/checklist scope for harness, eval profile, evidence outputs, and close-out docs.
- 2026-02-11 — Bootstrapped standalone repo structure (`.agents/`, `docs/`, canonical scripts, service/tests/docs migration).
- 2026-02-11 — Added Sir Convert-a-Lot v1 service surfaces and DDD-oriented module split.
- 2026-02-11 — Created Programme 001 and setup story/tasks (004–007) to enforce planning hierarchy.
- 2026-02-11 — Added docs contract metadata (`docs/_meta/docs-contract.yaml`) and upgraded validator to enforce YAML frontmatter for docs and rules.
- 2026-02-11 — Added repo-specific Hemma/GPU runbook (`docs/runbooks/runbook-hemma-devops-and-gpu.md`) and DevOps skill (`.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`).
- 2026-02-11 — Added Skriptoteket/HuleEdu-style wrapper scripts:
  - `pdm run run-local-pdm`
  - `pdm run run-hemma`
- 2026-02-11 — Passed full quality and docs gates:
  - `pdm run format-all`
  - `pdm run lint`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
- 2026-02-11 — Closed Story 004 bootstrap/governance execution:
  - `docs/backlog/tasks/task-04-03-migrate-canonical-converter-code-and-quality-gates.md`
  - `docs/backlog/tasks/task-04-04-prepare-docker-hemma-service-foundation.md`
  - `docs/backlog/stories/story-04-01-standalone-repo-bootstrap-and-governance-setup.md`
- 2026-02-11 — Opened Story 003b execution task:
  - `docs/backlog/tasks/task-05-enforce-gpu-first-lock-and-benchmark-evidence-for-story-003b.md`
- 2026-02-11 — Completed Story 003b implementation and evidence capture:
  - Runtime policy lock hardening (`runtime_engine.py`) with env unlock rejection.
  - Expanded API/runtime policy tests and benchmark runner tests.
  - Benchmark corpus added under `tests/fixtures/benchmark_pdfs/`.
  - Benchmark artifacts:
    - `docs/reference/benchmark-story-003b-gpu-governance-local.json`
    - `docs/reference/ref-story-003b-gpu-governance-benchmark-evidence.md`
- 2026-02-11 — Story 003b validation and docs gates passed:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- 2026-02-11 — Completed fix `fix-01-harden-cli-timeout-handling-for-long-running-background-jobs`:
  - CLI timeout hardening in `scripts/sir_convert_a_lot/interfaces/cli_app.py`:
    - `ClientError(code="job_timeout")` now records manifest `status: running` with `job_id`.
    - CLI no longer exits non-zero for timeout-only outcomes.
  - Added regression test:
    - `tests/sir_convert_a_lot/test_convert_a_lot_cli.py::test_convert_command_timeout_marks_job_running_without_cli_failure`
  - Updated operator/user docs:
    - `docs/converters/sir_convert_a_lot.md`
    - `scripts/sir_convert_a_lot/README.md`
  - Validation gates run for this fix:
    - `pdm run run-local-pdm format-all`
    - `pdm run run-local-pdm lint-fix`
    - `pdm run mypy --config-file pyproject.toml --no-incremental`
    - `pdm run run-local-pdm typecheck-all --no-incremental`
    - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
    - `pdm run run-local-pdm validate-tasks`
    - `pdm run run-local-pdm validate-docs`
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- 2026-02-11 — Story 003c docs-as-code synchronization completed for active slice:
  - Task details hardened in:
    - `docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md`
  - Normative contract published in:
    - `docs/converters/internal_adapter_contract_v1.md`
  - Consumer handoff reference completed in:
    - `docs/reference/ref-story-003c-consumer-integration-handoff.md`
  - Story state moved to `in_progress`:
    - `docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md`
- 2026-02-11 — Backlog metadata alignment after docs audit:
  - `docs/backlog/epics/epic-03-unified-conversion-service.md` moved to `status: in_progress`
    to reflect Story 003a/003b completion and active Story 003c execution.
- 2026-02-11 — Story 003c Task 06 closed with operational follow-up split:
  - `docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md`
    moved to `status: completed` after documenting executed Hemma/tunnel smoke evidence.
  - Follow-up operational task created:
    - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`
  - Story 003c remains `in_progress` pending successful Hemma deployment/tunnel smoke outcome.
- 2026-02-11 — Committed and pushed consolidated Story 003c + timeout hardening state:
  - `git commit` -> `8c5bd46` on `main`
  - `git push origin main` completed
- 2026-02-11 — Task 07 planning kickoff completed:
  - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`
    moved to `status: in_progress` with explicit execution plan, command plan, and risks.
- 2026-02-11 — Task 07 executed and completed:
  - Canonical Hemma repo placement established and verified:
    - `/home/paunchygent/apps/sir-convert-a-lot`
  - Remote service bootstrap on `127.0.0.1:28085` succeeded.
  - Tunnel smoke and adapter `submit -> poll -> result` evidence captured successfully.
  - Task closed:
    - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`
  - Story 003c handoff reference updated with successful smoke evidence:
    - `docs/reference/ref-story-003c-consumer-integration-handoff.md`
- 2026-02-11 — Lessons learned distilled into governance artifacts:
  - Runbook refined with explicit `~/apps` repo placement policy and migration guidance:
    - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - Hemma DevOps skill updated with mandatory first-step path guard:
    - `.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
  - Conversion workflow rule updated with Hemma repo placement invariant:
    - `.agents/rules/030-conversion-workflows.md`
- 2026-02-11 — Story 003c closure gate decision updated:
  - HuleEdu adoption is mandatory before Story 003c close-out.
  - New active task created:
    - `docs/backlog/tasks/task-08-adopt-story-003c-thin-adapter-in-huleedu-and-validate-demanding-scientific-pdf-workload.md`
  - Story criteria updated to require demanding scientific-paper workload validation evidence.
  - Default workload corpus path for Task 08 specified:
    - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- 2026-02-14 — Activated Story 02-01 execution slice for production-ready PDF->MD:
  - Story status moved to `in_progress` and wired to new PR-sized tasks (09–12).
  - Locked deterministic Markdown line breaks:
    - `conversion.normalize="strict"` is strong reflow at width 100 (Markdown-safe).
  - Acceptance gate corpus path (external, not vendored):
    - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- 2026-02-14 — Task 09 completed and Task 10 implementation started:
  - Durable filesystem job store + restart recovery + retention sweep behavior closed in Task 09.
  - Task 10 moved to `in_progress` with docs-as-code execution plan.
  - Implementation target locked for this slice:
    - `docling==2.73.1`
    - deterministic OCR auto retry (balanced heuristic)
    - deterministic markdown normalization (`none|standard|strict`, strict width 100)
    - temporary `backend_strategy="pymupdf"` `422 validation_error` until Task 11.
- 2026-02-14 — Task 10 completed and validated:
  - Runtime conversion path refactored to Docling backend seam + deterministic normalizer.
  - API/runtime enforce temporary backend availability guard for `backend_strategy="pymupdf"` (`422 validation_error`).
  - Added/updated Task 10 test coverage with valid checked-in PDF fixtures for conversion-success paths.
  - Resolved 12 runtime warnings from Docling deprecation noise via narrow call-site warning filter.
  - Validation gates passed:
    - `pdm run run-local-pdm format-all`
    - `pdm run run-local-pdm lint-fix`
    - `pdm run run-local-pdm typecheck-all`
    - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
    - `pdm run run-local-pdm validate-tasks`
    - `pdm run run-local-pdm validate-docs`
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- 2026-02-14 — Task 11 moved to `in_progress` with locked implementation plan:
  - Added execution-plan section and compatibility constraints in:
    - `docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md`
  - Locked behavior:
    - `backend_strategy="auto"` remains Docling-first
    - `backend_strategy="pymupdf"` is explicit-only
    - `pymupdf` requires `ocr_mode="off"` and CPU-compatible execution policy
- 2026-02-14 — Task 11 completed and validated:
  - Added PyMuPDF backend and runtime routing/compatibility validation.
  - Added deterministic PyMuPDF backend tests and updated API/runtime compatibility tests.
  - Updated converter/API docs for Task 11 compatibility matrix.
  - Validation gates passed:
    - `pdm run run-local-pdm format-all`
    - `pdm run run-local-pdm lint-fix`
    - `pdm run run-local-pdm typecheck-all`
    - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
    - `pdm run run-local-pdm validate-tasks`
    - `pdm run run-local-pdm validate-docs`
    - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Next Actions

1. Execute Task 12 (scientific-paper workload evidence harness + Hemma 10/10 acceptance report).
1. Continue Task 08 evidence capture in Huledu repo for Story 003c close-out.
