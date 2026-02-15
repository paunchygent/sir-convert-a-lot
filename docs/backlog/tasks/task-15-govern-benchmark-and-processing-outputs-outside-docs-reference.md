---
id: task-15-govern-benchmark-and-processing-outputs-outside-docs-reference
title: govern benchmark and processing outputs outside docs reference
type: task
status: completed
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md
labels:
  - governance
  - outputs
  - benchmark
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Establish a deterministic output-governance model so benchmark/test/evaluation artifacts and runtime
processing outputs are written outside `docs/reference`, while `docs/reference` is reserved for
curated documentation.

## PR Scope

- Move generated benchmark defaults to `build/` paths (already gitignored).
- Enforce output policy in benchmark code paths (reject generated outputs targeting
  `docs/reference`).
- Update docs/contracts so output location policy is explicit and replayable.
- Remove tracked generated Task 12 artifact files from `docs/reference/artifacts/`.
- Keep machine-readable + human-readable benchmark outputs available as generated artifacts under
  `build/` and publish-to-docs only by explicit manual curation.

## Deliverables

- [x] Output location policy documented (benchmark/eval/runtime categories).
- [x] Programmatic output-path guard prevents generated output under `docs/reference`.
- [x] Task 12 + Story 003b benchmark defaults write to `build/`.
- [x] Tracked generated Task 12 artifacts removed from `docs/reference/artifacts/`.
- [x] Tests and docs references updated for new defaults and policy.

## Acceptance Criteria

- [x] `benchmark:task-12` default outputs no longer target `docs/reference`.
- [x] `benchmark:story-003b` default outputs no longer target `docs/reference`.
- [x] Benchmark runners fail fast if generated output paths target `docs/reference`.
- [x] `docs/reference` no longer stores high-churn generated benchmark/test artifacts.
- [x] Runtime processing output policy remains deterministic (`CONVERTER_STORAGE_ROOT` /
  `SIR_CONVERT_A_LOT_DATA_DIR` under `build/` by default).
- [x] Docs and quality gates pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_benchmark_scientific_corpus.py tests/sir_convert_a_lot/test_benchmark_gpu_governance.py -q`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
