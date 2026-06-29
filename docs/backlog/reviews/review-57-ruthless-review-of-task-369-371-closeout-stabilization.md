---
id: review-57-ruthless-review-of-task-369-371-closeout-stabilization
title: Ruthless review of Task 369 and Task 371 closeout stabilization
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md
  - docs/backlog/reviews/review-54-ruthless-review-of-task-369-remove-cli-auto-rerun-wrappers.md
  - docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - approved
  - task-369
  - task-371
  - stabilization
  - idempotency
  - gateway-proof
---

Structured retained review artifact for the uncommitted Task 369/Task 371
closeout stabilization diff after local gates.

## Review Scope

Independent review-only pass. I stayed in the existing `main` checkout, did not
create a worktree, did not deploy, did not commit, did not edit production or
test implementation, did not delete files, and did not revert unrelated dirty
work. The only intentional mutation from this pass is this retained review
artifact.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/backlog/README.md`
- `docs/DOCS_STRUCTURE_SPEC.md`
- `docs/_meta/docs-contract.yaml`
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/backlog/tasks/task-371-expose-audio-transcript-bundle-cli-route-for-public-browser-idempotency-proof.md`
- `docs/backlog/reviews/review-54-ruthless-review-of-task-369-remove-cli-auto-rerun-wrappers.md`
- `docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`

Scoped changed files reviewed:

- `tests/sir_convert_a_lot/test_api_contract_v2_pdf_cancel_and_resume.py`
- `tests/sir_convert_a_lot/test_api_metrics_v2.py`
- `tests/sir_convert_a_lot/test_digiexam_correction_matching_blocked.py`
- `tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py`
- `docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`
- `docs/backlog/INDEX.md`

Explicitly excluded except for generated-index impact:

- `docs/backlog/tasks/task-372-normalize-source-labelled-choice-options-for-examnet-pdf-replay.md`
- `docs/backlog/reviews/review-56-ruthless-review-of-task-372-examnet-labelled-options.md`

Public and runtime boundaries checked:

- Service API v2 create-job status semantics for `wait_seconds=0`.
- PDF cancel-with-save, checkpoint, partial artifact, and resume behavior.
- DigiExam normal job-status polling before correction source-state issuance.
- Task 369 one-submit invariant: no CLI/client key salting, no caller-side
  second submit, and manifests report only service-returned jobs.
- Task 371 public proof-shape authority: browser/product proof must use the
  HuleEdu Gateway `/sir-convert/v2/convert/jobs` surface and downstream Sir
  Convert correlation, not direct-host browser proof.

## Findings

No blocking findings.

The test stabilizations are truthful behavioral proof rather than bug masking:

- The PDF cancel/resume test now gates on a real persisted checkpoint before
  cancellation by wrapping `persist_pdf_checkpoint` and pausing only after
  `processed_pages > 0`. The assertion still proves cancel-with-save partials
  and resumed artifact byte equality with a baseline successful conversion.
- The metrics helper accepts `200` or `202` for `wait_seconds=0`, which matches
  the Service API v2 contract: a stubbed conversion can terminalize before the
  create-job response is returned. The test still waits for terminal status and
  asserts bounded metric labels and status behavior.
- The DigiExam correction-block test now polls the normal authenticated
  `GET /v2/convert/jobs/{job_id}` boundary until `succeeded` instead of assuming
  `wait_seconds=20` always completes under full-suite load. It validates the
  response JSON shape before extracting `job_id` and still proves the matching
  correction is rejected without leaking submitted pair labels.
- The parallel PDF tests only lengthen stubbed per-page conversion delays to
  preserve cancellation/checkpoint race windows. They still assert the same
  checkpoint, partial, resume, and parity outcomes.

The scoped diff does not widen canceled-job, idempotency, retry, Gateway, CLI,
or caller-side rerun semantics. There are no production-code changes in this
stabilization diff. The reviewed contracts still require canceled jobs to be
strict idempotent replays, retryable failed reattempts to be service-owned, and
CLI/client callers to avoid salting keys or submitting hidden second jobs.

Review 55 now approves only Task 371 implementation/proof-plan shape. It
explicitly states that public live proof has not been run and that approval is
limited to the implementation and Gateway-owned proof shape before deploy/live
proof.

`docs/backlog/INDEX.md` includes unrelated Task 372 and Review 56 entries
because it was generated from the current dirty tree. That is not a behavioral
blocker for this retained review and is not an approval of Task 372. It is a
commit-packaging risk: a final closeout commit must either include the
referenced Task 372/Review 56 docs intentionally, or regenerate/check the index
from the final intended staged scope so it does not retain links to omitted
files.

## Follow-up Actions

1. Before final commit/deploy packaging, refresh or verify generated indexes
   against the intended staged scope so `docs/backlog/INDEX.md` does not link to
   omitted Task 372/Review 56 files.
1. Do not treat this approval as deploy or public live proof. Task 369 and
   Task 371 still require their governed post-deploy/public proof gates.
1. Refresh `docs/backlog/INDEX.md` in the final docs-sync lane so this
   Review 57 artifact is indexed, unless the final packaging lane chooses a
   different retained-review reuse policy.

## Decision

approved

## Response

Approved for the scoped Task 369/Task 371 closeout stabilization diff. The test
changes preserve behavioral proof instead of weakening the relevant contracts,
Review 55 now approves only implementation/proof shape and not live proof, and
the reviewed diff does not reintroduce CLI/client salting, caller-side second
submit, widened canceled-job replay, or direct-host browser proof closure.

This approval excludes Task 372 implementation/review content. The generated
index coupling is acceptable for the current dirty-tree review only; final
commit packaging must not leave index links to files that are omitted from that
package.

## Verification Evidence

Reviewer-run commands:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_api_contract_v2_pdf_cancel_and_resume.py tests/sir_convert_a_lot/test_api_metrics_v2.py tests/sir_convert_a_lot/test_digiexam_correction_matching_blocked.py tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py -q
```

Result: passed, `18 passed in 14.97s`.

Read-only commands and inspections used:

- `git status --short`
- `git diff --name-status`
- `git diff --stat`
- `git diff -- tests/sir_convert_a_lot/test_api_contract_v2_pdf_cancel_and_resume.py`
- `git diff -- tests/sir_convert_a_lot/test_api_metrics_v2.py`
- `git diff -- tests/sir_convert_a_lot/test_digiexam_correction_matching_blocked.py`
- `git diff -- tests/sir_convert_a_lot/test_pdf_parallel_execution_contracts.py`
- `git diff -- docs/backlog/reviews/review-55-ruthless-review-of-task-371-audio-cli-public-browser-proof.md`
- `git diff -- docs/backlog/INDEX.md`
- `rg -n "review-55|review-56|task-371|task-372" docs/backlog/INDEX.md`

Overseer-reported evidence reviewed from the task prompt:

- Focused DigiExam node: `1 passed`.
- Scoped Ruff check/format check for the DigiExam test: passed/already
  formatted.
- `pdm run typecheck-all`: success, no issues in `899` source files.
- `pdm run format-all`: `948` files left unchanged.
- `pdm run lint-fix`: all checks passed; docs/backlog validated.
- `pdm run coverage-gate`: `1754 passed`, `6 skipped`, coverage `95.53%`.
- Task 368 focused replay node: `1 passed`.
- Task 368 broader contract set: `91 passed`.
- Task 371/369 CLI one-submit set: `21 passed`.
- Route registry node: `1 passed`.
- `pdm run docs-sync`, `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`: passed.

## Completion

Review complete with decision `approved`. The retained artifact records scope,
findings, decision, verification evidence, skipped checks, residual risk, and
follow-up actions. Post-artifact validation:

- `pdm run validate-tasks` initially failed because this file was missing the
  repo-required `Response`, `Follow-up Actions`, and `Completion` review
  sections; this patch adds those sections.
- `rg -n "[ \t]+$" docs/backlog/reviews/review-57-ruthless-review-of-task-369-371-closeout-stabilization.md`
  returned no matches as direct trailing-whitespace proof for the untracked
  review file.
- `pdm run docs-validate` failed after adding this review because
  `docs/backlog/INDEX.md` is stale and needs `pdm run docs-sync`. I did not run
  `docs-sync` because this review pass is restricted to editing only the
  retained review artifact.

## Skipped Checks And Residual Risk

- I did not rerun the full `coverage-gate`, `typecheck-all`, or docs-sync lane;
  the overseer had already rerun those after the final stabilization edit, and
  this review reran the focused changed-test slice independently.
- I did not run deploy, live proof, Gateway proof, browser automation, or Hemma
  production checks. Task 369 and Task 371 still require their governed
  deploy/live proof gates before final live closeout.
- I did not run `docs-sync` after adding this review artifact because the user
  explicitly restricted edits to the retained review artifact. The generated
  backlog index should be refreshed in the final closeout packaging lane;
  until then, `pdm run docs-validate` fails on stale `docs/backlog/INDEX.md`.
- The unrelated Task 372/Review 56 generated-index coupling must be resolved by
  final staging discipline: do not commit an index that references omitted
  files.

## Checklist

- [x] Scope reviewed
- [x] Findings captured
- [x] Decision recorded
- [x] Verification evidence recorded
- [x] Skipped checks and residual risk recorded
- [x] Review closed
