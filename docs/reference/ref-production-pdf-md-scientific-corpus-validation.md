---
type: reference
id: REF-production-pdf-md-scientific-corpus-validation
title: Production PDF->MD Scientific Corpus Validation (Task 12)
status: active
created: '2026-02-15'
updated: '2026-02-15'
owners:
  - platform
tags:
  - benchmark
  - task-12
  - scientific-corpus
  - hemma
links:
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json
---

## Corpus and Run Context

- Corpus path: `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- Corpus size: `10` PDFs
- Local SHA: `459fb6f5744b2840839eb8fd6aace497d3e1d6f3`
- Hemma SHA: `459fb6f5744b2840839eb8fd6aace497d3e1d6f3`
- Generated at: `2026-02-15T01:28:14Z`

## Lane Methodology

- Acceptance lane uses production-lock tunnel service profile (`auto`, `gpu_required`).
- Evaluation lane runs A/B (`docling` vs `pymupdf`) with isolated eval profile for CPU-only pymupdf.
- Quality ranking uses weighted rubric and deterministic tie-breakers.

## Acceptance 10/10 Gate

- Gate passed: `True`
- Succeeded jobs: `10/10`
- p50 latency: `15.382687` seconds
- Retry warnings: `0`

## A/B Quality Results

| Backend | Median Score | Severe Failures | Success Rate | p50 Latency |
|---|---:|---:|---:|---:|
| pymupdf | 3.000 | 0 | 1.000 | 8.766 |
| docling | 3.000 | 0 | 1.000 | 11.430 |

- Evaluation lane success rate: `1.0`

## Governance Compatibility

- Quality winner: `pymupdf`
- Winner compatible for production profile: `False`
- Recommended production backend: `docling`

## Final Recommendation

- Adopt `docling` for production path based on quality-first ranking and governance constraints.

## Follow-up Actions

- Quality winner requires non-default governance profile; keep production recommendation governance-compatible and track follow-up decision task/ADR.
