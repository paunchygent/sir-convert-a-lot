---
id: task-286-extract-service-v2-runtime-supervision-telemetry-and-checkpoint-planning-modules
title: Extract service v2 runtime supervision telemetry and checkpoint planning modules
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md
  - docs/backlog/tasks/task-268-preserve-pdf-ocr-checkpoint-resume-metadata-truth.md
  - docs/backlog/tasks/task-269-reconcile-pdf-ocr-metadata-contract-across-docs-runtime-and-tests.md
labels:
  - runtime
  - checkpointing
  - source-simplification
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split the v2 runtime hotspots so worker supervision, telemetry, chunk planning,
and checkpoint state are discoverable bounded modules instead of broad
catch-all responsibilities inside the runtime engine and checkpointed PDF
executor.

## PR Scope

- Extract worker supervision and telemetry responsibilities from
  `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`.
- Extract chunk planning and checkpoint state responsibilities from
  `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`.
- Preserve the existing conversion lifecycle, progress events, checkpoint
  metadata, partial-artifact behavior, and failure semantics.
- Keep the extraction aligned with existing application/domain/infrastructure
  boundaries and use dependency injection where it clarifies composition.
- Avoid adding compatibility shims, `Any`, `typing.cast`, `# type: ignore`, or
  lint ignores to make the split pass.

## Deliverables

- [x] Worker supervision component with focused tests.
- [x] Telemetry/progress component with focused tests or preserved integration
  coverage.
- [x] Chunk planning component separated from checkpoint persistence/state.
- [x] Checkpoint state component with explicit resume/failure behavior.
- [x] Module-size evidence for the touched runtime files and extracted modules.

## Acceptance Criteria

- [x] Externally visible conversion behavior and artifact manifests are
  unchanged for existing service routes.
- [x] `runtime_engine_v2.py` and `v2_pdf_checkpointed_executor.py` no longer
  own unrelated supervision, telemetry, planning, and checkpoint-state logic in
  the same file.
- [x] Touched runtime modules stay under the repo's bounded-module target unless
  a documented exception is carried in the task close-out.
- [x] Focused checkpoint/resume, progress, and failure-path tests pass.
- [x] Full conversion-core gates required by AGENTS run before close-out.

## Implementation Notes

- Extracted runtime scheduling and lifecycle helpers:
  `runtime_supervision_v2.py`, `runtime_capacity_telemetry_v2.py`, and
  `runtime_job_runner_v2.py`.
- Extracted PDF checkpoint helpers:
  `v2_pdf_checkpoint_models.py`, `v2_pdf_checkpoint_planning.py`,
  `v2_pdf_checkpoint_state.py`, `v2_pdf_chunk_conversion.py`, and
  `v2_pdf_checkpoint_chunk_runner.py`.
- Preserved runtime monkeypatch boundaries used by existing tests:
  `runtime_engine_v2.execute_v2_job_conversion`,
  `runtime_engine_v2.start_conversion_heartbeat_v2`, and
  `v2_pdf_checkpointed_executor.execute_job_conversion` remain the patchable
  call sites. The extracted checkpoint chunk runner also receives checkpoint
  persistence and partial-artifact assembly from the parent executor so
  checkpoint-side instrumentation remains observable through the same boundary.

## Module-Size Evidence

- `runtime_engine_v2.py`: 432 LoC.
- `runtime_job_runner_v2.py`: 419 LoC.
- `runtime_capacity_telemetry_v2.py`: 297 LoC.
- `runtime_supervision_v2.py`: 134 LoC.
- `v2_pdf_checkpointed_executor.py`: 341 LoC.
- `v2_pdf_checkpoint_chunk_runner.py`: 344 LoC.
- `v2_pdf_chunk_conversion.py`: 214 LoC.
- `v2_pdf_checkpoint_models.py`: 72 LoC.
- `v2_pdf_checkpoint_planning.py`: 98 LoC.
- `v2_pdf_checkpoint_state.py`: 194 LoC.

## Validation Evidence

- `pdm run format-all` -> 687 files left unchanged after final fix.
- `pdm run lint-fix` -> All checks passed; docs validated as part of the
  command.
- `pdm run typecheck-all` -> Success: no issues found in 638 source files.
- Focused runtime/checkpoint tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_runtime_engine_v2.py tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py tests/sir_convert_a_lot/test_runtime_supervision_v2.py tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_cancel_and_resume.py::test_resume_idempotency_replay_survives_public_key_rotation tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py::test_parallel_api_contract_parity_for_artifact_checkpoint_resume tests/sir_convert_a_lot/test_v2_pdf_checkpoint_planning_and_state.py -q`
  -> 36 passed.
- First `pdm run coverage-gate` caught the extracted chunk runner bypassing the
  parent executor's checkpoint-persistence patch boundary; isolated reruns of
  both affected tests passed after the injected persistence boundary fix.
- Final `pdm run coverage-gate` -> 1152 passed, 5 skipped, total coverage
  96.95%.
- `pdm run docs-sync` -> generated docs indexes refreshed.
- `pdm run docs-validate` -> Validated 363 backlog files; Validated docs=422
  rules=11.
- `pdm run skills-validate` -> ok.
- `pdm run handoff-validate` -> ok.
- `git diff --check` -> clean.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
