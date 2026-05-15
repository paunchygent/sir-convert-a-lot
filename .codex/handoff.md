---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-05-15'
---

## Purpose

Keep only volatile Sir Convert-a-Lot agent state, blockers, validation evidence,
and next actions. Move durable session history to
`.codex/long-term-memory/entries/` and governed doctrine to docs, rules,
runbooks, or skills.

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

## Active Pointers

- Generated docs doorway: `docs/index.md`.
- Active planning and session handoff: `.codex/handoff.md`.
- Thin agent-router task:
  `docs/backlog/tasks/task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active public-edge recovery task: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- Active dependency-image follow-up task: `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
- Completed Hemma production deploy-command hardening task:
  `docs/backlog/tasks/task-283-harden-hemma-production-deploy-command-and-cache-hot-recreate.md`.
- Active Gateway cutover planning epic:
  `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Gateway cutover inventory reference:
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`.
- Sir Convert identity authorization profile:
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- Completed Gateway cutover profile task:
  `docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md`.
- Auth-aware public-edge evidence follow-up:
  `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- Active exam artifact conversion/authoring umbrella epic:
  `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`.
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
- Active answer-key completion lane: Epic 11; Tasks 294/295/302/303/304 built
  overlay/effective-IR/readiness/OpenAPI and unkeyed-manual QTI foundations.
  Tasks 298/305/307 completed source-neutral `ExamAuthoringIR v1` matching/gap
  contracts; Review 16 is accepted after the third remediation. It rejects
  value-level gap `mixed`, aggregate matching `mixed`, and non-empty matching
  pairs with `absent`. Task 296 completed the structured-provider harness,
  Dishka/runtime wiring, and default route no-call proof. Task 297 completed
  advisory candidate-lineage reports for choice/gap-fill items. Task 306
  completed reviewed overlay application into effective IR, with parser/source
  provenance untouched, bounded lineage in `digiexam_effective_exam_v2`, and
  apply mode making no structured-provider calls.
  Granite FP8 on Hemma ROCm vLLM remains the interim local provider from Task
  301; keyed matching QTI bridging waits for real matching-capable source
  fixtures through `ExamAuthoringIR v1`.
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
1. For machine-marked answer-key completion, request the post-implementation
   review for Task 306 before opening a new runtime slice.
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

- Older validation evidence lives in linked governed tasks, references, reviews,
  and long-term memory entries.
- 2026-05-13 through 2026-05-15 validation evidence for pre-release, Task 292,
  Hemma runbook cleanup, and Tasks 294/295/302 lives in linked governed
  tasks/reviews.
- 2026-05-15 Task 305 gates passed. Task 296 tranche 1 gates passed:
  focused structured-provider tests (`15 passed`), `typecheck-all`,
  docs/skills/handoff validation, `coverage-gate` (`1216 passed, 5 skipped`,
  coverage `95.43%`), and `git diff --check`.
- 2026-05-15 Task 296 tranche 2 focused tests passed:
  `test_structured_llm_provider_harness.py` plus
  `test_structured_llm_provider_execution.py` (`26 passed`), followed by
  `format-all`, `lint-fix`, `typecheck-all` with no issues in `668` source
  files, docs/skills/handoff validation after `docs-sync`, `coverage-gate`
  (`1232 passed, 5 skipped`, coverage `95.43%`), and `git diff --check`.
- 2026-05-15 Task 296 tranche 3 focused tests passed:
  structured-provider harness/execution/composition plus DigiExam default
  artifact-route no-call proof (`32 passed`), followed by `format-all` and
  `lint-fix`, `typecheck-all` with no issues in `671` source files,
  docs/skills/handoff validation after `docs-sync`, `coverage-gate`
  (`1238 passed, 5 skipped`, coverage `95.43%`), and `git diff --check`.
- 2026-05-15 Review 16 accepted after third remediation: focused ExamAuthoringIR
  gap/matching tests (`23 passed`), live bypass probes fail closed,
  `format-all`, `lint-fix`, `typecheck-all`, docs/skills/handoff validation
  after `docs-sync`, `coverage-gate` (`1250 passed, 5 skipped`, coverage
  `95.46%`), and `git diff --check`.
- 2026-05-15 Task 297 focused tests passed: advisory answer-key completion
  domain tests, DigiExam route mutation/no-call proofs, and OpenAPI contract
  tests (`12 passed`) after `pdm run openapi-export-v2`; full `coverage-gate`
  passed (`1248 passed, 5 skipped`, coverage `95.46%`).
- 2026-05-15 Task 306 gates passed: focused reviewed-completion apply/no-call
  proof (`26 passed`), `typecheck-all`, docs/skills/handoff validation, full
  `coverage-gate` (`1257 passed, 5 skipped`, coverage `95.48%`).

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
