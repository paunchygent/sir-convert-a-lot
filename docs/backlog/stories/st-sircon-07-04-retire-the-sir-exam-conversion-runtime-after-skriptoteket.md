---
type: story
id: ST-SIRCON-07-04
title: Retire the Sir exam-conversion runtime after Skriptoteket cutover
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-30'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: spec-verifier (Pi c24293c0-e3fc-4150-b5d8-6557b3aac055)
  decided_at: '2026-10-01T00:10:25+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Verified the complete ST-SIRCON-07-04 story slice at afabb8ee against S1-S5 and TASK-SIRCON-07-04-01 T6/T8 user decisions (2026-09-30); no open findings. Approved retirement, REP-0030 and REP-0032 rereviews and retained service (216 tests), speech (299 tests), conversion/OCR/workload (89 tests) and compose/workload (57 tests) evidence support the preserved generic boundary and exam-surface removal. Parent may close the story and reconcile stale live-proof wording; no deploy, Hemma or live proof was required or run because production/STT stay offline. Accepted residual risk: old same-key fingerprints may conflict until normal expiry; actual volume migration and restart-image availability remain unproven future-start dependencies. Retained review: .orchestration/context/sessions/01a0f366-a539-743a-8ee1-9b99e06d1157/evidence/reviews/st-sircon-07-04-verifier-review.md.'
epic: EPIC-SIRCON-07
acceptance_criteria:
  - After both Skriptoteket consumers have cut over, Sir Convert contains no exam-specific runtime, route, config, secret, test, or current documentation authority while generic document conversion, OCR, STT, job lifecycle, artifacts, workers, and offload remain.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

Retire Sir Convert's exam-conversion product surface after Skriptoteket has
taken ownership of both authenticated and public Exam Converter execution.
Remove DigiExam parsing, exam-authoring and correction state, Exam.net exports,
answer-key completion, public grants and leases, exam routes, and the config,
secrets, tests, scripts, and current docs that exist only for those capabilities.

Keep Sir Convert as the estate's generic conversion platform. PDF, DOCX, HTML,
Markdown, OCR, audio, speech-to-text, generic asynchronous jobs, artifacts,
workers, sidecars, and offload remain supported.

## Contract Inputs

- Skriptoteket `ST-SKRIPT-39-03`, including completed Tasks 01 and 02 and the
  cross-repository retirement owned by Task 03.
- HuleEdu `TASK-HULE-01-04-13`, which retires the former public grant authority
  while preserving HuleEdu's generic protected Sir edge.
- Current Sir exam modules, route branches, generated OpenAPI declarations,
  deployment configuration, secrets, tests, scripts, and current docs are the
  removal inventory. Closed historical backlog records remain historical.
- The generic Sir route table and runtime architecture define the preserved
  product boundary.

## Tasks

- `TASK-SIRCON-07-04-01`: remove the retired exam domain and runtime while
  preserving the generic platform.

## Verification

The owning task runs the affected generic conversion, OCR, speech, job,
artifact, worker, and documentation gates through the `service`, `speech`, and
`operations` check scopes; the exam check scope is removed with the exam
runtime. Sir Convert production and speech-to-text are intentionally offline by
user decision (2026-09-30), so no Hemma deploy or live check runs. Before any
future restart, the operator runs the one-time retired-spec-fields migration
from the service-operations runbook, then the live generic conversion and
speech-to-text checks.

## Decided Contract Terms

| ID  | Decided contract term                                                                                    |
| --- | -------------------------------------------------------------------------------------------------------- |
| S1  | Sir exam conversion is retired because both Skriptoteket consumers now execute locally.                  |
| S2  | Generic document conversion, OCR, STT, jobs, artifacts, workers, sidecars, and offload remain Sir-owned. |
| S3  | Mixed generic modules lose only exam branches; shared lifecycle and artifact behavior remain.            |
| S4  | Retirement leaves no compatibility route, adapter, dormant exam config, or fallback.                     |
| S5  | Qwen sidecar retirement belongs to Skriptoteket Task 04 and is outside this story.                       |
