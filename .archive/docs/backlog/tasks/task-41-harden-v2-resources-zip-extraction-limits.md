---
id: task-41-harden-v2-resources-zip-extraction-limits
title: Harden v2 resources zip extraction limits
type: task
status: completed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-34-service-v2-job-store-runtime-for-multi-format-artifacts.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - security
  - v2
  - resources
  - zip
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden v2 resources zip extraction against zip-bomb and filesystem abuse, while preserving
deterministic extraction semantics for CSS/images/fonts used by HTML/Markdown conversions.

## PR Scope

- Add explicit extraction limits enforced *before* extraction:
  - max members
  - max total uncompressed bytes
  - max single-file uncompressed bytes
- Extract member-by-member (avoid `ZipFile.extractall`) while retaining the existing path traversal
  protection.
- Ensure consistent deterministic error mapping via `ResourcesZipError` codes, including a new
  “resources_zip_too_large” style code (exact naming to be decided in implementation).
- Add focused tests that validate:
  - rejects `../` traversal and absolute paths (existing behavior preserved)
  - rejects excessive entry count
  - rejects excessive uncompressed size (zip bomb)
  - accepts a normal small zip and extracts expected paths

## Deliverables

- [x] Zip extraction limits exist and are enforced.
- [x] Deterministic error codes exist for each rejection path.
- [x] Focused unit tests exist for both success and failure cases.

## Acceptance Criteria

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_resources_zip.py -q` passes.
- [x] `pdm run run-local-pdm typecheck-all` passes.
- [x] `pdm run run-local-pdm validate-docs` passes (if contract docs mention limits).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
