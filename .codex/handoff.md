---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-05-13'
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
- Epic 10 is active for DigiExam to Exam.net migration. Completed lanes:
  Story 38/Task 267 PDF fallback parser, Story 40/Task 274 `.dxe` parser plus
  sanitized result-PDF enrichment, Story 41/Task 275 IR, Story 42/Task 276
  embedded assets, and Story 43/Task 277 Exam.net-oriented PDF renderer.
  Story 44/Task 278 are completed as the API/artifact contract gate for
  authenticated Skriptoteket delivery before QTI, service runtime, or
  Skriptoteket UI implementation proceeds.
  Story 45 is now scaffolded for normal teacher-owned Exam.net artifacts.
  Task 279 completed on 2026-05-12 as the docs-as-code direction gate: the
  route family is one shared service API v2 lifecycle with separate
  `digiexam_dxe -> examnet_migration_bundle` and
  `examnet_artifact -> teacher_authoring_bundle` contracts. The Exam.net route
  makes QTI packages, editable DOCX, Swedish Exam.net PDF-to-exam converter
  PDFs, QTI validation reports, and manual-follow-up reports first-class
  artifact targets.
  Task 280 completed as the QTI implementation gate: deterministic QTI 2.1
  sample packages for MCQ, free text, image-bearing MCQ/free text,
  unsupported-resource omission, and proof-gated matching plus
  `qti_validation_report` output.
  Task 281 completed for the local OneDrive `.dxe` validation corpus: raw files
  stay ignored/local-only, and the tracked evidence is a metadata-only manifest
  plus parser/IR regression tests.
  Task 282 completed the Sir Convert service-runtime implementation for
  DigiExam migration artifact bundle routes: signed HuleEdu
  `InternalIdentityContextV1` ownership, `digiexam_dxe -> examnet_migration_bundle`, named artifact listing/download routes, Task 280
  QTI integration, live service-route smoke coverage over a bounded local
  OneDrive `.dxe` corpus subset, selective `conversion.targets`, and
  manifest-backed `/result` metadata. Review 12 is accepted after re-review.
  The HuleEdu auth-edge implementation authority moved from the former Task 260
  planning lane to HuleEdu `ST-01-07`.
  Review 11's Task 276 zero-payload embedded-asset blocker was remediated on
  2026-05-12 and closed: `bodyHTML` `data-image-id` references now fail closed
  with `missing_embedded_asset_reference` when `question.images[]` is empty or
  absent.
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
- `TASK-0046`, `TASK-0043`, and `TASK-0045` established the compact handoff,
  `.codex/` governance surface, and validation command grammar. Do not
  recreate retired `.agents/` shims.
- Generated repomix packages belong under ignored `.codex/repomix_packages/`;
  do not track generated XML packages.

## Active Pointers

- Generated docs doorway: `docs/index.md`.
- Active planning and session handoff: `.codex/handoff.md`.
- Thin agent-router task:
  `docs/backlog/tasks/task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active public-edge recovery task: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- Active dependency-image follow-up task: `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
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
- Active DigiExam migration epic:
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
- Completed Exam.net authoring/QTI direction gate:
  `docs/backlog/tasks/task-279-define-exam-net-artifact-source-contract-and-swedish-pdf-to-exam-renderer-profile.md`.
- Completed QTI sample package and validation-report implementation task:
  `docs/backlog/tasks/task-280-implement-exam-net-qti-sample-packages-and-validation-report-gate.md`.
- Completed DigiExam `.dxe` validation corpus classification task:
  `docs/backlog/tasks/task-281-classify-digiexam-dxe-validation-corpus-and-add-parser-regression-gate.md`.
- Completed runtime task and HuleEdu auth-edge dependency:
  `docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`;
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`.
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
- Active Qwen Task 101 ledger:
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Qwen experiment governance:
  `.codex/rules/096-qwen-experiment-governance.md`.
- Hemma/Qwen runbook:
  `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`.
- Durable session-history index:
  `.codex/long-term-memory/index.md`.

## Next Actions

1. Continue Story 39 with the next governed implementation slice: Task 272 for
   formula-aware final pass and linked artifact bundle, or Task 273 for
   `chunk_size_pages=8` production-service tuning proof.
1. Continue the cutover on the HuleEdu/Skriptoteket side: HuleEdu `ST-01-07`
   must proxy `/sir-convert/v2/...` to Sir Convert's downstream
   `/v2/convert/...` routes and sign `InternalIdentityContextV1` with
   `aud=sir-convert-a-lot`; Skriptoteket then needs an adapter/UI/user-file
   task that consumes the Task 282 artifact-bundle contract after Review 12
   re-review acceptance.
1. Keep the Exam.net artifact authoring route separate from the DigiExam
   migration route. Do not feed Exam.net-origin PDFs or Word exports into
   `digiexam_dxe -> examnet_migration_bundle`.
1. Stop before editable DOCX generation, service API runtime changes, bulk
   migration workflow, Skriptoteket code, anonymous public conversion, or
   Exam.net browser/upload automation unless a new governed task authorizes it.
1. Keep Epic 09/Task 266 available as a separate cutover lane; do not mix it
   into the DigiExam parser implementation.

## Validation

- Older validation evidence for Gateway, Story 39, and EPIC-10 Tasks 267-280
  lives in the linked governed tasks, references, reviews, and long-term memory
  entries.
- 2026-05-12 Task 281 validation passed with local-only OneDrive corpus
  metadata, parser, IR, docs, skills, handoff, and diff-check gates.
- 2026-05-13 Task 282 Review 12 remediation validation passed:
  `pdm run format-all`; `pdm run lint-fix`; `pdm run typecheck-all`
  (`Success: no issues found in 622 source files`); focused Task 282 API tests
  (`12 passed`, including selective targets, `/result` metadata, and live
  OneDrive `.dxe` service-route subset); `pdm run coverage-gate`
  (`1140 passed, 5 skipped`, total coverage `93.38%`); `pdm run docs-sync`;
  `pdm run docs-validate` (`Validated 353 backlog files`;
  `Validated docs=412 rules=11`); `pdm run skills-validate`;
  `pdm run handoff-validate`; `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
