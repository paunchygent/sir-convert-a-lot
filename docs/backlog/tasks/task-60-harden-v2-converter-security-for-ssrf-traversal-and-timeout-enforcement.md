---
id: task-60-harden-v2-converter-security-for-ssrf-traversal-and-timeout-enforcement
title: Harden v2 converter security for SSRF traversal and timeout enforcement
type: task
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
labels:
  - security
  - resilience
  - v2
  - converters
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close critical pre-production findings in v2 conversion execution by hardening
WeasyPrint resource fetching, workdir path resolution, subprocess timeout behavior,
and HTML resource-validation consistency across routes.

## PR Scope

- Block SSRF/local file exfiltration in `weasyprint_html_to_pdf.py`:
  - enforce strict fetch policy via custom `url_fetcher`,
  - allow only local files under job `workdir`,
  - block external network/resource schemes.
- Add deterministic path-traversal protections in `v2_conversion_executor.py` for:
  - `css_filenames`,
  - `reference_docx_filename`.
- Enforce subprocess timeout support across Pandoc wrappers:
  - `pandoc_docx_to_markdown.py`,
  - `pandoc_html_to_markdown.py`,
  - `pandoc_html_to_docx.py`,
  - `pandoc_markdown_to_html.py`.
- Apply HTML local-resource validation parity for all HTML source routes
  (`html -> md`, `html -> pdf`, `html -> docx`) with deterministic 422 mapping.
- Add/extend unit and contract tests for security and timeout paths.

## Deliverables

- [x] WeasyPrint conversion path blocks external/local-outside-workdir resource fetches.
- [x] Executor rejects traversal attempts in CSS and reference DOCX spec fields.
- [x] Pandoc wrapper timeout behavior is deterministic and test-covered.
- [x] HTML source routes share the same local-resource validation behavior and error semantics.
- [x] Validation evidence captured (`typecheck`, targeted tests, coverage gate, docs validators).

## Acceptance Criteria

- [x] SSRF payloads and out-of-scope file references fail closed with deterministic error codes.
- [x] `../` traversal attempts in `css_filenames` and `reference_docx_filename` return 422
  without touching paths outside workdir.
- [x] Converter subprocesses fail deterministically on timeout with retry-safe mapping.
- [x] HTML route validation parity is enforced for `html -> md/pdf/docx`.
- [x] `pdm run run-local-pdm coverage-gate` remains >=90%.
- [x] `pdm run run-local-pdm validate-tasks` and `validate-docs` pass.

## Validation Commands

- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_v2_conversion_executor_general.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Validation Evidence

- [x] Targeted security/regression suite:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_weasyprint_html_to_pdf.py tests/sir_convert_a_lot/test_v2_conversion_executor_general.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_paths.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_pdf_to_docx.py tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`
    (pass: `62 passed`, 2026-02-28).
- [x] Type safety:
  - `rm -rf .mypy_cache && pdm run run-local-pdm typecheck-all`
    (pass: `Success: no issues found in 156 source files`, 2026-02-28).
- [x] Coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass: `388 passed, 5 skipped`; total coverage `95.53%`, 2026-02-28).
- [x] Docs gates:
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 85 backlog files`).
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=107 rules=9`).
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
    (pass: `/tmp/sir_tasks_index.md`).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
