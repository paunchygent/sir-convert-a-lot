---
id: task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus
title: Scientific-paper workload evidence harness + Hemma tunnel acceptance report (10/10 corpus)
type: task
status: in_progress
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

Lock evaluation priority for this task:

1. Layout fidelity + information retention + legibility.
1. Stability/reliability under realistic workload conditions.
1. Latency/throughput as secondary tie-breakers.

## Decision Lock (2026-02-14)

1. Topology:
   - Use dual-lane execution:
     - acceptance lane (production-lock tunnel path),
     - evaluation lane (A/B backend comparison).
1. Acceptance lane profile (governance-compatible default):
   - `backend_strategy=auto`
   - `ocr_mode=auto`
   - `table_mode=accurate`
   - `normalize=standard`
   - `acceleration_policy=gpu_required`
1. Evaluation lane profiles:
   - Docling:
     - `backend_strategy=docling`
     - `ocr_mode=auto`
     - `table_mode=accurate`
     - `normalize=standard`
     - `acceleration_policy=gpu_required`
   - PyMuPDF:
     - `backend_strategy=pymupdf`
     - `ocr_mode=off`
     - `table_mode=accurate`
     - `normalize=standard`
     - `acceleration_policy=cpu_only`
1. Artifact policy:
   - Commit full A/B markdown outputs for reproducible manual quality review.
1. Decision policy:
   - If quality winner conflicts with production governance constraints, keep governance-compatible
     production recommendation and record follow-up decision/task.

## Execution Plan

1. Add Task 12 harness module and evaluation-only service entrypoint.
1. Add deterministic output schema/report generation and artifact writing.
1. Add unit tests for ordering, metrics, lane behavior, decision tie-breakers, and report sections.
1. Run local quality/docs gates and targeted Hemma lane runs.
1. Commit evidence JSON/report/artifacts and close-out docs updates.

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
- [ ] Evaluation service entrypoint for isolated A/B runs (`serve:sir-convert-a-lot-eval`).
- [ ] `docs/reference/benchmark-pdf-md-scientific-corpus-hemma.json` (machine-readable evidence).
- [ ] `docs/reference/ref-production-pdf-md-scientific-corpus-validation.md` (human-readable report).
- [ ] Documented Hemma tunnel invocation that can be replayed by other developers/agents.
- [ ] Committed markdown artifacts for acceptance + A/B lanes.

## Acceptance Criteria

- [ ] Evidence uses this exact external corpus path (do not vendor PDFs into this repo):
  - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`
- [ ] Hemma tunnel acceptance run converts 10/10 PDFs successfully, with artifacts and summary committed. All resulting .mds are high quality and pass manual review for accuracy, completeness, and formatting.
- [ ] Backend decision for scientific PDFs is explicitly quality-first:
  - A/B comparison is recorded for available backend paths on the same 10/10 corpus.
  - Primary ranking metric is layout fidelity + information retention + legibility.
  - Latency/throughput are used only as secondary criteria when quality is materially equivalent.
- [ ] Evidence artifacts include:
  - service revision (git SHA),
  - backend and acceleration usage,
  - normalization mode used (width 100 strict strong-reflow when strict selected),
  - any retries and warnings.
- [ ] Selected backend path remains governance-compatible:
  - no silent policy bypasses,
  - deterministic validation behavior for incompatible options,
  - truthful conversion metadata (`backend_used`, `acceleration_used`, `ocr_enabled`).
- [ ] Quality gates pass (format/lint/typecheck/tests + docs validators and backlog index).

## Checklist

- [ ] Docs kickoff updated (`status: in_progress`, decision lock, execution plan)
- [ ] Harness and eval service implementation complete
- [ ] Tests added and passing
- [ ] Local quality gates complete
- [ ] Hemma acceptance + evaluation runs complete
- [ ] Evidence JSON/report/artifacts committed
- [ ] Close-out docs updated
