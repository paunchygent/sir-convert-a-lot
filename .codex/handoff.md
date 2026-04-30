---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-04-30'
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
- Epic 10 is now the active feature lane for DigiExam to Exam.net migration.
  Story 38 and Task 267 were scaffolded after reviewing the research baseline.
  Task 267 is the immediate implementation authority for parser v1 fixtures,
  confidence/warning reporting, and fail-closed handling of unknown or degraded
  item shapes.
- Task 267 is completed locally. Parser v1 now lives under the Sir Convert
  domain/infrastructure surfaces with deterministic tests for the two tracked
  DigiExam PDFs, explicit source evidence, answer-key provenance, and
  fail-closed typed warnings for degraded or unknown shapes. It still does not
  introduce Exam.net rendering, service/API routes, QTI/native import, or bulk
  migration workflow behavior.
- Review 07 follow-up fixed the parser-readiness blockers: exact
  multiple-choice prompt/options assertions now cover `Materia`, `Grundämnen`,
  and `Joner`; the `Grundämnen` page-boundary option no longer leaks into
  `Atomen`; and the out-of-scope `Match answers` renderer schema was removed
  from the Task 267 reference closeout.
- Task 268 is completed locally under Story 39. PDF checkpoint schema is now
  `v2_pdf_checkpoint_v2`, succeeded chunk records persist backend/OCR metadata,
  warnings, and canonical timings, and zero-new-chunk finalization hydrates
  terminal metadata from checkpoint records without reprocessing. Old v1
  checkpoint payloads fail closed; there is no backwards-compatibility bridge.
- Review 08 follow-up for Task 268 is implemented locally. The parallel test is
  order-insensitive, terminal assembly fails closed on missing/corrupt or
  incomplete chunk artifacts, OCR engine/language metadata is observed from the
  backend result contract, and the public checkpoint v2 schema is documented.
- Task 269 Review 09 is closed as approved under Story 39. Outcome B remains
  the OCR metadata contract, and no-OCR PDF semantics are now explicit:
  `ocr_languages_used=[]` when OCR was applicable but not executed, and
  `ocr_languages_used=null` only where OCR is not applicable.
  The 2026-04-29 re-review approved Task 268; Story 39 remains open for Task
  269, Task 270, Task 271, and final Task 74 evidence.
- Task 270 is completed locally under Story 39. Dirty-corpus evidence now
  requires metadata-only manifests plus `--dirty-corpus-source-root` hash
  verification; synthetic/local smoke remains schema/safety-only and cannot
  satisfy real-data performance proof.
- Task 271 implementation and Hemma proof are captured. Revision
  `405cddc59d02974f43eaf03556bad92cdd1c2341` was deployed and parity-verified
  before a detached production-service dirty-corpus benchmark ran on Hemma.
  The run verified 10 private manifest entries / 157 pages, processed them via
  `runtime_surface.mode=production_service`, reported `success_rate=1.0`,
  `failed_jobs=0`, `contains_job_id_label=false`, and met the 150-page target
  with `tuned_wall_clock_seconds=2179.0`. Raw JSON/Markdown artifacts live in
  ignored `build/benchmarks/story-39/` paths and were copied locally under
  `build/benchmarks/story-39/local-copies/task-271-dirty-pdf-ocr-proof/`.
  Story 39 still needs a reviewer decision or follow-up for the separate
  production-service `>=40%` baseline-vs-tuned improvement gate.
- `TASK-0046` compacted this handoff, moved durable March 2026 history into
  long-term memory, and added the real `pdm run handoff-validate` command
  surface.
- `TASK-0043` completed the direct governance cutover from `.agents/` paths to
  `.codex/` paths. Do not recreate compatibility shims.
- `TASK-0045` added the shared command grammar now available in this repo:
  `pdm run docs-validate` and `pdm run skills-validate`.
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
- Completed DigiExam parser story:
  `docs/backlog/stories/story-38-digiexam-pdf-parser-v1-fixtures-and-confidence-reporting.md`.
- Completed DigiExam parser task:
  `docs/backlog/tasks/task-267-implement-digiexam-pdf-parser-v1-fixtures-and-confidence-gate.md`.
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

## Durable Memory

- TASK-0043 governance cutover memory:
  `.codex/long-term-memory/entries/session-2026-04-16-task-0043.md`.
- March 2026 service, local runtime, service image, and Qwen operator
  history compacted from the former long handoff:
  `.codex/long-term-memory/entries/session-2026-03-25-service-and-qwen-operator-history.md`.

## Next Actions

1. Arrange a separate retained post-implementation review for Task 267 before
   treating the parser lane as independently approved.
1. Review Task 271 evidence and decide the next Story 39 closeout slice:
   either run a governed production-service baseline/tuned A/B proof for the
   remaining `>=40%` improvement gate, or record a Task 74/Story 39 blocker
   decision. Do not treat the Task 271 current-profile proof as baseline-vs-
   tuned improvement evidence.
1. Continue EPIC-10 with the next governed slice only after review: likely the
   Sir Convert intermediate exam representation and manifest schema, or a
   renderer-target decision task if Exam.net ingestion evidence still needs
   narrowing.
1. Stop before Exam.net renderer, QTI/native import, service API, or bulk
   migration workflow changes unless a new governed task is created.
1. Keep Epic 09/Task 266 available as a separate cutover lane; do not mix it
   into the DigiExam parser implementation.
1. Before any future Hemma Qwen run, use:
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   and
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`.

## Validation

- Older April 2026 Gateway, Task 255, Task 256, Task 259, and Review 06
  validation evidence lives in the linked governed task, reference, and review
  docs.
- 2026-04-27 Task 267 Review 07 follow-up validation
  passed: `pdm run format-all`; `pdm run lint-fix`;
  `pdm run typecheck-all` (`Success: no issues found in 571 source files`);
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_pdf_parser_v1.py -q`
  (`10 passed`); `pdm run coverage-gate` (`1061 passed, 5 skipped`, total
  coverage `95.55%`); `pdm run docs-sync`; `pdm run docs-validate`;
  `pdm run skills-validate`; `pdm run handoff-validate`; `git diff --check`.
- 2026-04-28 Task 268 validation passed: `pdm run format-all`;
  `pdm run lint-fix`; `pdm run typecheck-all`
  (`Success: no issues found in 574 source files`);
  `pdm run pytest-root tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py -q`
  (`19 passed`); `pdm run coverage-gate` (`1065 passed, 5 skipped`, total
  coverage `95.47%`).
- 2026-04-28 Review 08 follow-up validation passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py -q`
  (`20 passed`) and `pdm run typecheck-all`
  (`Success: no issues found in 574 source files`).
- 2026-04-29 Task 269 focused validation passed:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task269_ocr_metadata_contract.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py -q`
  (`4 passed`).
- 2026-04-29 Task 269 Review 09 follow-up validation passed:
  focused Task 269 suite (`5 passed`), `pdm run format-all`, `pdm run lint-fix`,
  `pdm run typecheck-all` (`Success: no issues found in 575 source files`),
  `pdm run docs-sync`, `pdm run docs-validate`, `pdm run validate-tasks`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
- 2026-04-29 Review 08 re-review approved Task 268 after verifying:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task268_pdf_checkpoint_metadata_resume.py tests/sir_convert_a_lot/test_pdf_checkpoints_v2.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_partial_and_checkpoint_endpoints.py tests/sir_convert_a_lot/test_task72_parallel_execution_contracts.py -q`
  (`20 passed`); `pdm run typecheck-all`
  (`Success: no issues found in 574 source files`); `pdm run docs-sync`;
  `pdm run docs-validate`; `pdm run skills-validate`;
  `pdm run handoff-validate`; `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
