---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-06-30'
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
- Task 366 is completed for STT lazy-load/idle-unload: `docs/backlog/tasks/task-366-implement-stt-sidecar-lazy-model-load-and-idle-unload.md`.
- Task 367 is completed, reviewed, deployed, and live-proved at `873c5ae1`; proof summary is `build/verification/task-367-stt-sidecar-idle-unload-live-proof/20260628T203221Z/summary.json`, with post-idle `/health` returning `models_resident=false` at `2026-06-28T20:50:02Z` and no strict `audio_sidecar_unavailable`/`unload_model` log matches.
- Task 368 is completed, reviewed, deployed, and live-proved at
  `0c2184e0`; proof summary is
  `build/verification/task-368-idempotency-live-proof/20260629T003205Z/summary.json`.
  The live proof created a real retryable failed job through the Service API,
  then proved service-owned `service_reattempt` admission and successful
  `transcript_json` fetch without idempotency pointer edits. Task 369 may now
  remove the Task 63 CLI-side failed-replay auto-rerun wrapper.
- Task 369 and Task 371 are completed, reviewed, deployed, and live-proved at
  `65a04e4a`. Task 369 removed the Task 63 caller-side failed-replay
  auto-rerun wrapper; Task 371 exposed the audio transcript-bundle route and
  closed the accepted public browser/Gateway proof path. Retained proof:
  `build/verification/task-371-public-browser-audio-cli-proof/20260629T082206Z/summary.json`.
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
  Story 58 is in progress; Tasks 375-379 are approved. Task 379 adds
  `pdm run proof:story58-live-replay` for redacted story-level Service API
  replay bundles. Latest downstream Skriptoteket product proof passed: prod
  `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0337-correction-session-live/20260630T110339Z/manifest.json`;
  Dev `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0337-correction-session-live/20260630T111643Z/manifest.json`.
  Final closeout remains story-level: run real Dev/Prod Service API proof
  manifests, prove the same-owner stale incompatible production replay through
  the product identity that owns the retained stale records, and retain closeout
  review before marking complete.
- Active public-edge recovery/follow-up tasks: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md` and `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active dependency-image cleanup task: `docs/backlog/tasks/task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds.md`.

## Conversion Remediation

- Epic 06 is the active long-PDF reliability, progress, and throughput epic:
  `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`.
- Formula and OCR carry-forward remains in Tasks 342-348 and 350. Preserve the
  owner split: Task 342 for CLI/replay visibility, Task 343 for decisioning,
  Task 345 for source-backed formula authority, and Tasks 346-350 for specialist
  OCR/runtime evidence.

Durable formula-lane findings are retained in `.codex/long-term-memory/entries/session-2026-06-13-handoff-trimmed-formula-history.md`; active carry-forward remains Task 345 for source-backed formula authority, Task 342 for safe authority metadata, and Task 343 for later decisioning.

## Next Actions

1. Run the separate Story 58 closeout with
   `docs/reference/ref-story-58-live-proof-operator-manifest-contract.md` and
   `pdm run proof:story58-live-replay --case-manifest <manifest>` for Dev/Prod
   service evidence plus consumer proof/review. Do not mark complete before full matrix evidence exists.
1. Task 365 is closed; do not reopen proxy, timeout, trust-key, or dedicated sidecar approaches without new governed evidence and explicit user approval.
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
- Task 359-364 retained red/green evidence lives in task docs and Reviews
  45-49.
- Task 365 detailed validation and native/local proof evidence is retained in
  its task doc and linked long-term entry; active warning: do not revive the
  rejected dedicated remote-proof STT sidecar.
- Task 368 validation and live-proof evidence is retained in its task doc and
  Review 52; do not reintroduce caller-side idempotency salting or auto-rerun
  remediation.
- Task 369/371 final validation is retained in task docs, Reviews 54, 55, 57,
  and the public proof summary.
- Task 376 is approved in Review 61. Red: stale/missing/drifted DigiExam
  successes strict-replayed (`3 failed, 4 passed`). Green: `14 passed`,
  broader `112 passed`, targeted ruff passed.
- Task 377 is approved in Review 62. Missing-source red returned `200 OK`;
  Review 62 missing-grant red returned `auth_missing_internal_identity_grant`;
  remediation green focused suite passed `36 passed, 1 warning`;
  `coverage-gate` passed `1784 passed, 6 skipped`; targeted ruff passed.
- Task 378 is approved in Review 63. Red: artifact-set tests failed `4 failed, 1 warning` on missing typed references and missing request-id conflict.
  Green: focused/preservation/OpenAPI suite `45 passed, 1 warning`; OpenAPI
  `4 passed`; coverage-gate `1788 passed, 6 skipped`, coverage `95.54%`.
- Task 379 proof-runner support is implemented and Review 64 approved; latest
  local audit passed focused proof-runner tests `9 passed`, targeted Ruff/mypy,
  docs/skills/handoff validation, and `git diff --check`. Partial Dev/Prod
  generic smoke and prod `ak7` lineage are retained under `build/verification/story-58-*`;
  full matrix still needs private Story 58 manifest inputs. Current downstream
  product proof used Sir Convert service revision
  `ef2284b3b9d6dc7cb1f403939c0581c9ee7d7c61` in both Dev and Prod. Do not rerun
  generic smoke as closeout.
- Final local gate refresh after helper return-type repairs passed:
  `format-all`, `lint-fix`, `typecheck-all`, `coverage-gate`, `docs-sync`,
  `docs-validate`, `skills-validate`, `handoff-validate`, and `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
