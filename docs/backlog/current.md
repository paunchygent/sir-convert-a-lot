---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-02-18'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md
  - docs/backlog/tasks/task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback.md
  - docs/backlog/tasks/task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning.md
  - docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md
  - docs/reference/ref-dockerized-hemma-gpu-passthrough-gap-2026-02-16.md
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/backlog/tasks/task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
labels:
  - session-log
  - active-work
---

## Context

Active focus is now Epic 04: multi-format converter suite parity delivered as a
**service-executed** conversion suite on Hemma via **service API v2**, while
preserving the locked service API v1 contract (`pdf -> md` only).

Epic 04 entrypoint:

- `docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md`

Normative v2 contract doc:

- `docs/converters/multi_format_conversion_service_api_v2.md`

CLI multi-format routing story:

- `docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md`

Story 02-01 tasks remain in progress but are not the active slice:

- `docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md`
- `docs/backlog/tasks/task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback.md`

## Worklog

- 2026-02-18:

  - Created Epic 04 and the initial critical pipeline task set:
    - `docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md`
    - `docs/backlog/tasks/task-31-cli-route-registry-for-local-and-hybrid-conversions.md`
    - `docs/backlog/tasks/task-32-html-css-to-pdf-route-weasyprint-with-deterministic-manifest.md`
    - `docs/backlog/tasks/task-28-markdown-to-pdf-via-html-intermediary-pandoc-weasyprint.md`
    - `docs/backlog/tasks/task-30-markdown-to-docx-via-html-intermediary-pandoc.md`
    - `docs/backlog/tasks/task-29-pdf-to-docx-hybrid-pipeline-service-pdf-md-local-md-html-docx.md`
  - Set YAML frontmatter as canonical student metadata source for feedback exports:
    `docs/backlog/stories/story-10-student-feedback-export-bundles-manifest-md-html-pdf-docx.md`
  - Completed Task 31 (route registry + `routes` + `--dry-run` + docs + tests).
    Local gates passed:
    `format-all`, `lint-fix`, `typecheck-all`, `pytest-root tests/sir_convert_a_lot`,
    `validate-tasks`, `validate-docs`, `index-tasks`.
  - Completed Task 32 (`html + css -> pdf` via local WeasyPrint) and flipped the `html -> pdf`
    CLI route to implemented.
    Local gates passed:
    `format-all`, `lint-fix`, `typecheck-all`, `pytest-root tests/sir_convert_a_lot`,
    `validate-tasks`, `validate-docs`, `index-tasks`.
  - Completed Task 28 (`md -> html -> pdf` via Pandoc + WeasyPrint) and flipped the `md -> pdf`
    CLI route to implemented (with `--keep-html` support).
    Local gates passed:
    `format-all`, `lint-fix`, `typecheck-all`, `pytest-root tests/sir_convert_a_lot`,
    `validate-tasks`, `validate-docs`, `index-tasks`.
    - Completed Task 30 (`md -> html -> docx` via Pandoc + Pandoc) and flipped the `md -> docx`
      CLI route to implemented (with `--reference-docx` and `--keep-html` support).
      Local gates passed:
      `format-all`, `lint-fix`, `typecheck-all`, `pytest-root tests/sir_convert_a_lot`,
      `validate-tasks`, `validate-docs`, `index-tasks`.

    - Pivoted Epic 04 from CLI-local/hybrid converters to a multi-format service API v2 expansion
      surface:

      - service remains contract-locked at v1 for `pdf -> md`,
      - `md/html/pdf -> pdf/docx` routes run inside the Hemma dockerized runtime.

    - Added v2 service contracts and decision record:

      - `docs/converters/multi_format_conversion_service_api_v2.md`
      - `docs/decisions/0002-multi-format-service-api-v2.md`

    - Implemented v2 runtime + routes and pivoted CLI routes to remote-only execution:

      - `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
      - `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
      - `scripts/sir_convert_a_lot/interfaces/http_client_v2.py`
      - `scripts/sir_convert_a_lot/interfaces/cli_app.py`
      - `scripts/sir_convert_a_lot/interfaces/cli_routes.py`

    - Replaced local Pandoc/WeasyPrint route tests with v2-client stubs:

      - `tests/sir_convert_a_lot/test_cli_v2_routes.py`

    - Completed Task 39 Hemma docker-lane v2 smoke verification and recorded evidence:

      - command: `pdm run run-local-pdm hemma-verify-v2-conversions`
      - report (Hemma): `build/verification/task-39-v2-smoke/report.md`

- 2026-02-16:

  - Task 27 completed with docker-lane GPU runtime compliance on Hemma.
  - Delivered docker lane runtime fixes:
    - pinned ROCm wheel installation in image build (`2.10.0+rocm7.1` stack),
    - ROCm device passthrough (`/dev/kfd`, `/dev/dri`),
    - verifier lane support (`host|docker`) and readiness-check reliability fixes,
    - container runtime fixes (`ensurepip`, required `video`/`render` groups,
      Docling shared runtime libs including `libxcb1`).
  - Hemma evidence:
    - in-container probe: `torch==2.10.0+rocm7.1`, HIP present, GPU available,
    - `8085/8086` `readyz` returned `ready=true` with revision match,
    - docker-lane verify passed:
      - `SIR_CONVERT_A_LOT_VERIFY_LANE=docker pdm run run-local-pdm hemma-verify-gpu-runtime`
      - live result: `acceleration_used="cuda"`, `gpu_busy_peak=99`.
  - Compose build topology optimized to one shared runtime image for prod/eval
    runtime overlays, removing duplicate image builds by default.

- 2026-02-16:

  - Task 27 created to close docker-lane GPU gap on Hemma.
  - Baseline recorded:
    - dockerized `8085/8086` lane is revision-ready but not GPU-ready,
    - container probe showed `torch==2.10.0+cu128`, `is_available=false`,
    - `/dev/kfd` and `/dev/dri` missing in container.
  - Reference:
    - `docs/reference/ref-dockerized-hemma-gpu-passthrough-gap-2026-02-16.md`

- 2026-02-16:

  - Implemented Task 26 local slice:
    - source-level Docling form ordering patch,
    - structural ordering quality gate,
    - deterministic layout-model fallback selection,
    - backend refactor to keep module size below guardrail.
  - Added focused tests:
    - `tests/sir_convert_a_lot/test_docling_ordering_fallback.py`
  - Local gates passed:
    - `pdm run format-all`
    - `pdm run lint-fix`
    - `pdm run typecheck-all`
    - `pdm run pytest-root tests/sir_convert_a_lot/test_docling_backend.py tests/sir_convert_a_lot/test_docling_ordering_fallback.py`
    - `pdm run validate-tasks`
    - `pdm run validate-docs`
    - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
  - Hemma lane validation remains pending for Task 26 close-out.

- 2026-02-16:

  - Task 26 created and linked to reproducible bug report evidence:
    - `docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md`
  - Locked direction from isolation A/B:
    - `_sort_cells + _sort_clusters` required for Heron-class repair,
    - default `egret_large` requires quality-gated fallback for residual Q13 defect.

## Next Actions

- Add v2 service-side contract tests + v1/v2 compatibility policy (unification path):
  - `docs/backlog/tasks/task-40-service-api-v2-contract-tests-v1-v2-compatibility-policy.md`
- Harden v2 resources zip extraction limits:
  - `docs/backlog/tasks/task-41-harden-v2-resources-zip-extraction-limits.md`
- Split oversized modules + fix v2 cancellation CAS hazard:
  - `docs/backlog/tasks/task-42-split-oversized-cli-and-v2-job-store-cancel-cas.md`
