---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-07-04'
---

## Purpose

Keep volatile Sir Convert-a-Lot state, blockers, validation evidence, and next
actions. Durable session history lives in `.codex/long-term-memory/entries/`;
durable implementation authority lives in governed docs.

## Current State

- TASK-SIRCON-REP-0021 is done and independently approved. Root tests use the
  seven behavior-owned directories; collection remains 1,444 items and the
  seven representative files pass 97 tests. The separate derived-quality task
  is next.
- Generated docs doorway is `docs/index.md`; durable session history starts at
  `.codex/long-term-memory/entries/session-2026-06-05-handoff-compaction.md`.
  STT, formatter, and formula-lane history is compacted under
  `.codex/long-term-memory/entries/`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- R2 job-artifact storage planning is accepted/completed in `ADR-0014`, Story
  59, Task 380, Review 65, and
  `REF-cloudflare-r2-job-artifact-storage-migration-pre-runbook`. The approved
  first implementation boundary is terminal/cold artifact blobs only: primary
  terminal artifacts and route-owned named terminal bundle artifacts behind a
  Sir-owned adapter. Raw inputs, resources, manifests, events, idempotency
  state, locks, active scratch/work dirs, partials, checkpoints, logs,
  correction replay artifact sets, prod env sync, object copy/backfill,
  cleanup, and raw/presigned R2 browser URLs remain unauthorized until later
  governed tasks. Task 381 is scaffolded as the proposed first implementation
  task for that terminal/cold artifact adapter and authorized streaming proof
  boundary.
- Active Gateway cutover lane: `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Completed STT/idempotency history is governed in Tasks 358-371 and Reviews
  40-57. Key live-proof pointers remain Task 367
  `build/verification/task-367-stt-sidecar-idle-unload-live-proof/20260628T203221Z/summary.json`,
  Task 368 `build/verification/task-368-idempotency-live-proof/20260629T003205Z/summary.json`,
  and Task 371 `build/verification/task-371-public-browser-audio-cli-proof/20260629T082206Z/summary.json`.
  Do not revive caller-side failed-replay reruns, browser-owned Sir Convert
  replay/download sagas, or the rejected dedicated remote-proof STT sidecar.
- Active exam artifact conversion/authoring lane: `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
  Story 58 is in progress; Tasks 375-379 are approved. Task 379 adds
  `pdm run proof:story58-live-replay` for redacted story-level Service API
  replay bundles. Latest prod Gateway proof
  `.artifacts/playwright-pr-0337-correction-session-live/20260630T154502Z/manifest.redacted.json`
  used real `ak7_lag_och_ratt_with_image.dxe`, retained service logs, proved
  PDF/QTI download and Save `200`, and mismatched artifact `409`. Current
  Service API proof on deployed `e49cb9ef`/`7a32e478`: Dev real-DXE strict replay
  `build/verification/story-58-live-replay-proof-dev-digiexam-real/20260630T133051Z/summary.json`;
  Dev/Prod generic `story-58-live-replay-proof-{dev,prod}-e49-generic` plus
  prod current generic `...prod-current-generic-7a32/20260630T160411Z`. Dev
  correction rows now have live Service API evidence: duplicate/mismatch
  `...correction-matrix/20260630T150721Z`, distinct
  `...correction-distinct/20260630T151122Z`, missing-source
  `...correction-missing-source/20260630T151411Z`, plus a fresh missing-source
  rerun on current `7a32e478` at
  `build/verification/story-58-live-replay-proof-dev-missing-source-current/20260630T170436Z/summary.json`.
  A current Dev full-manifest rerun with regenerated internal headers proved
  compatible strict replay but failed the captured correction rows with owner
  access denials; those rows require fresh browser-owner headers or new product
  capture, not API-key-only or internal-identity substitution. Stale replay
  proof current-state artifact
  `build/verification/story-58-prod-stale-replay-current-state/20260630T171951Z/summary.json`
  shows the retained projected prod stale rows are now absent from the prod
  idempotency volume; rerunning them would produce fresh admission. Final story
  closeout still needs a new unexpired same-owner stale replay plus Prod/full
  matrix `overall_status=passed`; API-key-only Prod correction proof needs
  owner-matching signed headers. Production Skriptoteket `20260630T154502Z`
  also proves the user-route duplicate final correction request digest,
  final `crset_167617d2fede86c0a774ff2c10bbf67b` download/save, and
  mismatch `409`, but not a second distinct production artifact set.
- Active public-edge recovery/follow-up tasks: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md` and `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active dependency-image cleanup task: `docs/backlog/tasks/task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds.md`.

## Conversion Remediation

- Epic 06 is the active long-PDF reliability, progress, and throughput epic:
  `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`.
- Formula/OCR carry-forward remains in Tasks 342-348 and 350: preserve the owner split across CLI/replay visibility, decisioning, source authority, and specialist OCR/runtime evidence.

Durable formula-lane findings are retained in `.codex/long-term-memory/entries/session-2026-06-13-handoff-trimmed-formula-history.md`; active carry-forward remains Task 345 for source-backed formula authority, Task 342 for safe authority metadata, and Task 343 for later decisioning.

## Next Actions

1. Run the separate Story 58 closeout with `docs/reference/ref-story-58-live-proof-operator-manifest-contract.md` and `pdm run proof:story58-live-replay --case-manifest <manifest>` for Dev/Prod service evidence plus consumer proof/review. Do not mark complete before full matrix evidence exists.
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
  focused proof-runner route-key follow-up suite passed `6 passed`; multipart
  transport follow-up test passed `1 passed`. Current
  `e49cb9ef`/`7a32e478` partial live proof: Dev real-DXE compatible strict replay
  `20260630T133051Z`; Dev/Prod generic `20260630T133156Z`/`20260630T133223Z`;
  Dev correction rows `20260630T150721Z`/`151122Z`/`151411Z`; prod Gateway
  proof `20260630T154502Z`; prod generic `20260630T160411Z`. Prod `ak7`
  lineage remains filesystem-only evidence; full matrix still needs private inputs or a signed owner-header lane.
- Latest local gate refresh after the route-key proof-runner follow-up passed:
  focused proof-runner route-key suite `6 passed`; `format-all` `983 files left unchanged`; `lint-fix` passed; `typecheck-all` passed over `934 source files`; `coverage-gate` `1799 passed, 6 skipped`, coverage `95.54%`.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence.
- Stop before changing service runtime, Hemma deploy, artifact retention, or provider experiment semantics without governed task authority.
- Do not cancel or abort live conversions as part of formula-quality work.
