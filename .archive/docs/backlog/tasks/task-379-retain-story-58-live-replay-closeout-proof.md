---
id: 'task-379-retain-story-58-live-replay-closeout-proof'
title: 'Retain Story 58 live replay closeout proof'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-30'
last_updated: '2026-06-30'
related:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
  - docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md
  - docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md
  - docs/backlog/reviews/review-62-ruthless-review-of-task-377-correction-source-job-fail-closed.md
  - docs/backlog/reviews/review-63-ruthless-review-of-task-378-correction-replay-artifact-sets.md
  - docs/backlog/reviews/review-64-ruthless-review-of-task-379-story-58-live-replay-proof-runner.md
  - docs/reference/ref-story-58-live-proof-operator-manifest-contract.md
labels:
  - service-api-v2
  - story-58
  - live-proof
  - replay
  - idempotency
  - correction-apply
  - redaction
---

PR-sized execution unit linked to Story 58 final closeout.

## Objective

Create the missing Story 58 live Service API replay proof support so operators
can retain one redacted Dev/Prod evidence bundle without mutating production
state, rewriting idempotency records, or widening the approved Tasks 375-378
runtime behavior.

## PR Scope

- Add a small domain-named proof runner under `scripts/sir_convert_a_lot/devops/`
  and expose it as `pdm run proof:story58-live-replay`.
- Run against an operator-supplied Service API v2 URL and API key.
- Persist redacted evidence under
  `build/verification/story-58-live-replay-proof/<timestamp>/`.
- Support the Story 58 live proof matrix by recording each case as `passed`,
  `failed`, `skipped`, or `requires_governed_setup` with a precise reason.
- Preserve only approved metadata: job ids, route id, replay action/reason,
  schema versions, request id, digests, artifact-set id/key/hash, HTTP
  status/error code, timestamps, service revision, and content-safe case
  labels.
- Do not change Service API route behavior, perform production idempotency or
  artifact surgery, synthesize failed jobs, salt keys, add browser-local
  authority, or introduce compatibility shims.

## Deliverables

- [x] `pdm run proof:story58-live-replay` writes `summary.json`, redacted
  per-case response files, artifact metadata files where present, `report.md`,
  and log capture files or explicit monitoring pointers when supplied.
- [x] Focused tests prove case classification, redacted retention, and
  fail-closed handling for unsafe preconditions.
- [x] Story 58, this task, `.codex/handoff.md`, and generated docs indexes are
  updated truthfully.

## Acceptance Criteria

- [x] Compatible strict DigiExam replay can be recorded as `passed` only from a
  real Service API response with strict replay metadata.
- [x] Stale incompatible DigiExam replay is recorded as `passed` only from a
  real `service_reattempt` response with reason
  `terminal_artifact_contract_incompatible`; otherwise it is
  `requires_governed_setup` when no safe existing stale precondition is
  supplied.
- [x] Missing-source correction apply fail-closed, duplicate correction retry,
  distinct correction applies, and stale/mismatched nested artifact download are
  either proven from real operator-supplied cases or marked
  `requires_governed_setup` without mutation.
- [x] Generic/shared idempotency preservation is recorded from a safe smoke case
  or as an explicit pointer to `pdm run hemma-verify-v2-conversions`.
- [x] Retained files do not contain raw exam content, signatures, private paths,
  secrets, idempotency keys, identity/grant envelopes, uploaded bytes, source
  text, provider prompts, or full response payloads.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Evidence

Task 379 adds `pdm run proof:story58-live-replay`, backed by a manifest-driven
Service API v2 proof runner under `scripts/sir_convert_a_lot/devops/`. The
runner executes operator-declared safe requests against a real Service API v2
URL, records every Story 58 matrix case as `passed`, `failed`, `skipped`, or
`requires_governed_setup`, and writes a timestamped evidence bundle under
`build/verification/story-58-live-replay-proof/`.

The evidence bundle includes `summary.json`, redacted per-case response files,
artifact metadata files when artifact references are present, `report.md`,
optional `monitoring-pointers.json`, and metadata-redacted log-capture files.
Manifest case requests may keep sensitive transport headers outside the
retained manifest by declaring `header_env` for per-header environment lookups
or `headers_file_env` for an environment variable that points to a private JSON
header file. Inline manifest headers remain supported for non-secret operator
metadata such as `Idempotency-Key`, but identity and grant envelopes should use
private sources.
Manifest requests may also declare metadata-only `extract` variables from the
request's redacted response payload. Later request `path`, `query`, and inline
`headers` values can interpolate those variables with `{variable_name}`. This
supports dependent proof chains such as correction apply followed by nested
artifact download without retaining raw response bodies or hand-editing
manifests. Missing extraction paths and unresolved placeholders fail closed
before a fallback request can be sent.
The runner retains only approved operational metadata and does not retain raw
exam content, signatures, private paths, secrets, idempotency keys,
identity/grant envelopes, uploaded bytes, source text, provider prompts, or
full response payloads. Log captures are redacted after the live case requests
finish so retained files can include request-time service evidence instead of
pre-run snapshots.

The runner deliberately does not create synthetic failed jobs, salt
idempotency keys, rewrite production idempotency/artifact files, perform
production artifact surgery, or change Service API route behavior. Cases that
need unsafe live state setup are marked `requires_governed_setup` with the
operator-supplied reason.

## Review State

Review 64 returned `changes_requested` for false-proof risks in the first
Task 379 implementation. The repair adds code-owned Story 58 matrix invariants
that cannot be weakened by loose manifest expectations, makes `/readyz`
runtime identity a proof prerequisite, and is approved by the Review 64 pass-2
follow-up.

### Red Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q`
  failed before implementation during collection with
  `ModuleNotFoundError: No module named 'scripts.sir_convert_a_lot.devops.story58_live_replay_proof'`.
- Repair red after retained-review inspection:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q`
  failed with `2 failed`: redacted log evidence dropped `crset_...` artifact-set
  ids, and `artifact_set_relationship="distinct"` failed when each request
  returned multiple target refs from the same artifact set.
- Review 64 repair red:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q`
  failed with `3 failed, 2 passed`: loose strict/stale replay expectations
  passed without mandatory idempotency metadata, the missing-source correction
  case passed with the wrong 409 error code, and failed `/readyz` did not force
  failed overall proof status.
- Proof-drift red after production incident review:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py::test_story58_live_replay_proof_captures_logs_after_live_requests -q`
  failed because retained log captures ran before live case requests and missed
  request-time job/artifact-set ids.
- Sensitive header-source red:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py::test_story58_live_replay_proof_loads_sensitive_headers_without_retention -q`
  failed with `KeyError: 'X-HuleEdu-Identity-Context'` because manifest-declared
  `header_env` and `headers_file_env` inputs were not loaded into the live
  request.
- Response context red:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py -q`
  failed with `2 failed`: dependent nested artifact download requests sent
  literal `{source_job_id}`, `{artifact_set_id}`, and `{content_sha256}`
  placeholders, and unresolved placeholders reached the HTTP layer instead of
  failing closed.
- Multipart transport follow-up red:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py -q`
  first failed because the proof runner sent `job_spec` outside the multipart
  text-part shape accepted by the live create-job route, then failed again
  when `job_spec` carried a per-part content type that the route treated as
  non-string upload data.

### Green Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py -q`
  passed after the proof-drift repair: `6 passed`.
- Review 64 pass-2 reviewer reran the focused proof-runner tests and targeted
  ruff/format/mypy checks; all passed.
- `/opt/homebrew/bin/pdm run ruff check ...` over the Task 379 proof runner and
  test files passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check ...` over the Task 379 proof
  runner and test files passed.
- `/opt/homebrew/bin/pdm run mypy ...` over the Task 379 proof runner and test
  files passed.
- Sensitive header-source follow-up:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py -q`
  passed: `7 passed`.
- Targeted `ruff check`, `ruff format --check`, and `mypy` over
  `story58_live_replay_proof_transport.py`,
  `story58_live_replay_proof_sensitive_inputs.py`, and
  `test_story58_live_replay_proof_sensitive_headers.py` passed.
- Response context follow-up:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py -q`
  passed: `2 passed`.
- Focused proof-runner suite after response context support:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py -q`
  passed: `9 passed`.
- Targeted `ruff check`, `ruff format --check`, and `mypy` over
  `story58_live_replay_proof.py`,
  `story58_live_replay_proof_context.py`, and
  `test_story58_live_replay_proof_context.py` passed.
- Multipart transport follow-up:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py -q`
  passed: `1 passed`.
- Log-capture regression check:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py::test_story58_live_replay_proof_captures_logs_after_live_requests -q`
  passed: `1 passed`.
- Targeted transport style/type checks:
  `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`,
  `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`,
  and
  `/opt/homebrew/bin/pdm run mypy scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`
  passed.
- Current safe Dev/Prod Service API smoke proof passed with retained response
  files and Docker log-capture summaries:
  `build/verification/story-58-live-replay-proof-dev-current/20260630T074139Z/summary.json`
  and
  `build/verification/story-58-live-replay-proof-prod-current/20260630T074211Z/summary.json`.
  Both runs proved `/readyz` plus generic `fresh_admission` followed by
  `strict_replay`; both remain `requires_governed_setup` for the full Story 58
  matrix.
- Current production generic Service API proof after the multipart transport
  follow-up passed on deployed revision
  `7a32e47857019b2c0077c0976e573c7d928aa1a9`:
  `build/verification/story-58-live-replay-proof-prod-current-generic-7a32/20260630T160411Z/summary.json`.
  It retains redacted response files plus
  `logs/sir_convert_a_lot_prod-live-wait20.redacted.log`, proving live generic
  `fresh_admission` followed by `strict_replay` for
  `jobv2_450466bdb3ec4c85bcaf01e87f`.
- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=592 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

### Remaining Story-Level Proof Work

This task supplies the retained proof runner only. Story 58 still requires
actual Dev/Prod live proof manifests for the full target matrix, including any
cases that need governed setup to safely demonstrate stale incompatible
DigiExam replay or correction replay fail-closed behavior.

Use `docs/reference/ref-story-58-live-proof-operator-manifest-contract.md` as
the final proof manifest and private-input contract. It defines the redaction
boundary, required private inputs, case matrix, and Dev/Prod command shapes
without retaining secrets or raw exam material.
