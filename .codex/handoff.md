---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-14'
---

## Purpose

Keep volatile Sir Convert-a-Lot state, blockers, validation evidence, and next
actions. Durable session history lives in `.codex/long-term-memory/entries/`;
durable implementation authority lives in governed docs.

## Current State

- Generated docs doorway is `docs/index.md`; durable session history starts at
  `.codex/long-term-memory/entries/session-2026-06-05-handoff-compaction.md`.
  STT, formatter, and formula-lane history is compacted under
  `.codex/long-term-memory/entries/`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active Gateway cutover lane: `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Task 361 is implemented and marked completed:
  `docs/backlog/tasks/task-361-consume-huleedu-internalidentitycontextv1-trust-profile-and-acceptance-smoke.md`.
  Sir Convert now consumes HuleEdu sanitized internal-identity trust profiles
  through typed runtime config, compares active key canonical DER SPKI
  fingerprint to the profile fingerprint, and uses the profile key id,
  issuer, audience, TTL, and skew in the existing verifier path. Local/prod
  compose require sanitized `HULEEDU_INTERNAL_IDENTITY_TRUST_PROFILE_JSON`.
  Acceptance smoke is content-safe test-material proof only; no live HuleEdu
  signed headers were retained.
- Active speech-to-text lane: Epic 12; ADR-0013 accepted; Story 53 JSON
  runtime is live after accepted Tasks 355, 356, and 357 plus Reviews 41-43.
- Task 366 is active for HuleEdu TASK-0814 STT lazy-load/idle-unload:
  `docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md`; Worker A self-verified with `33 passed`, review pending.
- STT production remediation Task 362 is completed:
  `docs/backlog/tasks/task-362-use-batched-fasterwhisper-inference-in-production-stt-sidecar.md`.
  The production sidecar now requires FasterWhisper
  `BatchedInferencePipeline`, passes `batch_size=8` during chunk transcription,
  exposes sanitized `/capabilities` truth with
  `backend_family=faster_whisper` and `batch_size=8`, and pins prod compose
  `SIR_STT_SIDECAR_BATCH_SIZE=8`. RCA: the observed 34-second first response
  was not solved by Gateway timeout alone; production must use batched
  inference.
- Task 363 fast replay architecture remediation is completed, approved in
  independent Review 48, committed, pushed, redeployed, and live-verified on
  Hemma:
  `docs/backlog/tasks/task-363-fast-transcript-formatter-replay-lane-outside-heavy-conversion-queue.md`.
  Durable closeout details are retained in
  `.codex/long-term-memory/entries/session-2026-06-14-task-363-fast-replay-closeout.md`.
  Downstream contract summary: admitted `wait_seconds=0` replay jobs
  terminalize synchronously as `succeeded` or fail-closed `failed` under the
  existing `/v2/convert/jobs` lifecycle and no longer dispatch through the
  generic heavy conversion worker queue.
  Skriptoteket `PR-0350` has consumed the contract and passed final
  authenticated live proof at
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0349-transcript-parity-live/20260614T030725Z/proof-summary.json`.
- Task 364 truthful STT progress/timing is completed and accepted in Review
  49; see task/review docs for full evidence. The audio `job.progress`
  contract adds
  `audio_pipeline_percent_complete` and `audio_pipeline_eta_seconds`, emits
  `diarizing` before blocking diarization, and persists canonical audio phase
  timings. The Skriptoteket PR-0351 field handoff is recorded in
  `docs/converters/downstream_integration_contract_v2.md`.
- Task 365 is complete:
  `docs/backlog/tasks/task-365-fence-remote-proof-trust-lane-and-remove-create-job-multipart-replay.md`.
  Current implementation removes create-job multipart parser replay after
  upload binding and adds the fenced Hemma `remote-proof` compose lane for
  local-auth Skriptoteket proof. Remote-proof uses
  `/home/paunchygent/.data/sir-convert-a-lot/remote-proof/remote-proof.env`
  on Hemma, `compose.remote-proof.yaml`, and `pdm run remote-proof-*`; it must
  stay separate from production `hemma-production` trust settings and public
  ingress. The current STT proof fix must use the existing hosted Hemma STT
  sidecar through the shared `sir-convert-a-lot-stt-sidecar-inputs` volume;
  do not reintroduce a dedicated remote-proof STT sidecar.
  The 2026-06-14 production upload failure was pinned to slow Sir Convert audio
  admission, not HuleEdu CORS/trust or a proxy setting: retained-job capacity
  checks called `runtime.get_job()` per job, and that API sweeps expired jobs at
  entry. Task 365 now includes the bounded-admission fix and the reference doc
  `docs/reference/ref-stt-proof-lanes-and-admission-operations.md`.
  Later formatter export failure is separate: remote-proof API fast-lane replay
  wrote artifacts while worker recovery reset the non-dispatching
  `transcript_json -> transcript_bundle` job back to `queued`; v2 recovery now
  requeues only generic-runtime routes.
  Local downstream proof passed at
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0349-transcript-parity-live/20260614T184817Z/proof-summary.json`.
  Sir Convert production is deployed at `159e82d5`; native Hemma production
  STT proof passed at
  `/home/paunchygent/apps/skriptoteket/.artifacts/playwright-pr-0352-transcript-parity-native/20260614T191738Z/proof-summary.json`.
  Downstream `REV-PR-0352` approved the local-first and native-production-second
  proof evidence, including formatter recovery and remote-proof lane fixes.
- Story 54 / Task 358 is complete and accepted in Review 44. Product-neutral
  TXT, Markdown, WebVTT, and SRT artifacts are implemented over validated
  canonical `transcript_json`; downstream apps own product meaning, durable
  saves, filenames, and workflow-specific derivatives.
- Story 56 plus Tasks 359/360 are implemented for overlay-aware transcript
  formatter replay. Service API v2 now supports
  `transcript_json -> transcript_bundle` over uploaded canonical
  `transcript_json_v1`, strict `transcript_formatter_replay_v1` options,
  closed requested artifacts `txt|md|vtt|srt`, typed
  `speaker_label_overrides`, and returned `transcript_txt`/`md`/`vtt`/`srt`
  named artifacts. Replay does not emit `transcript_json`; `/result` returns
  metadata for the primary `transcript_replay_bundle_manifest.json` artifact,
  while singular `/artifact` streams the content-safe
  `transcript_formatter_replay_result_v1` manifest body. No bespoke endpoint,
  downstream formatter, source-audio replay, or Gateway rewriting is part of
  the contract.
- Active exam artifact conversion/authoring lane: `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
- Active public-edge recovery/follow-up tasks: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md` and `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active dependency-image cleanup task: `docs/backlog/tasks/task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds.md`.

## Conversion Remediation

- Epic 06 is the active long-PDF reliability, progress, and throughput epic:
  `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`.
- Task 342 owns CLI live progress, manifest, idempotent replay, and recovery
  visibility:
  `docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md`.
- Task 343 owns PDF conversion decision logic and GPU/CPU performance
  attribution:
  `docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md`.
- Task 344 owns the Docling/Granite formula VLM generation-stability root
  cause:
  `docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md`.
- Task 345 owns source-layer formula authority for born-digital PDFs and must
  align implementation with Task 342 user feedback and Task 343 conversion
  decisioning:
  `docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md`.
- Task 346 owns the pre-infrastructure specialist formula/OCR candidate
  evaluation on the established Task 344 incident pages/crops and is completed:
  `docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md`.
- Task 347 owns the Hemma runtime-enablement evidence for PaddleOCR and
  DeepSeek-OCR-2:
  `docs/backlog/tasks/task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay.md`.
- Task 348 owns the native PaddleOCR/PaddleX AMD GPU container probe for
  formula recognition:
  `docs/backlog/tasks/task-348-probe-paddleocr-vl-and-paddlex-amd-gpu-container-support-for-formula-recognition-on-hemma.md`.
- Task 350 owns the governed DeepSeek-OCR-2 HF eager Task 346 replay:
  `docs/backlog/tasks/task-350-integrate-deepseek-ocr-2-hf-eager-candidate-replay-for-task-346.md`.

Durable formula-lane findings are retained in
`.codex/long-term-memory/entries/session-2026-06-13-handoff-trimmed-formula-history.md`.
Active carry-forward: Task 345 owns source-backed formula authority, Task 342
presents safe authority metadata, and Task 343 consumes it for later
decision/performance work.

## Next Actions

1. Task 365 is closed; do not reopen proxy, timeout, trust-key, or dedicated
   sidecar approaches without new governed evidence and explicit user approval.
1. Keep downstream transcript work on saved canonical `transcript_json`,
   accepted producer artifacts, and governed Gateway routes; do not revive
   browser-owned Sir Convert replay/download sagas.
1. Formula/PaddleOCR/DeepSeek carry-forward remains in the linked task docs and
   long-term memory entries; do not reopen rejected runtime lanes without new
   governed evidence.

## Validation

- Durable validation history is in the governed task/review docs. STT runtime
  acceptance is recorded in Reviews 40-43. Task 358 formatter acceptance is
  recorded in Review 44 after the `specs_v2.py` module split.
- Task 359-362 retained red/green evidence lives in their task docs and
  Reviews 45-47; Task 361 covers HuleEdu trust-profile consumption and Task
  362 covers batched FasterWhisper production STT sidecar remediation.
- Task 363 and Task 364 red/green/review evidence is retained in their task and
  review docs; Task 363 Review 48 and Task 364 Review 49 are approved.
- Task 365 evidence on 2026-06-14 so far: admission replay red test failed at
  `interfaces/http_routes_jobs_v2.py:254` on the second `request.form()` call;
  remote-proof compose contract initially failed because the lane did not
  exist; focused green proof passed with `6 passed`; `format-all`,
  `typecheck-all`, `lint-fix`, `docs-sync`, `docs-validate`,
  `skills-validate`, `handoff-validate`, and `git diff --check` passed before
  Hemma deployment prep. Later local STT E2E proof through `hemma-remote-proof`
  passed trust preflight but failed media probing because the borrowed
  production STT sidecar could not see the remote-proof data volume
  (`jobv2_e6e21993b1d7415681ececc4ed`, `audio_stream_missing`,
  `sidecar_status_code=422`). A rejected dedicated remote-proof STT sidecar
  then failed with GPU memory pressure and must not be retained. The current
  shared-staging fix removes that sidecar, stages audio into
  `sir-convert-a-lot-stt-sidecar-inputs`, and keeps the existing hosted STT
  sidecar as the only model worker. Red shared-staging proof failed with
  `9 failed, 15 passed`; focused green proof passed with `24 passed`; broadened
  Task 365 proof passed with `43 passed`; `coverage-gate` passed with
  `1733 passed, 6 skipped` and `95.37%` coverage. The retained-job capacity
  red test failed with repeated `JobStoreV2.sweep_expired` calls during audio
  admission; the fixed route now scans direct job-store subjects and focused
  proof passed with `1 passed`, then `44 passed` for the audio admission/parser
  replay plus evidence-helper slice. Formatter recovery proof failed red with
  `202 Accepted`, then passed with `1 passed`; adjacent proof passed with
  `35 passed`. Local downstream proof passed at
  `20260614T184817Z`; native Hemma production proof passed at
  `20260614T191738Z` with container logs retained under
  `/home/paunchygent/apps/skriptoteket/.artifacts/pr-0352-native-proof-logs/20260614T191737Z/`.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
