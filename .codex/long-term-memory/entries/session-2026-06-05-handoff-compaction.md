---
type: agent_session_long_term_memory
date: '2026-06-05'
scope: Handoff compaction for Sir Convert-a-Lot active-state surface
---

## Compacted Handoff History

This entry preserves the durable session-history categories that were removed
from `.codex/handoff.md` so the active handoff can satisfy the 200-line
contract.

## Service And Governance Lanes

- Epic 03 / Story 05 remains the DevOps lane for Hemma-hosted service
  operations; Task 254 and Task 255 details live in governed docs.
- Epic 09 / ADR-0009 remains the Gateway cutover lane. Review 06 reached
  acceptance readiness, but ADR-0009 remains proposed until Task 257 performs
  the explicit acceptance update.
- Task 265 was deployed on Hemma from commit
  `f6eebfecd2cee273699e5b656ac49f7fb26cd248`; `convert.hule.education`
  remains reserved until the Gateway cutover intentionally reopens the public
  edge.
- Task 266 remains the follow-up for auth-aware public-edge evidence and
  unknown public consumer classification without logging secrets.
- Task 253 governs cutting root `AGENTS.md` over to a thin skill router and
  aligning generated docs indexes with the canonical active-context model.

## Conversion And OCR Lanes

- Story 39 checkpoint/OCR lanes through Task 271 are completed or reviewed in
  their governed docs. Task 271's production-service dirty-corpus result is the
  current optimization baseline.
- Task 272 and Task 273 are Story 39 follow-ups: formula-aware full OCR PDF
  plus linked artifacts, then `chunk_size_pages=8` production tuning with
  warm-up and GPU sampling.
- Review 10 approved the amended Task 272/273 drafts. The earlier `>=40%` toy
  improvement gate is withdrawn as a blocker; Task 272 carries public
  artifact/retention contract details and Task 273 carries numeric
  promotion/resource thresholds.

## Exam Artifact And Correction Lanes

- Epic 10 is active for exam artifact conversion and authoring to
  Exam.net-compatible targets. DigiExam is a source adapter, not the product
  boundary.
- Completed lanes include parser/IR/assets/PDF/QTI/service runtime work through
  Task 282 for `digiexam_dxe -> examnet_migration_bundle`, public grant
  contract/runtime through Tasks 291/292, and the separate
  `examnet_artifact -> teacher_authoring_bundle` route split.
- Story 45 is scaffolded for teacher-owned Exam.net artifacts. Story 46 is the
  cleanup prerequisite before more Exam.net authoring runtime, with Tasks
  288/289 next.
- Tasks 322/323 completed the `PR-0332` point and matching DTO producer
  prerequisites. Task 324's matching-specific route is superseded/abandoned.
- Task 327 completed the unified source-neutral correction/apply contract.
  Task 330 implemented the first runtime/OpenAPI slice. Task 331 completed
  signed producer-state verification and Review 24 remediation.
- Task 333 completed non-matching unified apply runtime for DigiExam-backed
  item text, point, choice, and gap/open-cloze corrections. Task 332 blocks
  matching-capable producer work before downstream matching use.
- Task 337 is completed and accepted: accepted-current-state was removed from
  authoring/correction state, and missing-key PDF/QTI exports remain blocked
  until real key corrections exist.

## Provider And Validation Lanes

- ADR-0011 is accepted after Review 23 approved the remediated PR-0332
  continuation gate.
- Task 328 completed the proposed-ADR audit. Task 329 completed ADR-0002
  closeout docs; ADR-0002 is superseded by accepted ADR-0012.
- Task 309/319/326 provider evidence remains governed by those tasks: mini is
  the temporary accepted/default dev/prod provider and Qwen3.6 is guarded
  rollback.
- Task 325 diagnostics and gap-label policy validation live in its task doc.
- Tasks 334/335 added the guarded DeepSeek JSON Output provider and replaced
  the current profile with `deepseek-v4-pro-non-thinking`; full pro eval
  evidence remains under
  `build/verification/task-335-deepseek-v4-pro-full-eval-2026-05-18/`.
