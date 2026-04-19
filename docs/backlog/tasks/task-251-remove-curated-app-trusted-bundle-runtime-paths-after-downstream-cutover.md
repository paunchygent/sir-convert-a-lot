---
id: task-251-remove-curated-app-trusted-bundle-runtime-paths-after-downstream-cutover
title: Remove curated-app trusted-bundle runtime paths after downstream local cutover
type: task
status: done
priority: high
created: '2026-03-26'
last_updated: '2026-03-26'
related:
  - docs/backlog/tasks/task-249-add-trusted-app-bundle-mode-for-internal-html-to-pdf-exports.md
  - docs/decisions/0008-curated-app-owned-pdf-exports-stay-out-of-sir-convert-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - html
  - pdf
  - v2
  - cleanup
  - boundary
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

After downstream products such as Skriptoteket complete their local cutover for
curated app-owned PDF exports, remove the now-convoluted Sir Convert runtime
paths that existed only to support those downstream artifacts.

This task exists to ensure the architecture pivot in `ADR-0008` results in real
code deletion rather than a soft deprecation.

## PR Scope

- Delete curated-app-specific trusted-bundle runtime branches that are no
  longer needed after downstream cutover.
- Delete any auth/validation special cases that existed only for those curated
  app-owned PDF bundles.
- Keep public/general-purpose `html -> pdf` and other supported conversion
  routes intact.

Out of scope:

- changing public/general-purpose `html -> pdf` semantics;
- changing `html -> md` or `html -> docx` behavior unless they directly depend
  on the dead curated-app path;
- adding a replacement capability system for a path that should no longer
  exist.

## Deliverables

- [x] Curated-app-specific trusted-bundle runtime branches are removed.
- [x] No Sir Convert contract docs imply that curated app-owned PDF exports
  should still pass through the service.
- [x] General/public conversion routes remain documented and tested.

## Acceptance Criteria

- [x] Downstream local cutover is proven before cleanup starts:
  - one live seating export proof exists on `http://127.0.0.1:5173`
  - no supported consumer still depends on `trusted_app_bundle`
- [x] `html -> pdf` runtime code no longer contains branches or validation logic
  that exist only for downstream curated-app-owned PDF bundles.
- [x] Auth/validation no longer carry dead policy surface for the removed
  curated-app trusted-bundle path.
- [x] Sir Convert docs and runbooks describe only the supported remaining
  `html -> pdf` surfaces after cleanup.

## Exact Implementation Slice

Primary targets:

- `scripts/sir_convert_a_lot/interfaces/http_auth_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_jobs_v2_request_validation.py`
- `scripts/sir_convert_a_lot/infrastructure/v2_non_pdf_routes_html.py`
- `scripts/sir_convert_a_lot/infrastructure/weasyprint_html_to_pdf.py`

Expected shape:

- remove curated-app-specific trust-mode branching that no longer has a valid
  downstream consumer;
- collapse validation/auth/runtime logic back to the supported general
  conversion surface;
- keep the service boundary easy to reason about.

## Execution Plan

1. Do not begin cleanup until downstream cutover is proven complete:
   - require one live seating export proof from Skriptoteket on
     `http://127.0.0.1:5173`
   - require explicit confirmation that no supported consumer still relies on
     `trusted_app_bundle`
1. Delete the dead runtime/auth/validation branches.
1. Update docs/runbooks to match the cleaned runtime.
1. Run focused `html -> pdf` validation to prove public/general conversion
   remains intact.

## Suggested Validation Commands

- `pdm run validate-tasks`
- `pdm run validate-docs`
- focused test/verification for the remaining supported `html -> pdf` path

## Checklist

- [x] Downstream cutover confirmed
- [x] Live seating export proof recorded
- [x] No supported consumer still needs `trusted_app_bundle`
- [x] Cleanup implemented
- [x] Validation complete
- [x] Docs updated

## Implementation Note

Completed 2026-03-26:

- removed the trusted-bundle/input-trust-mode runtime path and the dedicated
  internal-key lane from the v2 service;
- simplified `html -> pdf` back to the supported general-purpose single-key
  contract;
- deleted the dead cross-lane and trusted-bundle verification/test surface;
- revalidated the supported `html -> pdf`, v2 lifecycle, webhook, and SSE
  contract suite.
