---
type: task
id: TASK-SIRCON-REP-0032
title: Type test-client responses with the httpx2 response type
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-09-30'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - The service and speech check typecheck phases pass with no httpx.Response annotation on a test-client response and no typing escape hatch
backlog_document_profile: contract-derived
---

## Implementation Contract

The FastAPI/Starlette test client now returns `httpx2.Response`, while Sir test
helpers and tests annotate its responses as `httpx.Response`. The `service` and
`speech` check typecheck phases fail on those assignments. Annotate each
test-client response with the type the client actually returns, so both
typecheck phases pass.

- Fix every reported site, including
  `tests/sir_convert_a_lot/service/http_routes_jobs_v2_edge_cases_test_support.py:133`,
  `tests/sir_convert_a_lot/service/test_create_job_admission_multipart_replay_v2.py:87`,
  `tests/sir_convert_a_lot/speech/audio_route_admission_test_support.py:85`,
  `tests/sir_convert_a_lot/speech/audio_transcript_task357_helpers.py:86`,
  `tests/sir_convert_a_lot/speech/test_audio_transcript_bundle_runtime_v2.py:685`,
  `tests/sir_convert_a_lot/speech/test_transcript_formatter_artifacts.py:326`,
  and `tests/sir_convert_a_lot/speech/test_transcript_formatter_replay_v2.py:425`.
- Change test annotations and imports only; test behavior stays the same.

## Contract Inputs

- Typecheck output from the `service` and `speech` checks retained in the Sir
  session evidence for TASK-SIRCON-07-04-01.
- Current FastAPI, Starlette, and httpx2 documentation for the test-client
  response type.

## Core Vertical And Performance

The change touches only test typing. Runtime code, the dependency set, and test
performance stay unchanged.

## Validation

- `pdm run check service` and `pdm run check speech` pass, including their
  typecheck phases.
- `pdm run docs-validate` and `git diff --check`.

## Stop Conditions

- A precise annotation needs a dependency change or a runtime code change.
- The fix would need `Any`, `cast`, or `type: ignore`.

## Decided Contract Terms

| ID  | Decided contract term                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------ |
| T1  | Each test-client response is annotated with the response type the client returns, not suppressed.      |
| T2  | Only test annotations and imports change; runtime code and dependencies stay unchanged.                |
| T3  | Authorized by the user on 2026-09-30 ("fix them") after the TASK-SIRCON-07-04-01 rereview surfaced it. |
