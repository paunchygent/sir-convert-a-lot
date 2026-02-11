---
id: '003-unified-conversion-service-epic'
title: 'Unified conversion service (Hemma-first, multi-format, cross-repo)'
type: 'epic'
status: 'proposed'
priority: 'critical'
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - 'docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md'
  - 'docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md'
  - 'docs/converters/pdf_to_md_service_api_v1.md'
  - 'docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md'
  - 'docs/backlog/stories/story-03-01-lock-v1-contract-and-no-hassle-local-dev-ux.md'
  - 'docs/backlog/stories/story-03-02-gpu-first-execution-and-fallback-governance.md'
  - 'docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md'
  - 'docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md'
  - 'docs/backlog/stories/story-03-05-quality-performance-reliability-validation-gates.md'
labels:
  - 'epic'
  - 'conversion-platform'
  - 'hemma'
  - 'huledu'
  - 'skriptoteket'
---
# Unified conversion service (Hemma-first, multi-format, cross-repo)

## Goal

Deliver one canonical, versioned conversion platform that:
- runs heavy workloads on Hemma,
- is simple to use from local development through internal HTTP/tunnel,
- integrates cleanly with both HuleEdu and Skriptoteket backends,
- replaces ad hoc repo-local converter scripts with one stable CLI + API surface.

## Behavioral End State (Product Promise)

From any local repo, a developer or coding assistant can run one command (`convert-a-lot`)
against a folder of files and get deterministic outputs in a target directory, with clear status,
retries, and failure reasons, without selecting backends manually or rewriting integration logic.

## In Scope

- Canonical service contract (`v1`) for conversion jobs.
- Canonical local client UX (`convert-a-lot`) for developer workflows.
- Internal API integration surface for HuleEdu and Skriptoteket.
- GPU-first execution for PDF-heavy workloads with explicit governance for fallback behavior.
- Consolidation of conversion capabilities under one platform for:
  - html
  - pdf
  - md
  - docx
  - xlsx
  - csv
- Test, performance, and reliability gates required before consolidation cleanup.

## Out of Scope (for this epic)

- Public internet exposure of conversion endpoints.
- Immediate queue-worker migration (must remain queue-compatible, but not required in first cut).
- New format classes outside listed scope.

## Stories

1. `docs/backlog/stories/story-03-01-lock-v1-contract-and-no-hassle-local-dev-ux.md`
2. `docs/backlog/stories/story-03-02-gpu-first-execution-and-fallback-governance.md`
3. `docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md`
4. `docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md`
5. `docs/backlog/stories/story-03-05-quality-performance-reliability-validation-gates.md`

## Acceptance Criteria

1. One canonical API + CLI contract is documented, test-enforced, and used across repos.
2. Local usage from tunnel/internal HTTP is stable and documented as default dev workflow.
3. HuleEdu and Skriptoteket backend integrations use the same internal contract with no repo-specific forks.
4. GPU-first policy is validated and enforced during initial rollout; fallback policy is explicit and decision-gated.
5. All listed formats (html/pdf/md/docx/xlsx/csv) are supported through canonical surface.
6. Redundant converter scripts are removed or converted to thin compatibility wrappers after stabilization gate.
7. Performance and reliability targets in Story 003e are met on the agreed benchmark corpus.

## Quality and Test Strategy (Epic Level)

- Contract tests: endpoint schema, idempotency behavior, error envelope.
- Integration tests: local client -> tunnel/internal HTTP -> Hemma service -> artifacts.
- Cross-repo tests: HuleEdu and Skriptoteket backend calls against same service contract.
- Regression corpus tests: noisy PDFs, mixed document classes, malformed inputs.
- Performance tests: latency/throughput/resource targets tracked against baseline hardware profile.

## Performance Targets (Initial)

- Job creation API (`POST /v1/convert/jobs`) p95 server handling < 500 ms excluding upload transfer time.
- Status API (`GET /v1/convert/jobs/{job_id}`) p95 < 200 ms under normal load.
- PDF conversion on benchmark corpus:
  - 90% of valid research PDFs <= 20 pages complete within 5 minutes on target Hemma GPU profile.
  - Batch of 10 benchmark PDFs completes within 30 minutes end-to-end.
- Service reliability:
  - >= 99% successful completion for valid benchmark inputs.
  - 100% idempotency correctness for replay/collision scenarios in test suite.

## Completion Gate

Epic is complete only when:
- all story acceptance criteria pass,
- consolidation cleanup is done,
- and default developer guidance in this repo and consuming repos points to canonical platform only.

## Checklist

- [x] Story 003a completed
- [ ] Story 003b completed
- [ ] Story 003c completed
- [ ] Story 003d completed
- [ ] Story 003e completed
- [ ] Cross-repo docs updated (HuleEdu + Skriptoteket integration notes)
- [ ] Consolidation cleanup finished (no ad hoc converter ownership drift)
