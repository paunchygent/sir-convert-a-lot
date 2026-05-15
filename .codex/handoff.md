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
  Exam.net-compatible targets. DigiExam is one legacy source adapter, not the
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
- Active answer-key completion lane: Epic 11; Task 294 completed the hard
  `digiexam_migration_bundle_v2` contract break, `digiexam_effective_exam_v1`,
  source fingerprints, target readiness, overlay/report schemas, and consumer
  break inventory. Task 295 implemented source-bound teacher overlay ingestion,
  effective renderer input, source fingerprints in the IR manifest, overlay
  reports, and post-overlay target readiness for manual answer keys and review
  decisions. Task 302 implemented `effective_item_patch` visible item-content
  repairs for effective IR while preserving source IR and answer-key
  provenance. Task 304 publishes a generated v2 OpenAPI snapshot for the
  DigiExam overlay/effective-IR/readiness contract so Skriptoteket can validate
  consumer types before live Docker/service tests. Task 303 completed the
  unkeyed/manual QTI profile that lets accepted-current-state enable QTI only
  after schema/profile validation. The profile is preservation-first: missing
  machine-marked keys remove automatic evaluation claims rather than visible
  QTI/PDF question content whenever a deterministic manual/unkeyed
  representation is valid. Exam.net import proof remains
  vendor-unproven/external until a vendor test path exists. The generated Task
  303 samples use real tracked DXE choice and gap-fill items; matching remains a
  Task-298-aware contract sample until a real matching DXE fixture is available.
  Granite FP8 on Hemma ROCm vLLM remains the interim local provider from Task
  301\.
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
1. For machine-marked answer-key completion, continue with Task 296/297:
   extract the structured local provider harness and then emit advisory
   answer-key completion reports on top of Task 295's overlay/effective IR
   substrate.
1. For accepted-current-state QTI export, use Task 303's completed
   `unkeyed_manual_qti_2_1_v1` profile and keep Exam.net import proof marked
   vendor-unproven until the vendor provides a test path.
1. Keep the Exam.net artifact authoring route separate from the DigiExam
   migration route. Do not feed Exam.net-origin PDFs or Word exports into
   `digiexam_dxe -> examnet_migration_bundle`.
1. Stop before editable DOCX generation, service API runtime changes, bulk
   migration workflow, Skriptoteket code, anonymous public conversion, or
   Exam.net browser/upload automation unless a new governed task authorizes it.
1. Keep Epic 09/Task 266 available as a separate cutover lane; do not mix it
   into the DigiExam parser implementation.

## Validation

- Older validation evidence lives in linked governed tasks, references, reviews,
  and long-term memory entries.
- 2026-05-13 pre-release gates passed: `format-all`, `lint-fix`,
  `typecheck-all` (`638 source files`), focused Story 46 tests (`11 passed`),
  `coverage-gate` (`1159 passed, 5 skipped`, coverage `95.93%`), docs/skills/
  handoff validation, and `git diff --check`.
- 2026-05-13 Task 292 focused gates passed: policy/runtime pytest (`12 passed`), `pdm run lint`, and `pdm run typecheck`.
- 2026-05-14 Hemma skill/runbook cleanup gates passed: `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- 2026-05-15 Task 294 contract gates passed: `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- 2026-05-15 Task 295 focused implementation gates passed: `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`, focused
  DigiExam overlay/IR/API pytest, docs/skills/handoff validation, and
  `git diff --check`.
- 2026-05-15 Task 302 focused implementation gates passed:
  `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`, focused
  DigiExam overlay pytest (`7 passed`), DigiExam migration bundle API pytest
  (`14 passed`), `pdm run coverage-gate` (`1181 passed, 5 skipped`, coverage
  `95.42%`), `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
