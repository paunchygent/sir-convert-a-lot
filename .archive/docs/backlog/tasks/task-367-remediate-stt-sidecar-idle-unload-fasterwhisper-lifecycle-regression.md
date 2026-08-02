---
id: task-367-remediate-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression
title: Remediate STT sidecar idle unload FasterWhisper lifecycle regression
type: task
status: completed
priority: high
created: '2026-06-28'
last_updated: '2026-06-28'
related:
  - docs/backlog/epics/epic-12-speech-to-text-audio-ingestion-and-transcript-delivery.md
  - docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md
  - docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md
  - docs/reference/ref-stt-proof-lanes-and-admission-operations.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - stt
  - sidecar
  - lazy-load
  - idle-unload
  - production-remediation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remediate the production STT sidecar regression introduced by Task 366's lazy
model idle-unload path. The deployed sidecar must stay healthy after resident
FasterWhisper and pyannote models become idle, and the next
`audio -> transcript_bundle` job must execute instead of failing with
`audio_sidecar_unavailable`.

Production RCA on 2026-06-28:

- Newest failed job:
  `jobv2_07aeba71c1eb4bcf884196b1b5`, source
  `Ny inspelning 45.m4a`, created and failed at `2026-06-28T19:53:46Z`.
- Admission was bounded and successful: Gateway proxied
  `POST /sir-convert/v2/convert/jobs?wait_seconds=0`, and Sir Convert returned
  `202 Accepted` in `169 ms`.
- The GPU worker then claimed the job and failed during sidecar availability
  probing. The job manifest terminal error was
  `audio_sidecar_unavailable`, `reason=sidecar_http_status`,
  `status_code=500`, `retryable=true`.
- `sir_convert_a_lot_stt_sidecar` health was failing with
  `AttributeError: 'WhisperModel' object has no attribute 'unload_model'`
  from `scripts/sir_convert_a_lot/stt_sidecar/model_lifecycle.py`.
- The immediately previous production audio job
  `jobv2_c012132cdbb2435c8874f88a35`, source `Ny inspelning 44.m4a`,
  succeeded at `2026-06-28T19:32:46Z`, so the failure class is idle-unload
  lifecycle drift, not upload admission or a general STT outage before idle
  cleanup.

## PR Scope

- Keep the Task 366 lazy-load and idle-unload product goal: sidecar readiness
  must not require heavyweight models to be resident at startup.
- Replace the non-existent FasterWhisper `WhisperModel.unload_model()` call with
  cleanup that matches the real FasterWhisper 1.2.1 / CTranslate2 4.8.0 public
  runtime surface.
- Preserve concurrency protections: no idle unload while model-using work is
  active, and simultaneous first-use calls still share one lazy load.
- Make `/health` and worker sidecar-availability probes resilient after idle
  timeout while still failing closed for genuine GPU, cache, or secret
  precondition failures.
- Update fake model fixtures so tests would have caught the production
  mismatch: the default fake FasterWhisper model must not expose
  `unload_model()`.
- Do not change public proxy timeout, body size, trust keys, production ingress,
  audio admission semantics, route policy, GPU-required policy, STT model ids,
  quantization, or CPU fallback.

## Deliverables

- [x] Focused red-first regression test that fails with the current
  `unload_model` call when the fake FasterWhisper model has no such method.
- [x] Production lifecycle fix for idle unload, shutdown cleanup, and health
  idle-unload triggering.
- [x] Focused STT sidecar tests and quality gates.
- [x] Retained Review 51 artifact with independent ruthless review approval.
- [x] Hemma deployment and live production proof showing sidecar health recovers
  and a post-idle `audio -> transcript_bundle` job succeeds.
- [x] Updated `.codex/handoff.md` with exact validation and live proof paths.

## Acceptance Criteria

- [x] `LoadedSttModels.unload()` and lifecycle cleanup do not depend on
  `WhisperModel.unload_model()` or any undocumented FasterWhisper method.
- [x] Calling `runtime.health()` after the idle timeout drops resident model
  references, returns ready health when preconditions are still satisfied,
  and does not make `/health` return `500`.
- [x] Shutdown cleanup remains idempotent and does not throw when models are
  resident.
- [x] Existing sidecar behavior is preserved for `/probe-media`,
  `/capabilities`, first transcription/diarization lazy load, active-use
  protection, and batched FasterWhisper execution.
- [x] Review 51 is approved after the reviewer verifies behavior, typing,
  docs-as-code state, and missing-test risk.
- [x] Live Hemma proof after deploy includes bounded logs or manifests showing:
  sidecar `/health` returns `200`, Docker health is healthy, a real
  production `audio -> transcript_bundle` job reaches `succeeded`, result
  and `transcript_json` artifact fetch succeed, and no new
  `audio_sidecar_unavailable`/`unload_model` errors appear in the proof
  interval.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Red-First Evidence

- Red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py -q`
  failed with `2 failed, 3 passed` after the default fake FasterWhisper model
  stopped exposing `unload_model()`. The failing paths were
  `test_idle_unload_waits_for_active_model_work_and_shutdown_drops_references`
  and `test_health_triggers_idle_unload_after_elapsed_timeout`; both raised
  `AttributeError: 'FakeWhisperModel' object has no attribute 'unload_model'`
  from `LoadedSttModels.unload()`.

## Implementation Notes

- `LoadedSttModels` no longer calls a backend-native unload hook. The lifecycle
  manager releases resident FasterWhisper, batched pipeline, and pyannote
  references by clearing its loaded model bundle only when no model-using work
  is active.
- The shared lazy-lifecycle fake FasterWhisper model and direct STT runtime
  fakes no longer expose `unload_model()`, so health-triggered idle unload and
  shutdown cleanup prove behavior against the real FasterWhisper public surface.
- Context7 check on 2026-06-28: FasterWhisper documents `WhisperModel` loading
  and transcription but no `unload_model()` method; CTranslate2 memory guidance
  documents deleting model objects as the public resource-release path.

## Green Validation Evidence

- Focused lifecycle proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py -q`
  passed with `5 passed`.
- Focused Task 366 STT lifecycle/runtime/HTTP/compose/readiness proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`
  passed with `47 passed`.
- `pdm run format-all` passed with `943 files left unchanged`.
- `pdm run typecheck-all` passed with
  `Success: no issues found in 894 source files`.
- `pdm run lint-fix` initially failed only because generated docs indexes were
  stale after adding Task 367. After `pdm run docs-sync`, `pdm run lint-fix`
  passed with `All checks passed!`, `943 files left unchanged`,
  `Validated docs=564 rules=11`, and `Validated 488 backlog files`.
- `pdm run coverage-gate` reached the coverage threshold
  (`95.37%`) but exited failed with `9 failed, 1732 passed, 6 skipped` because
  unrelated Qwen durable-checkpoint tests refused to save on the current local
  filesystem headroom (`free_bytes` about `27.4 GB` versus
  `required_free_bytes=30064771072`). All STT sidecar tests in the full run
  passed.

## Review Evidence

- Independent retained Review 51:
  `docs/backlog/reviews/review-51-ruthless-review-of-task-367-stt-sidecar-idle-unload-fasterwhisper-lifecycle-regression.md`
  is approved.
- Reviewer-run focused STT proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_stt_sidecar_lazy_lifecycle.py tests/sir_convert_a_lot/test_stt_sidecar_batched_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_media_runtime.py tests/sir_convert_a_lot/test_stt_sidecar_http_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_audio_transcription_sidecar_readiness.py -q`
  passed with `47 passed`.
- Reviewer-run `pdm run typecheck-all`, `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check` passed.

## Hemma Deployment And Live Proof Evidence

- Deployed and verified commit
  `873c5ae183a9aa7b9cd6ecb6fd63426eace293bd` with
  `pdm run hemma-deploy-and-verify --expected-revision 873c5ae183a9aa7b9cd6ecb6fd63426eace293bd --lane host`.
  Report:
  `build/verification/hemma-deploy-verify/report.md`, generated at
  `2026-06-28T20:28:52Z`, status `passed`, with expected, remote, and service
  revisions all matching `873c5ae183a9aa7b9cd6ecb6fd63426eace293bd`.
- Live production transcript proof:
  `build/verification/task-367-stt-sidecar-idle-unload-live-proof/20260628T203221Z/summary.json`.
  The proof observed `ready=true`, `service_profile=prod`, and
  `service_revision=873c5ae183a9aa7b9cd6ecb6fd63426eace293bd`, then completed
  job `jobv2_db9a0d46ace646188cc6340a90` with `status=succeeded`,
  `backend_used=stt_sidecar`, `acceleration_policy_requested=gpu_required`,
  `acceleration_used=rocm`, and `pipeline_used=audio_to_transcript_bundle_v2`.
- Artifact proof: the proof manifest reported `transcript_json=available`; the
  fetched transcript JSON contained `27` segments and speaker labels
  `SPEAKER_00` and `SPEAKER_01`.
- Health proof: Docker reported `sir_convert_a_lot_stt_sidecar` as
  `Up ... (healthy)` after the live job. The post-idle sidecar `/health` poll
  at `2026-06-28T20:50:02Z` returned `ready=true`, `gpu_ready=true`, and
  `models_resident=false`, proving idle cleanup no longer makes health fail.
- Bounded production log scans since `2026-06-28T20:29:00Z` for both
  `sir_convert_a_lot_stt_sidecar` and `sir_convert_a_lot_prod` returned no
  strict matches for `audio_sidecar_unavailable`, `unload_model`,
  `AttributeError`, `Internal Server Error`, or sidecar/prod `500` failure
  signatures in the proof interval.

## Residual Follow-Up

- No Task 367 remediation follow-up remains. The only known residual is the
  unrelated local `coverage-gate` Qwen durable-checkpoint free-space failure
  recorded above; it did not affect STT sidecar coverage or live production
  proof.
