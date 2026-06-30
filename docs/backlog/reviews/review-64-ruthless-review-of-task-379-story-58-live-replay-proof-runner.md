---
id: review-64-ruthless-review-of-task-379-story-58-live-replay-proof-runner
title: Ruthless review of Task 379 Story 58 live replay proof runner
type: review
status: completed
priority: high
created: '2026-06-30'
last_updated: '2026-06-30'
related:
  - docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md
  - docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md
  - docs/backlog/reviews/review-62-ruthless-review-of-task-377-correction-source-job-fail-closed.md
  - docs/backlog/reviews/review-63-ruthless-review-of-task-378-correction-replay-artifact-sets.md
labels:
  - review
  - approved
  - task-379
  - story-58
  - live-proof
  - service-api-v2
---

Retained independent review for Task 379. This reviewer did not author the
implementation or tests, did not deploy, did not commit, and did not modify
production or test implementation files. The only intentional Sir Convert
mutation from this review pass is this retained review artifact plus generated
docs index updates from validation.

## Review Scope

Authorities and instructions read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
- `docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md`
- `docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md`
- `docs/backlog/reviews/review-62-ruthless-review-of-task-377-correction-source-job-fail-closed.md`
- `docs/backlog/reviews/review-63-ruthless-review-of-task-378-correction-replay-artifact-sets.md`

Reviewed Task 379 surfaces:

- `.codex/handoff.md`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
- `pyproject.toml`
- `scripts/sir_convert_a_lot/devops/run_story58_live_replay_proof.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_evidence.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_manifest.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_models.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_report.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof.py`

Public/runtime surfaces affected:

- Operator command `pdm run proof:story58-live-replay`.
- Retained Story 58 proof evidence under
  `build/verification/story-58-live-replay-proof/<timestamp>/`.
- Dev/Prod closeout classification for the Story 58 proof matrix.

Out-of-scope pre-existing worktree dirtiness observed but not approved:

- `docker/service-deps/service-dependency-inputs-cpu.json`
- `docker/service-deps/service-dependency-inputs-rocm.json`
- `docker/service-deps/service-requirements.txt`
- `pdm.lock`

## Findings

### High: Matrix cases can pass without Story 58 invariant proof

`scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py:190` marks a
case `passed` after every request satisfies only the optional manifest
`expect` fields and an optional artifact-set relationship check. The actual
expectation validator at
`scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py:265` checks
`http_status`, `error_code`, `idempotency_state`, `idempotency_reason`, and
`route_id` only when the manifest author declares those fields. There is no
case-specific validator keyed by `Story58CaseId`.

This lets an operator manifest mark Story 58 matrix cases as `passed` with an
under-specified expectation. For example, a
`stale_incompatible_digiexam_replay` request can pass on `http_status: 200`
without proving `idempotency.state = service_reattempt` and
`idempotency.reason = terminal_artifact_contract_incompatible`. A compatible
strict replay can pass without proving `strict_replay`, and
`missing_source_correction_apply_fail_closed` can pass without proving the
specific fail-closed error envelope. That violates Task 379 acceptance, which
says these cases are passed only from the real Service API response metadata,
not from operator-declared loose expectations.

Why it matters: this is a false-proof path. The runner can produce a
decision-grade Story 58 closeout bundle that says `passed` while the live
Service API response still has stale strict replay, the wrong correction error,
or only a generic 2xx/4xx status.

Required fix shape: add runner-owned, case-specific validators for every
`Story58CaseId`. The manifest may add stricter expectations, but it must not be
able to weaken the Story 58 invariant. At minimum:

- `compatible_strict_digiexam_replay` must prove strict replay metadata on the
  DigiExam route.
- `stale_incompatible_digiexam_replay` must prove `service_reattempt` plus
  `terminal_artifact_contract_incompatible`.
- `missing_source_correction_apply_fail_closed` must prove the governed 409
  error code.
- duplicate and distinct correction apply cases must prove the request-level
  artifact-set relationship and successful typed references.
- stale/mismatched nested artifact download must prove the governed 404/409
  error code.
- generic smoke must either prove a safe live case or remain an explicit
  skipped external-command pointer.

Proof required: add focused tests where each matrix case returns the wrong
metadata while the manifest expectation is loose, and assert the runner marks
the case `failed`. Then rerun:

```bash
/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q
```

### Medium: Readiness/runtime identity failure does not affect overall status

`scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py:91` records
`/readyz`, but `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_manifest.py:144`
derives `overall_status` solely from case statuses. A failed/non-JSON
readiness response or a missing `service_revision` can still yield an overall
`passed` summary if the case expectations pass.

Why it matters: Story 58 retained proof is supposed to identify the live
Service API revision being proven. A proof bundle that passes while runtime
identity is unknown is not decision-grade evidence and can hide deployment or
URL mistakes.

Required fix shape: fail closed, or at least mark the run `failed`, when
`/readyz` is not a successful JSON object with the expected safe readiness and
revision fields. If some environments intentionally omit `service_revision`,
make that a governed explicit degraded state and prevent `passed` overall
status.

Proof required: add a focused test where `/readyz` returns 500 or omits
`service_revision` while cases otherwise pass, and assert the summary cannot be
`passed`. Then rerun:

```bash
/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q
```

### Medium: Docs overstate Task 379 approval and closeout readiness

`docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md:5`
marks the task `completed`, and the story/handoff text says the final local
gate refresh happened after task approval before an independent retained review
approved this slice. With the proof-runner findings above, those docs now
overstate Task 379 status and approval state.

Why it matters: Story 58 closeout depends on retained proof truth. Docs that
claim approval before review can cause the next operator to treat a blocked
proof runner as accepted evidence.

Required fix shape: after the runner fixes land, update Task 379, Story 58,
`.codex/handoff.md`, and generated indexes so they distinguish implemented,
reviewed, approved, and remaining Dev/Prod proof states truthfully.

Proof required: rerun:

```bash
/opt/homebrew/bin/pdm run docs-sync
/opt/homebrew/bin/pdm run docs-validate
/opt/homebrew/bin/pdm run handoff-validate
git diff --check
```

## Checklist

- [x] Governing Story 58, Task 379, Reviews 60-63, skills, and targeted rules
  read.
- [x] Current worktree status and known unrelated dirt inspected.
- [x] New proof-runner files, command surface, docs/handoff updates, and focused
  tests audited.
- [x] Tests audited under the testing skill for proof truthfulness.
- [x] Focused proof-runner test rerun.
- [x] Decision recorded in retained review artifact.

## Non-Blocking Observations

The module split is a real responsibility split rather than line-count theater:
CLI parsing, orchestration, manifest handling, transport, evidence redaction,
models, and report rendering are separated, and all reviewed Task 379 modules
are below 500 lines.

The retained-redaction test is useful and catches raw exam content, API key,
idempotency key, raw grants, signatures, private paths, provider prompts, and
the repaired `crset_...` log-capture shape. It is not sufficient as Story 58
matrix truth because it does not test loose or missing matrix expectations.

## Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py -q`
  passed: `2 passed`.
- `rg -n "proof:story58-live-replay|story58-live-replay|story58_live_replay" pyproject.toml docs/backlog/INDEX.md docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md .codex/handoff.md`
  confirmed the command surface and docs references.
- `wc -l` over the seven Task 379 proof-runner source modules and focused test
  confirmed each reviewed module stays below 500 lines.

Validation not rerun by this reviewer before this finding:

- Full `format-all`, `lint-fix`, `typecheck-all`, `coverage-gate`, and full
  docs closeout were not rerun because approval is blocked by the false-proof
  findings above.

## Follow-up Actions

- Fix Task 379 so runner-owned case validators enforce Story 58 matrix
  invariants independently of manifest-authored optional expectations.
- Add negative tests for loose matrix expectations and failed/missing readiness
  identity.
- Correct Task 379, Story 58, and handoff status language after the remediation
  lands and rerun docs/handoff validation.
- Story 58 Dev/Prod live proof remains blocked until Task 379 is approved.

## Pass 1 Decision

changes_requested

## Pass 1 Response

Task 379 is not approved. The command surface exists and the current focused
tests pass, but the proof runner can mark Story 58 matrix cases as passed from
under-specified manifest expectations and can pass overall without live runtime
identity. Fix those false-proof paths, add negative tests for loose
expectations and readiness failure, then rerun the focused proof-runner tests
and docs/handoff validation.

## Pass 1 Completion

Decision: `changes_requested`.

## Pass 2 Follow-Up Review

The Review 64 remediation is approved. This pass reviewed the repaired Task 379
proof-runner surface after the implementation added code-owned Story 58 matrix
invariants and readiness prerequisites.

Additional reviewed surfaces for pass 2:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py`
- Updated `scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py`
- Updated `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_manifest.py`
- Updated Task 379, Story 58, `.codex/handoff.md`, and generated backlog index

## Pass 2 Findings

No blocking findings.

The high false-proof finding is resolved. The runner now executes manifest
expectations first, then requires `case_invariant_result(...)` before a case can
be marked `passed`
(`scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py:197`,
`:206`, `:210`, `:218`). The invariant module owns every Story 58 matrix case,
including strict DigiExam replay, stale incompatible reattempt, missing-source
409, duplicate artifact-set reuse, distinct artifact sets, stale/mismatched
nested artifact download, and generic idempotency smoke
(`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py:33`,
`:40`, `:42`, `:44`, `:46`, `:48`, `:50`, `:52`). Loose manifest expectations
can no longer weaken those requirements; the focused negative tests prove wrong
strict/stale metadata and the wrong missing-source 409 now fail the proof
(`tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py:27`,
`:85`, `:90`, `:134`).

The readiness/runtime-identity finding is resolved. `/readyz` now produces a
sanitized readiness object with `status` and `reason`, and
`readiness_result(...)` requires HTTP 200, `ready=true`, and a non-empty
`service_revision`
(`scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py:95`,
`:101`, `:103`, `:104`;
`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py:57`,
`:60`, `:62`, `:64`). The summary cannot report overall `passed` when
readiness failed
(`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_manifest.py:156`,
`:165`, `:172`). The focused test proves failed readiness forces
`overall_status = failed`
(`tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py:138`,
`:179`, `:181`).

The docs-truth finding is resolved for Task 379. The task/story/handoff state
now distinguishes proof-runner support from Story 58 final closeout: Task 379 is
approved in this retained review, while Story 58 remains open until real
Dev/Prod manifests and the remaining downstream closeout proof are retained.

No new line-count theater was introduced. The new invariant module is a
domain-named proof-policy split, not static prose relocation, and all reviewed
Task 379 source/test modules remain under the repo's 400-500 line ceiling.

## Pass 2 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py -q`
  passed: `5 passed`.
- `/opt/homebrew/bin/pdm run ruff check ...` over the Task 379 proof-runner
  source and focused tests passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check ...` over the same Task 379
  files passed: `10 files already formatted`.
- `/opt/homebrew/bin/pdm run mypy --no-incremental --config-file pyproject.toml ...`
  over the same Task 379 files passed:
  `Success: no issues found in 10 source files`.
- `wc -l` over the Task 379 proof-runner source and tests confirmed all files
  remain under 500 lines.

Validation still required after this review artifact/status update:

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Follow-up Actions

- Story 58 still requires actual Dev/Prod live proof manifests for the full
  target matrix.
- This approval does not approve final Story 58 closeout, deployment, or
  downstream consumer proof.
- The unrelated dirty Docker service dependency files and `pdm.lock` remain
  out of scope for Task 379 review.

## Decision

approved

## Response

Task 379 is approved on pass 2. The proof runner now has code-owned Story 58
invariants that cannot be weakened by loose operator manifests, failed
readiness blocks overall pass status, redacted evidence remains content-safe,
and the command surface is scoped to proof collection without mutating
production idempotency or artifact state.

## Completion

Decision: `approved`.

## Pass 3 Sensitive-Header Follow-Up Review

This independent follow-up reviewed the Task 379 proof-runner sensitive-header
repair. The reviewer did not edit production or test implementation files and
did not commit or push. The only intentional mutation from this pass is this
retained review artifact.

Additional reviewed surfaces for pass 3:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_sensitive_inputs.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py`
- Updated `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
- Updated `.codex/handoff.md`

## Pass 3 Findings

No blocking findings.

The sensitive-header repair is approved. `header_env` and `headers_file_env`
are resolved only at request execution time, are not copied into the retained
summary, redacted response files, report, monitoring pointers, or log-capture
summary, and fail closed when declared private inputs are malformed or missing.
The transport keeps this as operator input resolution rather than a runtime
shim: it still calls the Service API through the same HTTP boundary and does
not alter Service API route behavior, idempotency records, artifact state, or
Story 58 case invariants.

The focused test is truthful for the follow-up risk. It exercises the public
proof-runner boundary with `httpx.MockTransport`, proves the private identity
and grant headers reach the live request, and proves the retained evidence tree
does not include the private values or private header-file path.

The docs and handoff accurately describe this as proof-runner support only.
Story 58 remains open for actual Dev/Prod live proof manifests and any still
relevant downstream consumer proof.

## Pass 3 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py -q`
  passed: `7 passed`.
- `/opt/homebrew/bin/pdm run ruff check ...` over the Task 379 proof-runner
  source and focused tests passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check ...` over the same Task 379
  files passed: `12 files already formatted`.
- `/opt/homebrew/bin/pdm run mypy --no-incremental --config-file pyproject.toml ...`
  over the same Task 379 files passed:
  `Success: no issues found in 12 source files`.
- `wc -l` over the Task 379 proof-runner source and tests confirmed all
  reviewed files remain under 500 lines.
- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=592 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

## Pass 3 Decision

approved

## Pass 3 Response

Task 379 sensitive-header follow-up is approved. The proof runner now supports
operator-private request headers through `header_env` and `headers_file_env`
without retaining private header values or paths, while inline headers remain
available for non-secret proof metadata.

## Pass 4 Response-Context Follow-Up Review

This independent follow-up reviewed the Task 379 proof-runner response-context
and interpolation repair. The reviewer did not edit production or test
implementation files and did not commit or push. The only intentional mutation
from this pass is this retained review artifact.

Additional reviewed surfaces for pass 4:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_context.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py`
- Updated `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
- Updated `docs/backlog/INDEX.md`

## Pass 4 Findings

No blocking findings.

The response-context repair is approved. Context capture happens only after the
Service API response is reduced through `redacted_response_payload(...)`, so
dependent requests can reuse approved metadata without storing raw response
bodies, exam content, signatures, private paths, identity/grant envelopes, or
provider prompts. The context stores scalar metadata only, rejects duplicate
variables and invalid extraction paths, and fails closed on missing extraction
or unresolved/malformed interpolation before a fallback request can be sent.

Interpolation is appropriately narrow for this proof-runner contract: later
request `path`, `query`, and inline `headers` values can consume extracted
metadata, while request bodies, multipart file paths, private header sources,
and Service API runtime behavior remain outside this orchestration feature.
The transport still calls the same Service API boundary, and Story 58 case
invariants remain code-owned after request expectations pass.

The focused tests are truthful for the main follow-up risks. They exercise the
public proof-runner boundary with `httpx.MockTransport`, prove a correction
apply response can feed a later nested artifact download path/query/header, and
prove unresolved placeholders abort before the HTTP layer sees the fallback
request. The happy-path test also confirms raw response-only fields are not
retained in the evidence tree.

Story 58 remains open for actual Dev/Prod live proof manifests and any still
relevant downstream consumer proof.

## Pass 4 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py -q`
  passed: `9 passed`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py scripts/sir_convert_a_lot/devops/story58_live_replay_proof_context.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py`
  passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py scripts/sir_convert_a_lot/devops/story58_live_replay_proof_context.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py`
  passed: `3 files already formatted`.
- `/opt/homebrew/bin/pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py scripts/sir_convert_a_lot/devops/story58_live_replay_proof_context.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py`
  passed: `Success: no issues found in 3 source files`.
- `rg -n "\bAny\b|cast\(|type: ignore|# noqa" ...` over the context follow-up
  source and test files found no typing or lint bypasses.
- `wc -l` over the context follow-up source and tests confirmed all reviewed
  files remain under 500 lines.

Post-artifact validation:

- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=592 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

## Pass 4 Decision

approved

## Pass 4 Response

Task 379 response-context follow-up is approved. The proof runner now supports
dependent live proof steps by extracting scalar metadata from redacted response
payloads and interpolating it into later request path/query/header values,
without retaining raw response bodies or secrets and without weakening Story 58
case invariants.

## Pass 5 Route-Key Follow-Up Review

This independent follow-up reviewed the route-key support for Story 58
proof-runner cases. The reviewer did not edit production or test
implementation files, did not commit or push, and did not mutate runtime state.
The only intentional mutation from this pass is this retained review artifact.

Additional reviewed surfaces for pass 5:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_evidence.py`
- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py`
- `docs/reference/ref-story-58-live-proof-operator-manifest-contract.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `.codex/handoff.md`

## Pass 5 Findings

### Medium: Stale reattempt route proof can still bind to `replayed_job_id`

`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py:91`
correctly starts stale incompatible proof from a `service_reattempt` response,
and the new route-key regression test rejects a route result for
`reattempt_of_job_id`. However `_idempotency_job_ids(...)` still adds
`idempotency.replayed_job_id` for every idempotency state
(`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py:176`).
For `service_reattempt`, the proof identity must be the fresh active reattempt
job, not any replayed/superseded job id. If a stale response includes a
`replayed_job_id` carrying the previous job, a later v2 `/result` response for
that previous job can satisfy `_matching_digiexam_route_proven(...)` at
`scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py:197`
and mark `stale_incompatible_digiexam_replay` passed.

Why it matters: the follow-up is meant to make stale incompatible replay proof
decision-grade. Passing because route metadata matched a superseded job would
recreate the false-proof path this slice is closing, especially for the
production stale-reattempt proof still needed for Story 58.

Required fix shape: make the accepted job-id set state-specific. For
`service_reattempt`, bind route proof only to `idempotency.active_job_id` and
the response `job.job_id` when it represents that same active job; do not accept
`replayed_job_id`, `reattempt_of_job_id`, or `previous_attempts` as route-proof
identities. Keep `replayed_job_id` only for `strict_replay` if it is needed
there.

Proof required: add a focused route-key regression where the service reattempt
response has `active_job_id = jobv2_new`, `replayed_job_id = jobv2_old`, and
`reattempt_of_job_id = jobv2_old`, while the result route metadata is fetched
for `jobv2_old`; the case must fail. Then rerun:

```bash
/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py -q
```

## Pass 5 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py -q`
  passed: `2 passed`.
- Current code review inspected the route-key redaction and route-proof
  invariant paths listed above. The focused test proves
  `reattempt_of_job_id` is rejected, but it does not cover the
  `service_reattempt` plus `replayed_job_id` stale-id case.

Post-artifact validation:

- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=593 rules=11`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

Validation not rerun by this reviewer before this finding:

- Full `format-all`, `lint-fix`, `typecheck-all`, `coverage-gate`,
  and `skills-validate` were not rerun because approval is blocked by the stale
  route-proof finding above.

## Pass 5 Decision

changes_requested

## Pass 5 Response

Task 379 route-key follow-up is not approved yet. The runner now retains v2
`route_key` evidence and rejects `reattempt_of_job_id` route proof, but the
stale reattempt invariant still accepts `replayed_job_id` as a matching route
identity for `service_reattempt`. Tighten the invariant to the active reattempt
job id and add the focused stale-id regression before using this as Story 58
stale incompatible replay proof.

## Pass 6 Route-Key Remediation Review

This independent follow-up reviewed the remediation for the Pass 5 stale
reattempt route-key finding. The reviewer did not edit production or test
implementation files, did not commit or push, and did not mutate runtime state.
The only intentional mutation from this pass is this retained review artifact.

Additional reviewed surfaces for pass 6:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_invariants.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py`

## Pass 6 Findings

No blocking findings.

The Pass 5 stale route-proof finding is resolved. Stale incompatible replay now
collects route-proof identities only from `idempotency.active_job_id` on
`service_reattempt` responses, and the stale invariant calls
`_matching_digiexam_route_proven(...)` with `allow_state_only_match=False`.
That keeps the proof bound to the fresh active reattempt job and prevents a v2
result route response for a previous `replayed_job_id`, `reattempt_of_job_id`,
or `previous_attempts` entry from satisfying the stale case.

Strict replay keeps the broader id collection and state-only match path, which
is appropriate for the existing strict replay proof shape where create-job
responses may carry strict replay metadata directly and route metadata may
arrive on a separate result response for the same replayed job.

The focused regression is truthful: it drives the public proof-runner boundary
with a service reattempt response containing `active_job_id = jobv2_new`,
`replayed_job_id = jobv2_old`, and `reattempt_of_job_id = jobv2_old`, then
supplies DigiExam `route_key` metadata only for `jobv2_old`; the case remains
`failed`.

Story 58 remains open for actual Dev/Prod live proof manifests and the full
matrix. This approval covers the Task 379 route-key proof-runner follow-up
only, not final Story 58 closeout.

## Pass 6 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py -q`
  passed: `6 passed`.
- `rg -n "\bAny\b|cast\(|type: ignore|# noqa" ...` over the route-key
  follow-up source and test files found no typing or lint bypasses.

Post-artifact validation:

- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=593 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

## Pass 6 Decision

approved

## Pass 6 Response

Task 379 route-key follow-up is approved. The proof runner now retains v2
`route_key` result metadata without weakening code-owned invariants, and stale
incompatible `service_reattempt` proof is bound to the active reattempt job id
rather than any superseded job id.

## Pass 7 Multipart Transport Follow-Up Review

This independent follow-up reviewed the Task 379 multipart transport repair
after the live production Story 58 generic proof had failed with Service API
`422` responses. The reviewer did not edit production or test implementation
files, did not commit or push, and did not mutate runtime state. The only
intentional mutation from this pass is this retained review artifact.

Additional reviewed surfaces for pass 7:

- `scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py`
- `tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`
- `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `.codex/handoff.md`
- Referenced retained proof:
  `build/verification/story-58-live-replay-proof-prod-current-generic-7a32/20260630T160411Z/summary.json`

## Pass 7 Findings

No blocking findings.

The multipart transport repair is approved. The proof runner now sends
`job_spec` as a multipart text form part via `files={"job_spec": (None, job_spec_text)}` instead of mixing a separate `data` field with multipart
files or adding a per-part content type. That matches the live create-job route
shape, where `job_spec` is a `Form(...)` string and the upload is an
`UploadFile`.

The current `httpx` multipart documentation confirms that a tuple with
filename `None` is encoded as a form field rather than a file part and omits
the per-part content-type header when no explicit content type is supplied.
The reviewed change uses that shape for `job_spec` while preserving the
uploaded source file's filename and content type.

The focused regression is truthful for the production failure mode. It drives
the proof-runner transport boundary through `httpx.MockTransport`, verifies
the API key reaches the request, rejects `job_spec` parts with a filename or
per-part `Content-Type`, and only returns `200` for the multipart body shape
accepted by the live Service API route. This would have caught both incident
variants: `job_spec` outside the multipart form body and `job_spec` encoded as
a file-like part.

The docs and handoff are truthful about proof scope. The retained production
generic proof at
`build/verification/story-58-live-replay-proof-prod-current-generic-7a32/20260630T160411Z/summary.json`
proves readiness on revision `7a32e47857019b2c0077c0976e573c7d928aa1a9` plus
generic `fresh_admission` followed by `strict_replay`, but its overall status
remains `requires_governed_setup`; it is not represented as final Story 58
matrix closeout. The retained proof scan showed only approved operational
metadata such as job ids, idempotency state, timestamps, service revision,
relative evidence paths, and content-safe labels.

Story 58 remains open for the stale incompatible DigiExam replay proof and the
remaining Prod/full correction matrix closeout. This approval covers the Task
379 multipart proof-runner transport follow-up only, not final Story 58
acceptance.

## Pass 7 Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_story58_live_replay_proof.py tests/sir_convert_a_lot/test_story58_live_replay_proof_invariants.py tests/sir_convert_a_lot/test_story58_live_replay_proof_sensitive_headers.py tests/sir_convert_a_lot/test_story58_live_replay_proof_context.py tests/sir_convert_a_lot/test_story58_live_replay_proof_route_key.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py -q`
  passed: `12 passed`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`
  passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`
  passed: `2 files already formatted`.
- `/opt/homebrew/bin/pdm run mypy scripts/sir_convert_a_lot/devops/story58_live_replay_proof_transport.py tests/sir_convert_a_lot/test_story58_live_replay_proof_transport.py`
  passed: `Success: no issues found in 2 source files`.
- `rg -n "\bAny\b|cast\(|type: ignore|# noqa|RequestFileValue|job_spec" ...`
  over the transport follow-up source and test files found no typing or lint
  bypasses and confirmed the old `RequestFileValue` import is gone.
- `jq` over the retained production generic proof summary confirmed
  `overall_status = requires_governed_setup`, readiness `status = passed`,
  service revision `7a32e47857019b2c0077c0976e573c7d928aa1a9`, and one passed
  generic idempotency smoke case with two live requests.
- `rg` over the retained production generic proof bundle for raw secret,
  identity/grant, signature, private path, source-text, provider, and
  wait-seconds markers found no forbidden retained material; matches were
  limited to approved metadata such as idempotency fields, relative evidence
  paths, and content-safe labels.

Post-artifact validation:

- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 516 backlog files` and `Validated docs=593 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

## Pass 7 Decision

approved

## Pass 7 Response

Task 379 multipart transport follow-up is approved. The proof runner now sends
create-job `job_spec` in the Service API's live multipart form shape, the
regression test proves the incident boundary, retained docs keep the production
generic proof scoped as partial evidence, and no Story 58 proof-contract or
redaction blocker was found.
