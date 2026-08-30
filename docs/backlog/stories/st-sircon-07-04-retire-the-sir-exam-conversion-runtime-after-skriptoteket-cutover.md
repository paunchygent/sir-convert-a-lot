---
type: story
id: ST-SIRCON-07-04
title: Retire the Sir exam-conversion runtime after Skriptoteket cutover
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-30'
status: active
closeout_review:
  record: inline
  status: not_started
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

The owning task runs the exam removal check together with the affected generic
conversion, OCR, speech, job, artifact, worker, and documentation gates. After
integration, Hemma must run the exact published revision and complete live
generic document-conversion and speech-to-text checks without any exam route or
exam-only deployment configuration remaining.

## Decided Contract Terms

| ID  | Decided contract term                                                                                    |
| --- | -------------------------------------------------------------------------------------------------------- |
| S1  | Sir exam conversion is retired because both Skriptoteket consumers now execute locally.                  |
| S2  | Generic document conversion, OCR, STT, jobs, artifacts, workers, sidecars, and offload remain Sir-owned. |
| S3  | Mixed generic modules lose only exam branches; shared lifecycle and artifact behavior remain.            |
| S4  | Retirement leaves no compatibility route, adapter, dormant exam config, or fallback.                     |
| S5  | Qwen sidecar retirement belongs to Skriptoteket Task 04 and is outside this story.                       |
