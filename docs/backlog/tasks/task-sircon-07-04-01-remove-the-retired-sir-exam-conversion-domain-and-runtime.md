---
type: task
id: TASK-SIRCON-07-04-01
title: Remove the retired Sir exam-conversion domain and runtime
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-30'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-09-30T22:22:19+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Independent review requested changes F1-F5; repairs 9ec42dd8 and a7f89f3c cleared F1 and F3-F5; T6 amended by user decision in 00a4c6c6 and implemented in 74a32254; independent rereview (Pi invocation 6dc1d6f3) approved with no open findings. No Hemma deploy or live proof per T8. Retained session 01a0f366-a539-743a-8ee1-9b99e06d1157 evidence/reviews/sir-exam-retirement-independent-review.md.'
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

- The named `exam` check cohort is removed with the exam runtime; run the
  owning `service`, `speech`, and `operations` check scopes instead.
- Run affected generic service, conversion, OCR, speech, job, artifact, worker,
  and offload tests needed to prove their preserved behavior.
- Regenerate and validate OpenAPI after removing exam routes and schemas.
- `pdm run docs-sync`, `pdm run docs-validate`, and `git diff --check`.
- Sir Convert production and its speech-to-text workflow are intentionally
  offline by user decision on 2026-09-30, so this task runs no Hemma deploy
  and no live check. Preserved generic behavior is proven by the tests above
  plus HTTP-boundary tests over stored pre-retirement manifests.

## Review Repair

Independent review `sir-exam-retirement-independent-review.md` (retained
session `01a0f366-a539-743a-8ee1-9b99e06d1157`) requested changes. Admitted
findings F1-F5 are repaired on this task: F1 and F2 through the T6 migration (F2 as amended by the T6 user decision),
F3 through T7, F4 by aligning the current codemap and handoff, and F5 by
splitting `job_store_v2.py`, `test_audio_transcription_route_admission_v2.py`,
and `hemma_workload.py` under the 500-line limit.

## Stop Conditions

- A current consumer still calls an exam-specific Sir route.
- Removing a mixed branch would change a generic route, artifact, job,
  conversion, OCR, speech, worker, sidecar, or offload contract.
- A named exam configuration or secret is shared by a generic capability.
- The change enters Qwen sidecar retirement, which belongs to Skriptoteket
  Task 04.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                           |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Delete exam-only modules and remove only exam branches from mixed generic modules.                                                                                                                                                                                                                                                                              |
| T2  | Preserve generic conversion, OCR, STT, jobs, artifacts, workers, sidecars, and offload.                                                                                                                                                                                                                                                                         |
| T3  | Remove exam routes, schemas, config, secrets, tests, scripts, and current docs together.                                                                                                                                                                                                                                                                        |
| T4  | Do not preserve adapters, aliases, fallbacks, or dormant exam code.                                                                                                                                                                                                                                                                                             |
| T5  | Qwen cleanup is excluded and remains owned by Skriptoteket Task 04.                                                                                                                                                                                                                                                                                             |
| T6  | Stored pre-retirement jobs are repaired by a one-time data migration command that drops retired fields; the runtime keeps no legacy-read code. By user decision (2026-09-30) the migration neither recomputes idempotency fingerprints nor waits for or blocks on idempotency records inside their replay window; such records expire on their normal schedule. |
| T7  | The retired `artifact_language` field is removed from the published generic request contract.                                                                                                                                                                                                                                                                   |
| T8  | No Hemma deploy or live proof: Sir production and STT stay offline by user decision (2026-09-30).                                                                                                                                                                                                                                                               |
