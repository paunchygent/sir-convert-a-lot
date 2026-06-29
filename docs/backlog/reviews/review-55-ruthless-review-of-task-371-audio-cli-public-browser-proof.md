---
id: review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof
title: Ruthless Review Of Task 371 Audio CLI Public Browser Proof
type: review
status: completed
created: '2026-06-29'
reviewed_task: docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md
decision: changes_requested
reviewer: codex
---

## Scope

Reviewed Task 371 changes in the main checkout only. Scope covered the governed
Task 371 document, Task 369 invariant references, current handoff, CLI/client/API
docs, and the reported CLI/client/test files for audio `transcript_bundle`
exposure.

Task 369 invariants reviewed here:

- no caller-side failed-replay retry wrapper;
- no idempotency-key salting or hidden second submit for retryable failed
  remediation;
- `--new-job` remains explicit independent user intent;
- manifests report only the service-returned job and service-returned
  idempotency metadata.

## Decision

changes_requested

The CLI/client implementation and focused tests truthfully exercise route
visibility, audio job-spec construction, one-submit behavior, and
service-returned `service_reattempt` manifest metadata. I did not find a retained
caller-side rerun wrapper or compatibility salting path in the reviewed code.

The retained public browser proof shape is not yet acceptable because it points
at the direct public service host as the proof surface, while the governed audio
contract requires browser/product traffic to enter through the HuleEdu Gateway
`/sir-convert/v2/convert/...` surface unless a separate accepted decision
changes that posture.

## Findings

### [High] Browser proof shape bypasses the governed Gateway surface

- File/line:
  `docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:158`
  and
  `docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md:163`
- Related conflicting authority:
  `docs/converters/audio-transcription-service-api-artifact-contract.md:184`
  and
  `docs/converters/audio-transcription-service-api-artifact-contract.md:778`
- Related user-facing contradiction:
  `docs/converters/sir_convert_a_lot.md:325` and
  `docs/converters/sir_convert_a_lot.md:405`

Failure mode:
Task 371's retained browser proof plan says to use the public Service API v2 URL
`https://convert.hule.education` and count `POST /v2/convert/jobs`. The audio
contract says product/browser traffic is Gateway-owned and must enter through
`/sir-convert/v2/convert/...`; it also says direct `convert.hule.education`
browser product traffic remains reserved/fail-closed unless a separate accepted
decision changes that posture. The Sir Convert docs now add an audio CLI example
using `https://convert.hule.education`, while the same document still says the
Gateway/public lane is disabled until cutover proof re-enables it.

That mismatch matters for this task because the public browser proof is the
reason Task 371 exists. A proof against the direct service host can pass while
failing to prove the accepted public browser/Gateway surface, identity forwarding,
CORS/edge behavior, and no-rewrite replay semantics. It would also risk letting
Task 369 close with weaker evidence than its live-proof gap requires.

Concrete fix:
Update the Task 371 browser-proof shape and CLI docs so browser/product proof
targets the accepted public Gateway path, including network evidence for exactly
one `POST /sir-convert/v2/convert/jobs` at the public browser surface and a
correlated downstream Sir Convert create-job request. If the intended proof is
instead a direct service-host/operator CLI proof, split that from the browser
proof and add or link the accepted decision that changes the current
fail-closed/direct-host posture before using it as Task 369 closure evidence.

Proof requirement:
Add retained reviewable evidence or tests/docs guards showing the proof harness
uses the Gateway/browser path for browser proof, preserves a single caller
submission, captures service idempotency state `service_reattempt`, and does not
rewrite idempotency pointers or job records. Re-run the focused Task 371 tests
and the docs validators once the generated index can be regenerated without
mixing unrelated Task 367/370 drift.

## Verification Evidence

Commands run:

```bash
rg -n "Task 371|task-371|audio-cli-public-browser-proof" docs/backlog/reviews docs/backlog/INDEX.md
```

Result: no existing retained Task 371 review artifact found before creating this
review.

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q
```

Result: passed, `21 passed in 0.81s`.

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py::test_routes_command_lists_supported_routes_in_stable_order -q
```

Result: passed, `1 passed in 0.57s`.

Read-only inspection confirmed:

- `scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py:399`
  performs one `convert_upload_to_artifact` call for a submitted file and builds
  the success manifest from `v2_outcome.job_id` and
  `v2_outcome.idempotency`.
- `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py:239`
  proves one audio submit, one idempotency key, service-returned
  `service_reattempt`, and no hidden extra submit at the CLI submission seam.
- `tests/sir_convert_a_lot/test_cli_v2_routes.py:411` proves audio route CLI
  visibility, source inference/job-spec shape, `gpu_required` default execution,
  output path, and service-returned idempotency metadata in the manifest.
- `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py:35` and
  `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py:145` continue to
  prove the v2 client does not synthesize a second submit for retryable-failed
  replay and accepts service-owned reattempt metadata.

## Skipped Checks And Residual Risk

- Did not run `docs-sync`; the handoff and task evidence say generated
  `docs/backlog/INDEX.md` is already dirty from unrelated Task 367/370 work, and
  this review must not mix generated-index normalization into Task 371.
- Did not run `docs-validate` or lint mutation gates because the known generated
  index drift is outside Task 371 implementation scope and the user explicitly
  restricted edits to the retained review artifact.
- Did not deploy or live-proof. Public live proof remains intentionally pending
  until the proof surface mismatch above is corrected and accepted.
