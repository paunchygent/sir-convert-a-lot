---
type: adr
id: ADR-SIRCON-0011
title: Service API v2 Current-State Authority and Extension Boundary
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: accepted
links:
  governing: []
deciders:
  - platform
retired_ids:
  - ADR-0012
---

## Context

Source record: docs/decisions/0012-service-api-v2-current-state-authority-and-extension-boundary.md

### Purpose

> Record the current accepted decision authority for Service API v2 after the
> runtime, converter contracts, and follow-on ADRs overtook the original
> ADR-0002 proposal.
>
> This decision supersedes ADR-0002 as the active decision record for Service API
> v2. ADR-0002 remains the historical February 2026 proposal that introduced the
> multi-format v2 pivot, but it no longer matches current v2-only runtime truth.

### Context

> ADR-0002 proposed Service API v2 as the multi-format expansion surface while
> preserving the locked PDF-to-Markdown v1 contract. That was correct when
> written on 2026-02-18, but the active platform state changed:
>
> - Task 44 removed v1 conversion routes and CLI clients as a clean break to v2.
> - Task 51 purged conflicting active-surface v1 and local/hybrid guidance.
> - `docs/reference/ref-sircon-general-multi-format-conversion-service-api-v2-multi-format-conversion-service-api-v2.md` is the active
>   normative converter contract and names v1 conversion routes as removed from
>   the runtime surface.
> - `docs/reference/ref-sircon-general-downstream-integration-contract-v2-downstream-integration-contract-v2.md` states that
>   downstream conversion integrations are v2-only and `/v1/convert/jobs*` is not
>   part of the supported runtime surface.
> - Accepted ADRs 0003 through 0008 extended or constrained v2 after ADR-0002.
>
> Leaving ADR-0002 as proposed created an authority split: runtime and converter
> docs treated Service API v2 as active, while the decision state still suggested
> the base v2 product decision was unresolved.

## Decision

### Decision

> Service API v2 is the accepted, active conversion API authority for Sir
> Convert-a-Lot.
>
> ### V2-only conversion surface
>
> Conversion integrations use Service API v2 only. The `/v1/convert/jobs*`
> conversion route family is historical and unsupported in the active runtime.
> The historical v1 converter document remains available as an archival contract
> record, not as active integration guidance.
>
> ### Normative contract document
>
> The normative API contract for active v2 conversion behavior is:
>
> - `docs/reference/ref-sircon-general-multi-format-conversion-service-api-v2-multi-format-conversion-service-api-v2.md`
>
> Route-specific converter contracts may extend that base contract only when they
> are explicitly linked from the v2 contract and governed by their own backlog,
> ADR, reference, or review authority.
>
> ### Current base route authority
>
> The active v2 conversion route surface is the set documented in the v2 converter
> contract and exposed by the generated OpenAPI/router surface for conversion
> jobs, artifacts, templates, async push, and approved route-specific conversion
> extensions.
>
> This decision does not make every `/v2/*` HTTP route part of the base
> multi-format conversion ADR. Operator-only settings and Gateway/internal
> identity cutover remain governed by their own decisions and references.
>
> ### Extension policy
>
> Service API v2 evolves by governed additive extension:
>
> - optional fields, new response metadata, new error codes, and new routes may be
>   added when a backlog task plus converter/ADR/reference authority defines the
>   behavior;
> - breaking changes to existing v2 conversion semantics require a new major
>   version or an explicit accepted decision that records the clean break;
> - route-specific behavior must not become implicit base-contract behavior until
>   the governing docs promote it.
>
> ### Accepted follow-on v2 decisions
>
> The following accepted ADRs remain detailed authority for their specific v2
> extensions or boundaries:
>
> - ADR-0003: async push delivery through SSE, webhooks, and polling fallback.
> - ADR-0004: PDF layout presets, preview rendition, and `docx -> pdf`.
> - ADR-0005: long-job progress, checkpoints, partials, cancel-with-save, resume,
>   and retention.
> - ADR-0006: sidecar-backed TTS architecture and non-PDF GPU governance.
> - ADR-0007: reusable internal multi-backend TTS sidecar capability contract.
> - ADR-0008: curated app-owned PDF exports stay out of Sir Convert v2.

## Non-Decisions

## Consequences

### Status

> - Accepted
> - Date: 2026-05-18
> - Supersedes: `docs/decisions/0002-multi-format-service-api-v2.md`

### Follow-up

> - Review the ADR-0002 closeout through
>   `docs/backlog/reviews/review-22-ruthless-review-of-task-329-adr-0002-closeout.md`.
> - Do not mark Task 329 completed until an independent reviewer approves the
>   status-changing closeout.

### Consequences

> - ADR-0002 is superseded, not amended into a new historical shape.
> - Active docs can cite ADR-0012 as the accepted base decision for current
>   Service API v2 authority.
> - Historical v1/v2 compatibility and v1 API docs remain archival or draft
>   context; they do not override the active v2-only conversion surface.
> - Future conversion route expansion must declare whether it is base v2,
>   route-specific v2, operator-only, or Gateway/internal identity authority.
> - Runtime behavior is unchanged by this decision. This is a docs-as-code
>   authority closeout, not a deploy or implementation slice.
