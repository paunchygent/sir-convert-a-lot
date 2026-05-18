---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-05-18'
---

## Purpose

Keep volatile Sir Convert-a-Lot state, blockers, validation evidence, and next actions. Move durable history to `.codex/long-term-memory/entries/`.

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
- Tasks 322-324 completed the `PR-0332` producer prerequisites: point
  corrections, source-neutral matching DTO, and
  `POST /v2/exam-authoring/matching/manual-answer-key/apply` are exposed with
  source-fingerprint binding, effective state/readiness, OpenAPI, and
  Skriptoteket generated-type/preflight proof.
- ADR-0011/Task 327 are proposed for the cleaner producer-contract follow-up:
  Task 324 is bridge work, and the next source-neutral slice should define
  `POST /v2/exam-authoring/corrections/apply` with typed correction entries.
- Task 328 completed the proposed-ADR audit. Task 329 implemented the ADR-0002
  closeout docs: ADR-0002 is superseded by accepted ADR-0012. Review 22 closed
  as `changes_requested` because the Task 329 review set is mixed with separate
  Task 325-B runtime/OpenAPI provider-lineage changes.

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
- Active answer-key completion lane: Epic 11. Tasks 294-309/312/319/321-323
  built provider, advisory, overlay/effective-IR, unkeyed-manual QTI, Qwen3.6,
  target-key preservation, point correction, and the matching DTO.
  ADR-0011/Task 327 are proposed for the unified source-neutral
  correction/apply contract before adding more item-specific Gateway/service
  routes. Qwen3.6 remains guarded; ADR-0010 is accepted. Task 325 is in
  progress for OpenAI hot settings; Task 325-B now pins provider/settings
  lineage at admission and report level. Task 326 remains the eval gate.
- Review 17 for Task 306 is closed as `approved`; future generated-type claims
  need current producer/consumer evidence, not the historical PR-0331 finding.
- Review 18 for Task 319 is closed as `approved`; Hemma/Qwen3.6 live
  provider-status plus choice/gap/vision microprobes are green.
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
- ADR-0002 closeout: Task 329 plus Review 22 `changes_requested`.

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
1. Continue Skriptoteket `PR-0332` from completed Tasks 322/324: implement
   source-bound correction UI using returned Sir Convert effective
   IR/readiness/report state; submit matching keys through
   `/v2/exam-authoring/matching/manual-answer-key/apply` with the producer
   `source_item_fingerprint`; keep browser drafts non-authoritative until Sir
   Convert returns effective state/readiness.
1. Before adding more item-specific correction routes, continue Task 327:
   define the unified source-neutral
   `/v2/exam-authoring/corrections/apply` contract under proposed ADR-0011,
   then sequence HuleEdu authenticated edge proxying and Skriptoteket
   teacher-correction API migration after acceptance.
1. Remediate Review 22 by splitting or separately governing the Task 325-B
   runtime/OpenAPI provider-lineage changes, then re-review Task 329 before
   marking it completed.
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

- Older validation evidence lives in governed tasks, references, reviews, and
  `.codex/long-term-memory/entries/`.
- 2026-05-16 Task 309/319: Qwen3.6-27B-Q6_K final was 39 correct, 3
  wrong-but-valid, 2 manual-follow-up out of 44; Review 18 proved 317/317
  Hemma corpus coverage plus green live provider-status/choice/gap/vision
  microprobes.
- 2026-05-17 Task 320 in progress: production default is Qwen3.6 MTP via
  Docker service DNS `sir_convert_qwen_answer_key:8082`; HTTP admission is
  separated from PDF/OCR GPU execution, dependency-image identity writes under
  ignored `build/verification/service-deps/`, and live Hemma proof still needs
  deploy/recreate plus authenticated MCQ candidate verification.
- 2026-05-17 Task 321 completed: reviewed/source/teacher gap/open-cloze keys
  now reach QTI/PDF artifacts, QTI blocks omitted-item or missing-gap-key
  packages, and internal fallback text is absent from user-facing PDFs. Local
  validation passed per Task 321 evidence. Live dev-container proof was not
  run; it requires auth edge, Sir Convert, and tunneled LLM together.
- 2026-05-18 Task 324 local closeout passed OpenAPI export, format/lint/type
  gates, focused matching/OpenAPI pytest, coverage-gate, and Skriptoteket
  generated-type/preflight proof.
- 2026-05-18 Review 22 completed as `changes_requested`: ADR-0012 closeout is
  directionally sound, but Task 329 cannot be approved while bundled with
  unrelated Task 325-B runtime/OpenAPI provider-lineage changes.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence or changing service runtime, Hemma deploy, artifact retention, or Qwen experiment semantics.
