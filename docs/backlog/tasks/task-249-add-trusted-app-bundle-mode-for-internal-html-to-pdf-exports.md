---
id: 'task-249-add-trusted-app-bundle-mode-for-internal-html-to-pdf-exports'
title: 'Supersede trusted app bundle mode for Klassrumskartan-owned HTML-to-PDF exports'
type: 'task'
status: 'canceled'
priority: 'high'
created: '2026-03-25'
last_updated: '2026-03-26'
related:
  - docs/backlog/tasks/task-37-service-v2-route-html-css-pdf-weasyprint.md
  - docs/backlog/tasks/task-52-publish-downstream-integration-contract-for-skriptoteket-hule-and-projektveckor.md
  - docs/backlog/tasks/task-248-fix-hemma-live-verifier-weasyprint-probe-to-match-container-runtime.md
  - docs/backlog/tasks/task-251-remove-curated-app-trusted-bundle-runtime-paths-after-downstream-cutover.md
  - docs/decisions/0008-curated-app-owned-pdf-exports-stay-out-of-sir-convert-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - html
  - pdf
  - v2
  - service
  - weasyprint
  - trust-boundary
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

The original objective of this task was to make Klassrumskartan-owned
`html -> pdf` bundles work through Sir Convert-a-Lot.

That direction is now superseded by `ADR-0008`, which locks a cleaner
architecture boundary:

- Klassrumskartan-owned PDF artifacts render locally in Skriptoteket
- Sir Convert-a-Lot remains the general conversion service

This task is retained as the audit trail for the superseded trusted-bundle
direction and as a removal target for any remaining service-side trusted-bundle
expansion tied to Klassrumskartan.

This task exists because Hemma proof showed the exact current seam:

- plain WeasyPrint inside `sir_convert_a_lot_prod` embeds local PNG assets;
- the same container, same image, and same HTML lose the image only when
  rendered through
  `scripts/sir_convert_a_lot/infrastructure/weasyprint_html_to_pdf.py`;
- the failure is specific to the service wrapper path using the restricted
  fetcher contract, not to WeasyPrint generally and not to the
  Klassrumskartan renderer itself.

## PR Scope

- Stop expanding the trusted-bundle path for Klassrumskartan-owned artifacts.
- Update converter/downstream docs so app-owned curated-app PDF exports are no
  longer presented as Sir Convert integration targets.
- Preserve Sir Convert's general-purpose/public `html -> pdf` route.
- Treat any remaining trusted-bundle code as a cleanup/removal target rather
  than as the preferred future direction for downstream app-owned exports.

Out of scope:

- changing `html -> md` trust behavior;
- broadening public `html -> pdf` resource access;
- adding any network fetch support;
- introducing hidden caller heuristics instead of an explicit trust contract;
- app-side watermark/layout work in Skriptoteket.

## Deliverables

- [ ] Converter docs explicitly keep Klassrumskartan-owned PDF exports out of
  the Sir Convert boundary.
- [ ] Any remaining trusted-bundle planning linked to Klassrumskartan is marked
  superseded.
- [ ] Public/general-purpose `html -> pdf` remains documented as a supported
  Sir Convert capability.

## Acceptance Criteria

- [ ] Sir Convert contract docs no longer describe Klassrumskartan-owned PDF
  artifacts as a downstream integration target.
- [ ] Skriptoteket and Sir Convert docs agree that Klassrumskartan-owned PDFs
  render locally.
- [ ] No follow-up implementation plan in this task encourages new auth,
  webhook, or trusted-bundle complexity on behalf of Klassrumskartan.

## Proposed API Contract

Public contract direction after supersession:

- public/general-purpose `html -> pdf` remains in Sir Convert;
- app-owned curated-app PDF exports such as Klassrumskartan do not.

## Exact Implementation Slice

This task is now **docs-only supersession and audit trail** work.

The only valid implementation slice from this task is:

- update converter/downstream/internal-adapter contracts so Klassrumskartan
  no longer appears as a Sir Convert final-rendering target;
- point any future runtime cleanup to a dedicated removal task instead of
  extending trusted-bundle behavior;
- preserve the supported public/general-purpose conversion surfaces.

This task must not be used as justification for:

- adding new auth/capability machinery on behalf of Klassrumskartan;
- adding new trusted-bundle branches or caller heuristics;
- expanding service-owned rendering for curated app-owned PDF artifacts.

## Execution Plan

1. Record the service-boundary decision in ADRs/contracts.
1. Update downstream apps such as Skriptoteket to render app-owned PDFs locally.
1. Hand any remaining runtime cleanup to a dedicated removal task rather than
   expanding the trusted-bundle path here.

## Decision Notes

This task no longer defines the preferred future direction.
Its original trusted-bundle objective is superseded for Klassrumskartan by the
local-export boundary in `ADR-0008`.

## Hemma Evidence To Require

No further Hemma proof is required from this superseded task.
The relevant proof burden moves to:

- local Klassrumskartan seating-PDF cutover in Skriptoteket
- cleanup/removal verification if trusted-bundle code is later deleted from
  Sir Convert

## Suggested Validation Commands

- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Checklist

- [ ] Supersession recorded
- [ ] Validation complete
- [ ] Docs updated
