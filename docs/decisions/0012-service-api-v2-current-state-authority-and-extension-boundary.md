---
type: decision
id: ADR-0012
title: Service API v2 Current-State Authority and Extension Boundary
status: accepted
created: 2026-05-18
updated: 2026-05-18
owners:
  - platform
tags:
  - adr
  - api
  - v2
  - conversion
  - governance
links:
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0003-v2-async-push-sse-webhooks-and-polling-fallback.md
  - docs/decisions/0004-v2-pdf-layout-presets-preview-rendition-and-docx-to-pdf.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0006-hemma-sidecar-tts-architecture-and-non-pdf-gpu-governance.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
  - docs/decisions/0008-curated-app-owned-pdf-exports-stay-out-of-sir-convert-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/service_api_v1_v2_compatibility_policy.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-329-close-out-adr-0002-against-active-service-api-v2-authority.md
---

## Purpose

Record the current accepted decision authority for Service API v2 after the
runtime, converter contracts, and follow-on ADRs overtook the original
ADR-0002 proposal.

This decision supersedes ADR-0002 as the active decision record for Service API
v2. ADR-0002 remains the historical February 2026 proposal that introduced the
multi-format v2 pivot, but it no longer matches current v2-only runtime truth.

## Status

- Accepted
- Date: 2026-05-18
- Supersedes: `docs/decisions/0002-multi-format-service-api-v2.md`

## Context

ADR-0002 proposed Service API v2 as the multi-format expansion surface while
preserving the locked PDF-to-Markdown v1 contract. That was correct when
written on 2026-02-18, but the active platform state changed:

- Task 44 removed v1 conversion routes and CLI clients as a clean break to v2.
- Task 51 purged conflicting active-surface v1 and local/hybrid guidance.
- `docs/converters/multi_format_conversion_service_api_v2.md` is the active
  normative converter contract and names v1 conversion routes as removed from
  the runtime surface.
- `docs/converters/downstream_integration_contract_v2.md` states that
  downstream conversion integrations are v2-only and `/v1/convert/jobs*` is not
  part of the supported runtime surface.
- Accepted ADRs 0003 through 0008 extended or constrained v2 after ADR-0002.

Leaving ADR-0002 as proposed created an authority split: runtime and converter
docs treated Service API v2 as active, while the decision state still suggested
the base v2 product decision was unresolved.

## Decision

Service API v2 is the accepted, active conversion API authority for Sir
Convert-a-Lot.

### V2-only conversion surface

Conversion integrations use Service API v2 only. The `/v1/convert/jobs*`
conversion route family is historical and unsupported in the active runtime.
The historical v1 converter document remains available as an archival contract
record, not as active integration guidance.

### Normative contract document

The normative API contract for active v2 conversion behavior is:

- `docs/converters/multi_format_conversion_service_api_v2.md`

Route-specific converter contracts may extend that base contract only when they
are explicitly linked from the v2 contract and governed by their own backlog,
ADR, reference, or review authority.

### Current base route authority

The active v2 conversion route surface is the set documented in the v2 converter
contract and exposed by the generated OpenAPI/router surface for conversion
jobs, artifacts, templates, async push, and approved route-specific conversion
extensions.

This decision does not make every `/v2/*` HTTP route part of the base
multi-format conversion ADR. Operator-only settings, Gateway/internal identity
cutover, and exam-authoring correction APIs remain governed by their own
decisions, converter contracts, references, and backlog tasks.

### Extension policy

Service API v2 evolves by governed additive extension:

- optional fields, new response metadata, new error codes, and new routes may be
  added when a backlog task plus converter/ADR/reference authority defines the
  behavior;
- breaking changes to existing v2 conversion semantics require a new major
  version or an explicit accepted decision that records the clean break;
- route-specific behavior must not become implicit base-contract behavior until
  the governing docs promote it.

### Accepted follow-on v2 decisions

The following accepted ADRs remain detailed authority for their specific v2
extensions or boundaries:

- ADR-0003: async push delivery through SSE, webhooks, and polling fallback.
- ADR-0004: PDF layout presets, preview rendition, and `docx -> pdf`.
- ADR-0005: long-job progress, checkpoints, partials, cancel-with-save, resume,
  and retention.
- ADR-0006: sidecar-backed TTS architecture and non-PDF GPU governance.
- ADR-0007: reusable internal multi-backend TTS sidecar capability contract.
- ADR-0008: curated app-owned PDF exports stay out of Sir Convert v2.

## Consequences

- ADR-0002 is superseded, not amended into a new historical shape.
- Active docs can cite ADR-0012 as the accepted base decision for current
  Service API v2 authority.
- Historical v1/v2 compatibility and v1 API docs remain archival or draft
  context; they do not override the active v2-only conversion surface.
- Future conversion route expansion must declare whether it is base v2,
  route-specific v2, operator-only, Gateway/internal identity, or exam-authoring
  authority.
- Runtime behavior is unchanged by this decision. This is a docs-as-code
  authority closeout, not a deploy or implementation slice.

## Evidence

- ADR-0002 frontmatter was still proposed before this closeout and preserved
  v1 endpoints in the original decision text.
- Task 44 completed the clean break that removed v1 conversion routes and CLI
  clients.
- Task 51 completed active-surface cleanup and v2-only hygiene checks.
- The active v2 converter contract says v1 conversion routes were removed from
  the runtime surface and lists Service API v2 as the active conversion
  contract.
- The generated OpenAPI/router surface exposes active `/v2/convert/jobs*`,
  artifact, checkpoint, resume, async push, template, operator, and
  exam-authoring routes; this decision classifies the non-conversion routes as
  governed by their own authority rather than by the base v2 ADR.

## Follow-up

- Review the ADR-0002 closeout through
  `docs/backlog/reviews/review-22-ruthless-review-of-task-329-adr-0002-closeout.md`.
- Do not mark Task 329 completed until an independent reviewer approves the
  status-changing closeout.
