---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-03-01'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
  - docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md
  - docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md
  - docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-45-unify-route-registry-on-v2-and-manifest-contract-hardening.md
  - docs/backlog/tasks/task-46-design-docx-template-contract-storage-and-selection-model.md
  - docs/backlog/tasks/task-47-implement-docx-template-endpoints-validation-and-fixture-templates.md
  - docs/backlog/tasks/task-48-add-v2-route-docx-to-md-with-deterministic-normalization.md
  - docs/backlog/tasks/task-49-add-v2-route-html-to-md-with-resources-and-normalization.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/backlog/tasks/task-53-adr-v2-async-push-delivery-model-sse-webhooks-polling-fallback.md
  - docs/backlog/tasks/task-54-publish-v2-async-push-api-contract-for-sse-and-webhooks.md
  - docs/backlog/tasks/task-55-implement-v2-event-emission-and-sse-streaming.md
  - docs/backlog/tasks/task-56-runbook-and-observability-for-v2-async-push-delivery.md
  - docs/backlog/tasks/task-57-implement-v2-webhook-onboarding-endpoints-and-secret-lifecycle.md
  - docs/backlog/tasks/task-58-implement-v2-webhook-delivery-worker-retries-signatures-and-replay-protection.md
  - docs/backlog/tasks/task-59-enforce-90-percent-test-coverage-gate-for-conversion-core.md
  - docs/backlog/tasks/task-60-harden-v2-converter-security-for-ssrf-traversal-and-timeout-enforcement.md
  - docs/backlog/tasks/task-61-enforce-pandoc-sandbox-and-bounded-subprocess-stderr-handling.md
labels:
  - session-log
  - active-work
---

## Context

Active focus has shifted to Epic 05: a prototype-to-production hardening track that enforces a
**v2-only conversion architecture** with explicit Markdown ingress routes and template-governed DOCX
outputs.

This file is the canonical long-term memory index for session progress; session handoff summaries
must be archived here when `handoff.md` is pruned.

Entrypoints:

- `docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md`
- `docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md`

Primary implementation stories:

- `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
- `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
- `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
- `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
- `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md` (next
  slice after clean-break gates)

## Worklog

- 2026-03-01:

  - Completed Task 61 security follow-up hardening for Pandoc wrappers:
    - added `--sandbox` to all v2 Pandoc conversion wrappers to close unsandboxed
      SSRF/LFI attack surface,
    - introduced shared bounded subprocess helper:
      - `scripts/sir_convert_a_lot/infrastructure/pandoc_subprocess.py`,
    - replaced unbounded `capture_output=True` wrapper execution with bounded
      stderr capture via temp-file strategy and timeout-safe process cleanup.
  - Hardened workdir traversal error echo handling in executor:
    - sanitized user-provided filename echo details in
      `scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`.
  - Extended and updated regression tests for sandbox and timeout behavior:
    - `tests/sir_convert_a_lot/test_pandoc_docx_to_markdown.py`
    - `tests/sir_convert_a_lot/test_pandoc_html_to_markdown.py`
    - `tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`
  - Validation evidence for Task 61:
    - `pdm run run-local-pdm typecheck-all` (pass: `Success: no issues found in 157 source files`)
    - `pdm run run-local-pdm coverage-gate` (pass: `392 passed, 5 skipped`; coverage `95.39%`)
    - `pdm run run-local-pdm validate-tasks` (pass: `Validated 86 backlog files`)
    - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=108 rules=9`)
  - Task 61 moved to `completed` with checklist/evidence synchronized.
  - Scaffolded the next downstream-GUI enabling slice (proposed) via ADR-0004 and Story 16.
  - Proposed execution order: Task 64 -> Task 65 -> Task 66.
  - Completed Task 64 (ADR-0004 contract alignment) and Task 65 (v2 PDF layout presets):
    - added `conversion.pdf_layout` to v2 JobSpec and applied it to PDF outputs via deterministic
      generated CSS (`pdf_layout_presets_v2.py`),
    - added unit and executor tests; executor tests re-split to keep modules \<500 LoC,
    - coverage gate remained >=90% (pass: `95.87%`).
  - Completed Task 66 (`docx -> pdf` v2 route):
    - added sandboxed Pandoc DOCX->HTML wrapper with extracted media under workdir,
    - added executor branch `pipeline_used="docx_to_pdf_v2"` and CLI route registry entry,
    - updated v2 converter docs and downstream integration contract to mark `docx -> pdf` implemented.

- 2026-02-28:

  - Epic 05 was fully executed and terminalized in strict order:
    - clean-break v2-only removal (`T04-T05`, `S01`),
    - DOCX template governance and endpoints (`T06-T07`, `S02`),
    - Markdown ingress routes (`T08-T09`),
    - downstream contract + runtime/docs cleanup (`T10-T12`, `S03-S04`),
    - async push ADR/contract/implementation (`T02-T03`, `T13-T16`, `S05`).
  - Key milestones from the day:
    - v1 conversion surfaces removed; v2 route registry and contracts hardened,
    - `docx -> md` and `html -> md` routes implemented with deterministic validation and tests,
    - eval container/runtime removed; topology simplified to single runtime,
    - async push stack completed (SSE replay + webhook onboarding + signed retry/DLQ delivery),
    - Task 60 security hardening delivered (WeasyPrint SSRF/LFI guard + traversal + timeout parity).
  - Validation trend remained above target throughout:
    - coverage gates across slices ranged from `93.03%` to `96.14%`,
    - docs/task validators and typecheck remained passing.
  - Canonical detailed evidence is preserved in:
    - `docs/backlog/tasks/task-44-*.md` through `task-60-*.md`,
    - `.agents/session/handoff.md` dated entries for 2026-02-28.

- 2026-02-18:

  - Epic 04 delivered service API v2 multi-format runtime and CLI remote-only pivot
    for non-PDF->MD routes.
  - Follow-up hardening tasks 40-42 completed (tests, zip-hardening, cancellation CAS).

## Next Actions

- Epic 05 is complete; run post-implementation ruthless review and release-readiness verification.
- After Story 16 contract surfaces land, proceed with Skriptoteket curated conversion app cutover planning
  (remove runner-script conversion surfaces, route all conversions via Sir Convert-a-Lot v2).
