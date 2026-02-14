---
id: task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus
title: Scientific-paper workload evidence harness + Hemma tunnel acceptance report (10/10 corpus)
type: task
status: proposed
priority: high
created: '2026-02-14'
last_updated: '2026-02-14'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/backlog/tasks/task-09-durable-filesystem-job-store-restart-recovery-retention-sweeper-story-02-01.md
  - docs/backlog/tasks/task-10-docling-backend-ocr-policy-mapping-deterministic-markdown-normalization-width-100.md
  - docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md
labels:
  - benchmark
  - evidence
  - hemma
  - tunnel
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Provide reproducible, machine-readable workload evidence that the service is production-ready for
real scientific-paper PDFs, with the hard acceptance gate being 10/10 successful conversions on
Hemma through the tunnel workflow.

## PR Scope

- Add a harness runner that can:
  - submit jobs for a directory of PDFs,
  - poll until completion (or record `running`),
  - fetch results and write outputs,
  - emit a JSON summary suitable for `docs/reference/` appendices.
- Add a reference report describing:
  - corpus path used (must be external to this repo),
  - success/failure counts,
  - latency distribution (p50/p90/p99),
  - backend/acceleration usage split,
  - any OCR retries and warnings.
- Document Hemma tunnel run commands (non-invasive, reproducible).
- Extend CLI with explicit background-first flows if needed by the harness:
  - `submit`, `status`, `collect` (no synchronous assumptions).

## Deliverables

- [ ] Harness runner script and smoke/unit tests for deterministic output structure.
- [ ] `docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json` (machine-readable evidence).
- [ ] `docs/reference/ref-production-pdf-md-scientific-corpus-validation.md` (human-readable report).
- [ ] Documented Hemma tunnel invocation that can be replayed by other developers/agents.

## Acceptance Criteria

- [ ] Evidence uses this exact external corpus path (do not vendor PDFs into this repo):
  - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- [ ] Hemma tunnel acceptance run converts 10/10 PDFs successfully, with artifacts and summary committed.
- [ ] Evidence artifacts include:
  - service revision (git SHA),
  - backend and acceleration usage,
  - normalization mode used (width 100 strict strong-reflow when strict selected),
  - any retries and warnings.
- [ ] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
