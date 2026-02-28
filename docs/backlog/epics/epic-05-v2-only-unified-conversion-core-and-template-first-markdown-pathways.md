---
id: epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways
title: V2 only unified conversion core and template first markdown pathways
type: epic
status: in_progress
priority: critical
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - v2
  - clean-break
  - prototype-to-prod
---
Major capability increment managed through linked stories.

## Goal

Deliver a clean-break, production-grade conversion core where **all API conversion routes are v2**,
legacy split-brain behavior is removed, and template-first Markdown pathways are explicit and
downstream GUI-friendly.

This epic is complete only when v1 is fully removed, required Markdown ingress routes are
implemented and tested, DOCX template governance is complete, and conflicting legacy docs/runtime
paths are cleaned up.

## In Scope

- Full v2 unification:
  - remove v1 API/service/client/domain/doc surfaces,
  - move `pdf -> md` to v2 route semantics and tests,
  - unify CLI routing on v2 only.
- Complete Markdown ingress route set:
  - `pdf -> md` (v2)
  - `docx -> md` (v2)
  - `html -> md` (v2)
- DOCX template governance and productization:
  - template contract and metadata,
  - reusable catalog of practical reference DOCX templates,
  - API selection semantics suitable for UI products.
- Runtime and ops simplification:
  - remove eval container/profile and associated conflicting surfaces,
  - preserve deterministic, hardened single-runtime behavior.
- Docs-as-code cleanup:
  - remove stale local/hybrid/v1 assumptions,
  - synchronize converter docs, ADR state, runbooks, and backlog references.
- Downstream integration readiness:
  - publish clear API contract patterns for Skriptoteket, HuleEdu, and Projektveckor GUI flows.
- Production async push readiness on v2:
  - SSE live events for UI progress,
  - webhook callbacks for server-to-server integrations,
  - webhook onboarding APIs with secret lifecycle management,
  - polling preserved as fallback.

## Out of Scope

- New non-document conversion domains (audio/image/TTS expansion) beyond already approved backlog scope.
- Feature additions that do not contribute to v2 unification, Markdown ingress completeness, or template governance.
- Reintroducing dual-version compatibility bridges.

## Stories

1. `docs/backlog/stories/story-14-v2-only-clean-break-and-api-surface-unification.md`
1. `docs/backlog/stories/story-13-docx-template-catalog-and-reference-governance.md`
1. `docs/backlog/stories/story-11-markdown-ingestion-routes-docx-to-md-and-html-to-md.md`
1. `docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md`
1. `docs/backlog/stories/story-15-v2-async-push-channels-sse-webhooks-and-polling-fallback.md`

## Acceptance Criteria

- [ ] No v1 conversion API surface remains in runtime or public CLI behavior.
- [ ] `pdf -> md`, `docx -> md`, and `html -> md` are all served by v2 with deterministic contracts.
- [ ] DOCX template catalog exists with at least three practical reference templates and typed API selection semantics.
- [ ] Route taxonomy and manifest semantics are deterministic and explicit for downstream UI orchestration.
- [ ] Eval container/profile and conflicting legacy runtime paths are removed.
- [ ] Converter/ADR/runbook/backlog docs no longer describe stale v1 or local/hybrid behavior.
- [ ] V2 async push model is documented and implemented with SSE/webhooks and polling fallback.
- [ ] Async push readiness has measurable outcomes:
  - polling request-rate reduced by >= 60% for push-enabled clients,
  - SSE propagation p95 <= 2s,
  - webhook initial delivery p95 <= 5s and success >= 99% within first 3 attempts.
- [ ] Quality gates pass:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
