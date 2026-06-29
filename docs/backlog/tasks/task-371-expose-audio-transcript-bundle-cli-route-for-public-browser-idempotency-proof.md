---
id: task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof
title: Expose audio transcript bundle CLI route for public browser idempotency proof
type: task
status: in_progress
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/reference/ref-stt-proof-lanes-and-admission-operations.md
labels:
  - cli
  - audio
  - transcript-bundle
  - v2
  - idempotency
  - public-proof
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Expose the existing Service API v2 `audio -> transcript_bundle` route through
the Sir Convert CLI/client surface so the accepted Task 368 retryable-failed
precondition can be created and replayed by a current CLI/client path.

This task exists because Task 369 removed the historical caller-side
failed-replay auto-rerun behavior, but its final live proof cannot be completed
truthfully while the CLI supports only document conversion routes. The known
safe retryable failure precondition is the audio/STT sidecar-unavailable lane;
document-route retryable failures would require perturbing production GPU,
dependency, or timeout behavior and are not accepted proof paths.

The goal is not to change Service API v2 retry semantics. The goal is to make
the already-governed audio transcription route reachable from the CLI/client
surface and to define a retained public browser proof that demonstrates one
create-job submission from that caller path, followed by service-owned
Task 368 reattempt handling.

## PR Scope

- Add CLI route support for local audio/video inputs that map to
  `source.format = "audio"` and `conversion.output_format = "transcript_bundle"` using the existing Service API v2 job lifecycle.
- Reuse the current audio transcription contract for request shape, including
  GPU-required execution, `retention.pin=false`, and product-neutral transcript
  artifact selection.
- Extend CLI file discovery, route listing, help text, job-spec construction,
  deterministic idempotency-key derivation, output path handling, and manifest
  recording for the audio transcript-bundle route.
- Keep Task 369's invariant: one CLI/client conversion invocation submits one
  create-job request and records only the job returned by the service.
- Add a retained public browser proof harness shape that exercises the live
  production/public HuleEdu Gateway browser surface, not the direct service
  host or local Hemma tunnel. The proof must be browser-scripted and must
  retain evidence that the browser/client path produced exactly one
  `POST /sir-convert/v2/convert/jobs` for the replay invocation, plus
  correlated downstream Sir Convert create-job evidence.
- Use the known safe Task 368 precondition path only if it can be created
  through real service APIs and permitted runtime operation. Do not edit,
  delete, quarantine, or fabricate idempotency pointers or job records.
- Update CLI and converter docs to describe audio transcript-bundle CLI usage
  and to keep service-owned retryable-failed reattempt semantics normative.
- Do not mutate Gateway or Skriptoteket, introduce caller-side retry wrappers,
  change canceled-job semantics, add DB/queue migrations, or perturb
  document-route production GPU/dependency/timeout behavior.

## Deliverables

- [x] Red-first CLI route test proving current behavior rejects or lacks the
  `audio -> transcript_bundle` route.
- [x] CLI/client implementation for audio and video-with-audio source files
  using the existing Service API v2 audio transcription request contract.
- [x] Manifest and artifact-output behavior that reports only the
  service-returned job and product-neutral transcript bundle artifacts.
- [x] Tests proving the audio CLI route submits once, derives a stable
  idempotency key for the logical request, handles service-owned
  `service_reattempt` metadata, and does not introduce a caller-side rerun
  path.
- [x] CLI/converter docs synchronized for audio transcript-bundle usage,
  supported extensions, expected artifacts, and Task 368 idempotency behavior.
- [x] Browser-proof plan or harness drafted for overseer review before live
  execution, with Gateway public browser surface, credential handling, request
  counting, downstream Sir Convert correlation, evidence files, and bounded
  service-log collection described.
- [ ] Retained public live proof after deploy, only if the accepted proof
  harness can create the retryable-failed precondition without forbidden state
  edits or out-of-scope runtime perturbation.

## Acceptance Criteria

- [x] `convert-a-lot routes` exposes an implemented audio transcript-bundle
  route without broadening document-route semantics.
- [x] The CLI can submit supported audio/video inputs to Service API v2 as
  `audio -> transcript_bundle` and fetch the resulting transcript bundle
  artifacts through the existing result/artifact endpoints.
- [x] The CLI/client performs no failed-replay remediation, key salting, or
  second-submit compatibility rerun. Explicit independent new-job intent, if
  available, remains separate from retry remediation.
- [x] CLI manifests remain truthful for audio jobs: they record the
  service-returned job id, status, output path or artifact metadata, and
  relevant idempotency state without hiding extra submissions.
- [x] Focused tests prove service-owned retryable-failed reattempt metadata is
  accepted from the service response and represented truthfully by the CLI.
- [ ] Public live proof uses the HuleEdu Gateway public browser surface rather
  than `127.0.0.1`, a local Hemma tunnel, private-only endpoints, or the
  direct Sir Convert service host.
- [ ] Browser proof evidence includes:
  - deployed service revision including Task 368 and deployed CLI/client
    revision including Task 369 and this task;
  - scripted browser/client transcript of the public create-job replay
    invocation;
  - browser or network instrumentation showing exactly one
    `POST /sir-convert/v2/convert/jobs` from the caller path for the replay
    invocation, plus correlated downstream Sir Convert create-job evidence;
  - service idempotency metadata showing `service_reattempt` for the
    retryable-failed lineage;
  - terminal succeeded job and artifact fetch evidence;
  - bounded public/service logs showing no CLI-side compatibility rerun in the
    proof interval.
- [ ] If the browser proof cannot safely create the retryable-failed
  precondition through real public APIs and accepted runtime operations, stop
  and record the exact mismatch instead of weakening proof or fabricating
  state.

## Red-First Test Plan

First failing proof:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py::test_audio_transcript_bundle_route_is_cli_visible -q
```

Expected red behavior before implementation: the CLI route registry has no
audio source format and no `audio -> transcript_bundle` route.

Focused green proof should include:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q
```

Broader close-out gates for the implementation task:

```bash
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
pdm run coverage-gate
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

## Browser Proof Shape

The retained live proof must be designed before execution and reviewed as part
of this task. The proposed harness shape is:

1. Use a content-safe audio fixture and the HuleEdu Gateway public browser
   surface for Sir Convert: `/sir-convert/v2/convert/jobs`.
   Direct `https://convert.hule.education` requests are operator/direct-service
   evidence only and cannot close this browser proof or the Task 369 live gate.
1. Create the retryable-failed precondition only through real Service API calls
   and accepted runtime operation for the audio route.
1. Restore the accepted runtime condition, then trigger the replay through the
   browser-scripted CLI/client proof path. The harness must use the deployed
   public client bundle or public-browser-driven client surface under review,
   not `127.0.0.1`, a Hemma tunnel, a private-only endpoint, or direct
   `convert.hule.education` browser traffic.
1. Capture browser/network evidence that the replay step emitted exactly one
   `POST /sir-convert/v2/convert/jobs`; accepted evidence includes a Playwright
   network event log plus Gateway and downstream Sir Convert correlation ids
   for the same request.
1. Capture the service response body showing Task 368
   `idempotency.state = "service_reattempt"` and lineage to the retryable
   failed attempt.
1. Poll/fetch through the public surface until the job succeeds and retain
   result plus named transcript artifact proof.
1. Retain bounded service logs for the proof interval and scan for caller-side
   rerun/key-salting indicators.

Evidence bundle location should be a timestamped ignored directory under
`build/verification/task-371-public-browser-audio-cli-proof/` containing:

- browser/network transcript with request count, public Gateway URL, and
  correlation id;
- create-job request/response redacted JSON for the replay invocation;
- downstream Sir Convert create-job correlation evidence for the same Gateway
  request;
- manifest/output artifact proof showing only the service-returned job;
- result and named `transcript_json` artifact fetch proof;
- bounded service logs and search terms for rerun/key-salting indicators.

Stop before implementation if this proof shape requires Gateway/Skriptoteket
mutation, private tunnel substitution, document-route runtime perturbation, or
manual idempotency/job state edits.

## Implementation Evidence

- Red-first evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py::test_audio_transcript_bundle_route_is_cli_visible -q`
  failed before production edits because `convert-a-lot routes` did not list
  `audio -> transcript_bundle`.
- Same-node green evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py::test_audio_transcript_bundle_route_is_cli_visible -q`
  passed after route registration.
- Focused green evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed with `21 passed`.
- Legacy route-registry sync evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py::test_routes_command_lists_supported_routes_in_stable_order -q`
  passed with `1 passed` after updating the deterministic route-list
  expectation for the new audio route.
- Broad green evidence:
  `pdm run coverage-gate` passed with `1752 passed, 6 skipped` and total
  coverage `95.53%`.
- Safe governance gates passed locally: `pdm run typecheck-all`,
  `pdm run validate-tasks`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- `pdm run docs-validate` and the docs-validation phase of `pdm run lint`
  remain blocked by the already-dirty generated
  `docs/backlog/INDEX.md`. `pdm run docs-sync` was not run because it would
  mix Task 371 index regeneration with unrelated Task 367/370 generated-index
  drift in the shared working tree.

This implementation does not execute deploy or live proof. Task 369 remains
open until the public browser proof is reviewed, deployed, run, and retained.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
