---
type: task
id: TASK-SIRCON-07-04-01
title: Remove the retired Sir exam-conversion domain and runtime
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-30'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Delete the retired DigiExam, exam-authoring, Exam.net, answer-key, correction, and public-grant runtime and remove only their branches from shared job and artifact surfaces; preserve generic conversion, OCR, STT, job lifecycle, artifacts, workers, and offload.
story: ST-SIRCON-07-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Delete the exam-only DigiExam, exam-authoring, Exam.net QTI/PDF/DOCX,
answer-key provider, correction replay, public-grant, public-access, and lease
code. Remove their HTTP and CLI registrations, generated API declarations,
tests, proof scripts, deployment configuration, secrets, and current docs.

Where exam behavior shares a module with generic conversion, remove only the
exam route, spec, inference, executor, or artifact branch. Keep generic job
creation, status, cancellation, replay, artifacts, conversion routing, OCR,
audio, STT, worker, sidecar, and offload behavior. Do not add compatibility
surfaces or retain dormant exam branches.

## Contract Inputs

- `ST-SIRCON-07-04` decided terms S1-S5.
- The cross-repository inventory retained by Skriptoteket Task 03.
- HuleEdu `TASK-HULE-01-04-13` for removal of the paired public grant authority.
- Sir's current generic service route table and generated OpenAPI contract as
  the preserved API boundary.

## Core Vertical And Performance

The deleted exam vertical starts at exam-specific public and protected routes,
passes through exam specifications and source inference, and ends in exam
parsers, authoring state, answer-key providers, and Exam.net renderers. Removing
it must reduce route and runtime branching without changing the generic
conversion execution model or adding work to generic requests.

## Validation

- Inspect the named `exam` check plan and run `pdm run check exam`.
- Run affected generic service, conversion, OCR, speech, job, artifact, worker,
  and offload tests needed to prove their preserved behavior.
- Regenerate and validate OpenAPI after removing exam routes and schemas.
- `pdm run docs-sync`, `pdm run docs-validate`, and `git diff --check`.
- After merge, deploy the exact published revision to Hemma and complete live
  generic document-conversion and speech-to-text checks.

## Stop Conditions

- A current consumer still calls an exam-specific Sir route.
- Removing a mixed branch would change a generic route, artifact, job,
  conversion, OCR, speech, worker, sidecar, or offload contract.
- A named exam configuration or secret is shared by a generic capability.
- The change enters Qwen sidecar retirement, which belongs to Skriptoteket
  Task 04.

## Decided Contract Terms

| ID  | Decided contract term                                                                    |
| --- | ---------------------------------------------------------------------------------------- |
| T1  | Delete exam-only modules and remove only exam branches from mixed generic modules.       |
| T2  | Preserve generic conversion, OCR, STT, jobs, artifacts, workers, sidecars, and offload.  |
| T3  | Remove exam routes, schemas, config, secrets, tests, scripts, and current docs together. |
| T4  | Do not preserve adapters, aliases, fallbacks, or dormant exam code.                      |
| T5  | Qwen cleanup is excluded and remains owned by Skriptoteket Task 04.                      |
