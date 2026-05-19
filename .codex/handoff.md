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
- Tasks 322/323 completed the `PR-0332` point and matching DTO producer
  prerequisites. Task 324's matching-specific route is superseded/abandoned.
- Task 327 completed the unified contract at
  `docs/converters/exam-authoring-corrections-apply-contract.md`; Task 330
  completed the runtime/OpenAPI hard cut for
  `POST /v2/exam-authoring/corrections/apply`, including initial
  `manual_matching_answer_key` support and removal of the Task 324 route.
  Task 331 added signed producer-state verification, remediated the direct
  source-state signer, wired DigiExam producer emission of the source-state
  sidecar, and widened that sidecar for DigiExam text/point/choice/gap
  correction surfaces. Review 24 is approved; downstream matching use remains
  blocked on proposed Task 332 because DigiExam emits no real matching
  interactions.
- ADR-0011 is accepted after Review 23 approved the remediated PR-0332
  continuation gate.
- Task 328 completed the proposed-ADR audit. Task 329 completed the ADR-0002
  closeout docs: ADR-0002 is superseded by accepted ADR-0012. Review 22 closed
  as `approved` and explicitly scopes out already-published Task 325-B
  runtime/OpenAPI provider-lineage changes.
- Task 337 is completed and accepted: accepted-current-state is removed from authoring/correction state and missing-key PDF/QTI exports stay blocked until real key corrections exist. Task 315 is the next ready slice for Exam.net PDF strategy extraction; its strategy model must keep the core PDF item protocol target-agnostic while isolating Exam.net-specific reshaping in the Exam.net PDF target profile.

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
- Proposed Exam.net artifact authoring bundle story:
  `docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md`.
- Proposed service/source cleanup tranche before more Exam.net runtime work:
  `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`.
- Completed DigiExam route/runtime and public Exam Converter docs: Tasks
  279-282 and 291-292, plus HuleEdu `ST-01-07` auth-edge dependency.
- Active answer-key completion lane: Epic 11. Tasks 294-309/312/319/321-323
  built provider, advisory, overlay/effective-IR, unkeyed-manual QTI, Qwen3.6,
  target-key preservation, point correction, and the matching DTO.
  ADR-0011 is accepted, Task 327 defines the unified source-neutral
  correction/apply contract, and Task 330 implements the first runtime/OpenAPI
  slice for `manual_matching_answer_key`. Task 331 completed the Review 24
  remediation response. Task 333 completed the non-matching unified apply
  runtime for DigiExam-backed item text, point, choice, and gap/open-cloze
  corrections; Task 332 blocks matching-capable producer work before any
  downstream matching use. Qwen3.6 remains guarded; ADR-0010 is
  accepted. Task 325 is in progress for OpenAI hot settings; Task 325-B now
  pins provider/settings lineage at admission and report level. The 2026-05-18
  Task 325 diagnostics slice adds redacted upstream OpenAI provider-error
  diagnostics and a focused item-013 advisory-corpus repro lane for the
  ekologiprov `.dxe`; commit/push/Hemma deploy remains required before
  Hemma production can expose the new diagnostic fields. Task 326 is in
  progress as the eval gate; after teacher adjudication of the mini failure
  rows, the fresh 2026-05-18 rerun scores mini 43/1/0 and nano 36/8/0 versus
  the retained Qwen3.6 41/3/0 baseline.
- Task 337 is ready as the upstream parent for Skriptoteket PR-0341:
  remove `review_decision` / `accept_current_state_for_export` from authoring
  correction contracts; any future incomplete export must be export-only.
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
- Completed ADR-0002 closeout: Task 329 plus Review 22 `approved`.

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
1. Continue the cross-repo correction cutover with HuleEdu `TASK-0567` after
   Task 333: expose the unified source-state issue/apply edge, keep the Task
   324 route absent, and continue Task 332 later before any downstream
   `manual_matching_answer_key` submission.
1. Task 337 is complete; implement Task 315 next so Exam.net PDF item strategy extraction starts from the clean post-337 boundary.
1. Continue downstream PR-0332 only after its correction family has a
   producer-issued source-state surface. HuleEdu Gateway proxies
   `/v2/exam-authoring/corrections/apply`, and Skriptoteket treats returned
   effective state/readiness as authoritative for the governed correction
   families.
1. Continue PR-0331 from the completed Sir Convert Task 321 cleanup: the next
   answer-key UI/consumer slice must preserve reviewed gap/open-cloze keys in
   QTI and PDF artifacts, must not offer QTI packages when conversion follow-up
   means an item was omitted, and must keep remaining degraded output as
   explicit accepted-current-state behavior. Local tests are not live-dev proof;
   live proof needs the auth edge, Sir Convert service, and tunneled LLM
   container together.
1. Treat Task 307 as completed but still binding before implementing any new
   Exam.net PDF, teacher-authored DOCX, or teacher-authored Markdown source
   parser: new parsers need source-native parse models plus adapters into
   `ExamAuthoringIR v1`, not direct target-exporter coupling.
1. Keep the Exam.net artifact authoring route separate from the DigiExam
   migration route. Do not feed Exam.net-origin PDFs or Word exports into
   `digiexam_dxe -> examnet_migration_bundle`.
1. Stop before editable DOCX generation, service API runtime changes, bulk migration workflow, Skriptoteket code, anonymous public conversion, or Exam.net browser/upload automation unless a new governed task authorizes it.
1. Keep Epic 09/Task 266 available as a separate cutover lane; do not mix it
   into the DigiExam parser implementation.

## Validation

- Task 309/319/326 provider evidence remains governed by those tasks: mini is
  the temporary accepted/default dev/prod provider; Qwen3.6 is guarded rollback.
- Task 321 local validation passed; live dev-container proof still requires
  auth edge, Sir Convert service, and tunneled LLM together.
- Task 330/331 validation evidence lives in their governed task/review docs.
- Task 333 validation includes OpenAPI export, format/lint/type, focused route
  and OpenAPI tests, real DigiExam text/point/choice/gap issue/apply tests, and
  coverage-gate at 95.56%.
- 2026-05-18 Review 24 completed as `approved`: Task 331 is closed, and
  `manual_matching_answer_key` remains blocked on Task 332 until a
  matching-capable producer emits real matching source state.
- 2026-05-18 Task 325 diagnostics and gap-label policy validation lives in the
  task doc. Focused local gates passed, OpenAI item-013 returned labels only,
  and all current label/number gap-fill eval rows returned expected labels.
- 2026-05-18 Tasks 334/335 added the guarded DeepSeek JSON Output provider and
  replaced the current profile with `deepseek-v4-pro-non-thinking`. Full pro
  eval retained under `build/verification/task-335-deepseek-v4-pro-full-eval-2026-05-18/`
  scored 39 correct, 3 wrong-but-valid, and 2 image/asset manual follow-ups;
  do not promote DeepSeek yet.

## Stop Conditions

- Stop before deleting durable Qwen/service/Hemma evidence or changing service runtime, Hemma deploy, artifact retention, or Qwen experiment semantics.
