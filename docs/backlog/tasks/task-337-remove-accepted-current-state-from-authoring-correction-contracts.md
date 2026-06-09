---
id: task-337-remove-accepted-current-state-from-authoring-correction-contracts
title: Remove accepted-current-state from authoring correction contracts
type: task
status: completed
priority: critical
created: '2026-05-19'
last_updated: '2026-06-04'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-333-implement-non-matching-unified-correction-apply-runtime-for-digiexam-pr-0332.md
  - docs/backlog/tasks/task-336-implement-correction-replay-artifact-references-for-skriptoteket-pr-0339.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder.md
  - docs/backlog/tasks/task-316-extract-target-readiness-policy-decisions-from-artifact-availability-and-target-string-branches.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
  - docs/reference/ref-examnet-pdf-to-exam-swedish-renderer-profile.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0341-st-21-04-authoring-export-boundary-separation.md
labels:
  - exam-authoring
  - corrections
  - export-boundary
  - skriptoteket
---

## Remove Accepted-Current-State From Authoring Correction Contracts

## Objective

Remove `accept_current_state_for_export` from Sir Convert's authoring
correction and overlay state models. The approved product boundary is now:
authoring corrections mutate effective exam state; export policy consumes
effective exam state and produces artifacts. Export policy must not be encoded
as a correction entry, review decision, source overlay, answer-key substitute,
or target-readiness unlock inside authoring replay.

## Product Decision

- Missing answer keys remain missing until the teacher supplies real authoring
  corrections.
- Sir Convert correction apply must not accept `review_decision` /
  `accept_current_state_for_export` as a supported authoring correction kind.
- The DigiExam ingestion overlay path must not use accepted-current-state to
  turn missing-key rows into export-enabled manual/unkeyed artifacts.
- Existing manual/unkeyed renderer helpers may be deleted or retained only if a
  separate export-only task uses them directly. They must not be reachable from
  authoring/correction replay.
- If best-effort incomplete export is reintroduced later, it must be an
  explicit export request policy, not authoring state, and it needs a separate
  governed contract.
- Story 50 / Task 315 PDF strategy extraction must not normalize the old
  accepted-current-state path into the durable PDF strategy model. Until an
  export-only request contract exists, the correct strategy behavior for missing
  keys is to keep targets blocked rather than produce manual/unkeyed export
  bytes from correction replay.

## PR Scope

- Remove `ExamAuthoringReviewDecisionCorrectionV1` and the
  `review_decision.kind == "accept_current_state_for_export"` mapping from the
  correction apply API contract, Pydantic models, OpenAPI schemas, replay
  overlay builder, and runtime apply path.
- Remove `DigiExamOverlayReviewDecision` / `review_decision` from
  `digiexam_ingestion_overlay_v2` if it only exists to authorize
  accepted-current-state export.
- Remove `ready_after_accepted_current_state`,
  `needs_teacher_review_decision`, accepted-current-state reason codes, and
  accepted-current-state artifact availability unlocks from target-readiness
  generation.
- Remove or rewrite QTI/PDF tests that prove accepted-current-state enables
  manual/unkeyed exports. Replace them with tests proving missing keys keep
  targets blocked unless real answer-key corrections are present.
- Update converter contracts, reference docs, ADR/task references, generated
  OpenAPI, and downstream guidance for Skriptoteket `PR-0341`.

## Non-Goals

- No best-effort/manual incomplete export mode in this task.
- No compatibility shim, route alias, wrapper, deprecated field parser, or
  fallback for `review_decision`.
- No source IR or effective IR schema mutation beyond removing export-policy
  state from authoring/correction surfaces.
- No matching producer enablement.

## Deliverables

- [ ] Correction apply contract and generated schema remove `review_decision`.
- [ ] DigiExam ingestion overlay and replay runtime no longer accept or apply
  accepted-current-state export decisions.
- [ ] Target-readiness output no longer emits accepted-current-state readiness
  classes or reason codes.
- [ ] QTI/PDF artifact builders are reachable from correction replay only with
  real authoring/effective state, not accepted-current-state item IDs.
- [ ] Converter contracts, reference docs, generated OpenAPI, and tests reflect
  the authoring/export boundary.

## Open Questions Closed

1. Should Sir Convert keep accepting `accept_current_state_for_export` for
   correction replay?
   - Decision: no. Correction replay is authoring-state replay.
1. Should missing-key artifacts still be downloadable through manual/unkeyed
   fallbacks?
   - Decision: no active path. Missing-key targets are blocked until keys are
     supplied through authoring corrections.
1. Should legacy accepted-current-state tests remain as compatibility coverage?
   - Decision: no. Rewrite them as negative tests or delete them.
1. Where should future incomplete export live?
   - Decision: in a future export-only request contract, if approved.

## Acceptance Criteria

- [ ] `POST /v2/exam-authoring/corrections/apply` generated schemas expose no
  `review_decision` correction entry and reject any such submitted payload.
- [ ] DigiExam correction replay can render corrected PDF/QTI artifacts only
  from real source/effective answer-key, point, or text corrections.
- [ ] Missing choice or gap/open-cloze answer keys produce non-exportable
  readiness rows until corrected answer-key state exists.
- [ ] Target-readiness reports contain no
  `ready_after_accepted_current_state`,
  `needs_teacher_review_decision`,
  `accepted_current_state_manual_unkeyed_profile`, or
  `accepted_current_state_pdf_manual_unkeyed_profile` values.
- [ ] No authoring/correction path passes accepted-current-state item IDs into
  QTI/PDF artifact builders.
- [ ] Generated OpenAPI and converter docs match the new authoring/export
  boundary.

## Follow-up Test-contract Closeout

2026-06-04 follow-up closed the leftover coverage-gate failures that still
encoded the superseded `TASK-303` accepted-current-state QTI/PDF behavior.

- Rewrote legacy QTI sample assertions so missing-key choice and gap/open-cloze
  examples now prove blocked QTI reports and no generated `qti-package.zip`.
- Kept the synthetic manual matching sample as an export-only/manual free-text
  preservation sample, not as an authoring/correction replay unlock.
- Updated the reviewed gap-completion PDF assertion to expect `Typ: Lucktext`
  with retained accepted values, aligning with `TASK-315` and `TASK-321`.
- Verified the original seven failing coverage-gate node IDs now pass.

## Validation Plan

- Focused correction apply tests for schema rejection and missing-key blocking.
- Focused DigiExam replay artifact tests proving corrected downloads remain
  enabled when real authoring corrections provide keys.
- QTI/PDF renderer or artifact tests proving no accepted-current-state item ID
  path remains reachable from authoring replay.
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- focused `pdm run pytest-root ...`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if removing accepted-current-state would require weakening source-state
  signatures, item fingerprints, answer-key provenance, or replay artifact
  authority.
- Stop if a consumer still requires incomplete export in the same release; that
  must become a separate export-only task before implementation continues.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
