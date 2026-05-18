---
id: review-22-ruthless-review-of-task-329-adr-0002-closeout
title: Ruthless review of Task 329 ADR-0002 closeout
type: review
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/tasks/task-329-close-out-adr-0002-against-active-service-api-v2-authority.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md
labels:
  - review
  - adr
  - v2
  - governance
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: independent ruthless docs-as-code review of Task 329 ADR-0002
  closeout.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-329-close-out-adr-0002-against-active-service-api-v2-authority.md`
  - `docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md`
- Scope under review:
  - ADR-0002 status changed from proposed to superseded.
  - ADR-0012 created as accepted current-state Service API v2 authority.
  - Active v2 converter/downstream/CLI docs linked to ADR-0012.
  - Task 329 evidence and validation closeout.
- Public surfaces affected:
  - Service API v2 decision authority.
  - Converter docs and downstream integration docs.
- Compatibility posture:
  - Docs-as-code governance closeout only.
  - No runtime, Hemma, Gateway, HuleEdu, Skriptoteket, ADR-0009, or ADR-0011
    behavior is authorized by this review.
- Independence requirement:
  - The implementing agent authored this ADR/status closeout and must not
    approve it. A separate reviewer must verify the finding set and decision.

## Findings

1. [x] `blocker` - Task 329 is mixed with unrelated runtime/OpenAPI contract
   changes despite its stop condition.
   - Evidence:
     - `docs/backlog/tasks/task-329-close-out-adr-0002-against-active-service-api-v2-authority.md:208`
       marks "No runtime ... change is bundled into this task" as satisfied.
     - `docs/backlog/tasks/task-329-close-out-adr-0002-against-active-service-api-v2-authority.md:225`
       explicitly stops before changing service runtime behavior or generated
       OpenAPI snapshots without separate implementation-task authority.
     - `scripts/sir_convert_a_lot/infrastructure/job_store_models_v2.py:83`
       changes the persisted job record model default for
       `structured_llm_admission`.
     - `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json:455`
       adds `DigiExamAnswerKeyCompletionProviderLineageV1`, expanding the
       generated OpenAPI contract surface.
   - Why it matters: Review 22 is only authorized to approve the ADR-0002
     closeout and ADR-0012 decision-state repair. Bundling provider-lineage
     runtime/schema changes into the same uncommitted review set makes the
     closeout evidence inaccurate and risks approving Task 325-B behavior
     through the Task 329 review gate.
   - Required fix: Split the Task 325-B runtime/OpenAPI/test changes out of the
     Task 329 review set or attach them to their own governed closeout/review
     before this review approves Task 329. After the Task 329 diff is clean,
     rerun the docs closeout gates and update this review with a narrow
     re-review.
   - Proof requirement: show `git diff --name-status` scoped to Task 329 docs
     only, then rerun `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check`.

## Decision

Changes requested.

## Response

The ADR-0002 supersession shape and ADR-0012 current-state authority are
directionally sound, but Task 329 is not approved while the review set also
contains unrelated runtime/OpenAPI provider-lineage changes. Task 329 must
remain `in_progress`.

## Follow-up Actions

1. Keep Task 329 `in_progress`.
1. Split or separately govern the Task 325-B runtime/OpenAPI/test changes before
   re-reviewing Task 329.
1. Rerun the docs closeout gates after the review set is narrowed.

## Completion

Completed as `changes_requested` on 2026-05-18.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
