---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-05-18'
---

## Purpose

Keep only volatile Sir Convert-a-Lot agent state, blockers, validation evidence, and next actions. Move durable session history to `.codex/long-term-memory/entries/` and governed doctrine to docs, rules, runbooks, or skills.

## Current State

- Epic 03 / Story 05 remains the DevOps lane for Hemma-hosted service
  operations; Task 254 and Task 255 details live in their governed docs.
- Epic 09 / ADR-0009 remains the proposed Gateway cutover lane. Review 06 is
  resolved to acceptance readiness, but ADR-0009 stays proposed until Task 257
  performs the explicit acceptance update.
- Task 265 was deployed on Hemma from commit
  `f6eebfecd2cee273699e5b656ac49f7fb26cd248`; `convert.hule.education` remains
  reserved until the Gateway cutover intentionally reopens the public edge.
- Task 266 remains the follow-up for auth-aware public-edge evidence and unknown
  public consumer classification without logging secrets.
- Task 253 is the current docs-governance authority for cutting root
  `AGENTS.md` over to a thin skill router and aligning generated docs indexes
  with the canonical `.codex/handoff.md` active-context model.
- Epic 10 is active for exam artifact conversion and authoring to
  Exam.net-compatible targets. DigiExam is one source adapter, not the
  product boundary. Completed lanes include parser/IR/assets/PDF/QTI/service
  runtime work through Task 282 for `digiexam_dxe -> examnet_migration_bundle`,
  public grant contract/runtime through Tasks 291/292, and the separate
  `examnet_artifact -> teacher_authoring_bundle` route split. Story 45 is
  scaffolded for teacher-owned Exam.net artifacts; Story 46 is the cleanup
  prerequisite before more Exam.net authoring runtime, with Tasks 288/289 next.
  HuleEdu auth-edge implementation authority lives in HuleEdu `ST-01-07`.
- Story 39 checkpoint/OCR lanes through Task 271 are completed or reviewed in
  their governed docs. Task 271's production-service dirty-corpus result is the
  current optimization baseline; do not rerun a serial baseline unless a later
  governed decision changes that policy.
- Task 272 and Task 273 are proposed Story 39 follow-ups: formula-aware full
  OCR PDF plus linked artifacts, then `chunk_size_pages=8` production tuning
  with warm-up and GPU sampling.
- Review 10 re-reviewed and approved the amended Task 272/273 drafts. The
  `>=40%` toy improvement gate is withdrawn as a blocker; Task 272 now carries
  the public artifact/retention contract and Task 273 now carries numeric
  promotion/resource thresholds.
- Task 322 completed and remediated the Sir Convert producer prerequisite for
  Skriptoteket `PR-0332`: `point_correction.max_score` is strict
  positive-integer, effective reports expose `effective_point_correction`,
  source-fingerprint readiness is pinned, reviewed/manual key coexistence is
  tested, OpenAPI is refreshed, and Skriptoteket generated DTOs/preflight now
  consume both new fields.

## Active Pointers

- Generated docs doorway: `docs/index.md`.
- Active planning and session handoff: `.codex/handoff.md`.
- Thin agent-router task: `docs/backlog/tasks/task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active public-edge recovery task: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- Active dependency-image follow-up task: `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
- Completed Hemma production deploy-command hardening task: `docs/backlog/tasks/task-283-harden-hemma-production-deploy-command-and-cache-hot-recreate.md`.
- Active Gateway cutover planning epic: `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Gateway cutover inventory reference: `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`.
- Sir Convert identity authorization profile: `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- Completed Gateway cutover profile task: `docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md`.
- Auth-aware public-edge evidence follow-up: `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active exam artifact conversion/authoring umbrella epic: `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
- Completed DigiExam parser/IR docs: Story 38/Task 267, Story 40/Task 274,
  Story 41/Task 275.
- Completed DigiExam embedded asset story/task: Story 42 and Task 276.
- Completed DigiExam Exam.net PDF renderer story/task: Story 43 and Task 277.
- Completed DigiExam migration API/artifact delivery story:
  `docs/backlog/stories/story-44-digiexam-migration-api-and-skriptoteket-artifact-delivery-contract.md`.
- Completed DigiExam migration API/artifact contract task:
  `docs/backlog/tasks/task-278-define-digiexam-migration-api-artifact-bundle-and-skriptoteket-ownership-contract.md`.
- Proposed Exam.net artifact authoring bundle story:
  `docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md`.
- Proposed service/source cleanup tranche before more Exam.net runtime work:
  `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`.
- Completed cleanup tranche docs/source tasks: Tasks 284-287; Review 14 is
  accepted in
  `docs/backlog/reviews/review-14-ruthless-review-of-tasks-285-287-service-route-registry-runtime-and-cli-split.md`.
  Next Story 46 tasks: Tasks 288/289.
- Completed DigiExam route/runtime and public Exam Converter docs: Tasks
  279-282 and 291-292, plus HuleEdu `ST-01-07` auth-edge dependency.
- Active answer-key completion lane: Epic 11. Tasks 294-309/312/319/321/322
  built provider, advisory, overlay/effective-IR, unkeyed-manual QTI,
  Qwen3.6, target-key preservation, and point-correction producer surfaces.
  Qwen3.6 MTP on `llama.cpp` is the guarded advisory model; automatic
  promotion remains blocked by 3 wrong-but-valid suggestions.
- Review 17 for Task 306 is closed as `approved`; future generated-type
  staleness claims need current producer-contract and consumer-regeneration
  evidence, not the historical PR-0331 finding.
- Review 18 for Task 319 is closed as `approved`: Hemma is synced, Qwen3.6
  llama.cpp runs localhost-only with `mmproj-F16.gguf`, `--media-path`, and GPU
  offload, and provider-status plus choice/gap/vision microprobes are green.
- Hemma DevOps skill/runbook cleanup is now structural: the repo-local skill is
  a thin router, the former omnibus Hemma runbook is a compact doorway, and
  focused service/GPU/conversion/TTS runbooks carry current operator guidance.
- DigiExam migration service API/artifact contract:
  `docs/converters/digiexam-migration-service-api-artifact-contract.md`.
- Draft Exam.net artifact authoring service API/artifact contract:
  `docs/converters/examnet-artifact-authoring-service-api-artifact-contract.md`.
- Exam.net Swedish PDF-to-exam renderer profile:
  `docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md`.
- Exam.net QTI import contract and validation strategy:
  `docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`.
- DigiExam IR converter contract:
  `docs/converters/digiexam-intermediate-exam-representation-contract.md`.
- DigiExam artifact and item-type evidence:
  `docs/reference/ref-digiexam-exam-artifact-item-type-evidence.md`.
- DigiExam and Exam.net migration research:
  `docs/reference/ref-digiexam-jspdf-export-shape-and-examnet-migration-research.md`.
- ADR-0009 readiness review:
  `docs/backlog/reviews/review-06-ruthless-review-of-adr-0009-gateway-cutover-readiness.md`.

## Next Actions

1. Continue Story 46 with Tasks 288/289 before further Exam.net runtime.
1. Continue Story 39 with the next governed implementation slice: Task 272 for
   formula-aware final pass and linked artifact bundle, or Task 273 for
   `chunk_size_pages=8` production-service tuning proof.
1. Continue the HuleEdu/Skriptoteket cutover: HuleEdu `ST-01-07` proxies
   `/sir-convert/v2/...`; Skriptoteket then consumes the Task 282 contract.
1. Skriptoteket `PR-0322` public live proof can consume Task 292 runtime
   evidence; do not widen this lane beyond
   `digiexam_dxe -> examnet_migration_bundle`.
1. Continue Skriptoteket `PR-0332` from the completed Task 322 producer and
   consumer-contract preflight: implement source-bound correction UI using the
   returned Sir Convert effective IR/readiness/report state.
1. Continue PR-0331 from the completed Sir Convert Task 321 cleanup: the next
   answer-key UI/consumer slice must preserve reviewed gap/open-cloze keys in
   QTI and PDF artifacts, must not offer QTI packages when adapter follow-up
   means an item was omitted, and must keep remaining degraded output as
   explicit accepted-current-state behavior. Local tests are not live-dev proof;
   live proof needs the auth edge, Sir Convert service, and tunneled LLM
   container together.
1. Treat Task 307 as completed but still binding before implementing any new
   Exam.net PDF, teacher-authored DOCX, or teacher-authored Markdown source
   parser: new parsers need source-native parse models plus adapters into
   `ExamAuthoringIR v1`, not direct target-exporter coupling.
1. For accepted-current-state QTI export, use Task 303's completed
   `unkeyed_manual_qti_2_1_v1` profile and keep Exam.net import proof marked
   vendor-unproven until the vendor provides a test path.
1. Keep the Exam.net artifact authoring route separate from the DigiExam
   migration route. Do not feed Exam.net-origin PDFs or Word exports into
   `digiexam_dxe -> examnet_migration_bundle`.
1. Stop before editable DOCX generation, service API runtime changes, bulk migration workflow, Skriptoteket code, anonymous public conversion, or Exam.net browser/upload automation unless a new governed task authorizes it.
1. Keep Epic 09/Task 266 available as a separate cutover lane; do not mix it
   into the DigiExam parser implementation.

## Validation

- Older validation evidence (2026-05-13 through 2026-05-15) lives in linked
  governed tasks, references, reviews, and long-term memory entries.
- Full Task 309 answer-key validation history (Granite/vLLM demotion, Qwen3.6
  evaluation, Devstral demotion) is preserved in LTM:
  `.codex/long-term-memory/entries/session-2026-05-16-answer-key-validation-history.md`.
- 2026-05-16 Qwen3.6-27B-Q6_K final: 39 correct, 3 wrong-but-valid, 2
  manual-follow-up out of 44 eligible scored items; promotion gate
  `wrong_but_valid_count == 0` is not met. Devstral is demoted at 34/8/2.
- Task 309/319 validation: golden validation covered 44 entries, Qwen3.6
  request-shape preview covered 44 eligible items with 2 multimodal requests,
  and Review 18 proved 317/317 Hemma corpus coverage plus green live
  provider-status/choice/gap/vision microprobes.
- 2026-05-17 Task 320 in progress: production default is Qwen3.6 MTP
  (`qwen36-llama-cpp-mtp`, alias `qwen3.6-27b-q6k-mtp`) via Docker service DNS
  `sir_convert_qwen_answer_key:8082`. The production runtime now separates
  HTTP admission (`sir_convert_a_lot_prod`, no GPU devices, no submit-time job
  execution) from current PDF/OCR GPU execution
  (`sir_convert_a_lot_gpu_worker`, private Docker service with supervisor).
  Generated dependency image identity files now write under ignored
  `build/verification/service-deps/` instead of dirtying tracked
  `docker/service-deps/` state. Local gates passed; live Hemma proof still
  needs deploy/recreate and authenticated MCQ candidate verification.
- 2026-05-17 Task 321 completed: reviewed/source/teacher gap/open-cloze keys
  now reach QTI/PDF artifacts, QTI blocks omitted-item or missing-gap-key
  packages, and internal fallback text is absent from user-facing PDFs. Local
  validation passed per Task 321 evidence. Live dev-container proof was not
  run; it requires auth edge, Sir Convert, and tunneled LLM together.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
