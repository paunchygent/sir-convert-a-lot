---
id: task-61-enforce-pandoc-sandbox-and-bounded-subprocess-stderr-handling
title: Enforce Pandoc sandbox and bounded subprocess stderr handling
type: task
status: completed
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/backlog/tasks/task-60-harden-v2-converter-security-for-ssrf-traversal-and-timeout-enforcement.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
labels:
  - security
  - resilience
  - pandoc
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close remaining critical converter attack vectors by sandboxing all Pandoc
invocations and preventing unbounded stderr memory growth under malformed input.

## PR Scope

- Add `--sandbox` to all Pandoc wrappers used by v2 conversion flows:
  - `pandoc_docx_to_markdown.py`
  - `pandoc_html_to_markdown.py`
  - `pandoc_html_to_docx.py`
  - `pandoc_markdown_to_html.py`
- Replace unbounded `capture_output=True` execution with bounded stderr capture
  backed by temporary files (stdout discarded).
- Preserve timeout behavior and deterministic error mapping for all wrappers.
- Add/adjust tests to assert:
  - sandbox flag presence in command arrays,
  - timeout mapping remains deterministic,
  - wrappers still produce expected success/failure semantics.

## Deliverables

- [x] Pandoc wrappers enforce `--sandbox` on every command.
- [x] Subprocess stderr capture is bounded (no unbounded in-memory accumulation).
- [x] Tests cover sandbox flag usage and timeout/error stability.
- [x] Validation evidence captured and docs/task gates pass.

## Acceptance Criteria

- [x] Critical SSRF/LFI vector via unsandboxed Pandoc is closed in v2 wrappers.
- [x] Wrapper execution no longer depends on unbounded `capture_output=True`.
- [x] No regression to timeout/error code behavior.
- [x] `pdm run run-local-pdm coverage-gate` remains >=90%.
- [x] `pdm run run-local-pdm validate-tasks` and `validate-docs` pass.

## Validation Commands

- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_v2_conversion_executor_general.py tests/sir_convert_a_lot/test_v2_conversion_executor_html_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_paths.py tests/sir_convert_a_lot/test_v2_conversion_executor_docx_to_md.py tests/sir_convert_a_lot/test_v2_conversion_executor_pdf_to_docx.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Validation Evidence

- [x] Type safety:
  - `pdm run run-local-pdm typecheck-all`
    (pass: `Success: no issues found in 157 source files`, 2026-03-01).
- [x] Full coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass: `392 passed, 5 skipped`; total coverage `95.39%`, 2026-03-01).
- [x] Docs gates:
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 86 backlog files`).
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=108 rules=9`).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
