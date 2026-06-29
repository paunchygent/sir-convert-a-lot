---
id: 'story-57-cross-repo-compact-answer-key-review-state-production-proof'
title: 'Cross-repo compact answer-key review state production proof'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/stories/story-21-11-cross-repo-compact-answer-key-review-state-production-proof.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0406-st-21-04-exam-converter-consume-compact-answer-key-review-state.md
labels:
  - exam-migration
  - answer-key-review
  - cross-repo
  - production-proof
  - skriptoteket
---
Cross-repo overseer tracking story for Sir Convert producer work and
Skriptoteket consumer proof.

## Objective

Make Sir Convert the single producer of compact DigiExam answer-key review
state and prove, through Skriptoteket production UI, that teachers can review,
save, replay, export, and return to a corrected DXE conversion without
Skriptoteket re-deriving answer-key truth locally.

## Scope

- Sir Convert Task 373 owns the producer contract:
  `digiexam_answer_key_review_state_v1`,
  `answer_key_review_state_report`, correction-apply
  `answer_key_review_state`, strict state/origin/reason vocabulary, bounded
  `provenance_detail`, and no legacy `history` / `review_decision`
  compatibility surface.
- Skriptoteket PR-0406 owns consumption through the mirrored Skriptoteket story
  and must not define producer semantics locally.
- Final proof uses this tracked fixture:
  `inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1776888013-ak7-lag-och-ratt.dxe`.
- If that fixture cannot exercise one required interaction family, the
  overseer may add one more tracked fixture from the same corpus, but must
  record why one file was insufficient.

## Overseer Implementation Handoff

You are the overseer. Run Task 373 first with `implementation_agent`, then a
fixed `ruthless_review_agent` until the retained review is approved. Only after
Task 373 is approved may Skriptoteket PR-0406 start. Do not inspect partial
worker diffs while a worker or reviewer is active.

Task 373 success means producer tests and contract docs prove the compact
projection. PR-0406 success means the UI consumes that projection through one
adapter and no longer uses local IR/effective-IR/correction-session joins as
answer-key review truth. The cross-repo story is complete only after the final
production browser proof below passes and is retained in both repos.

## Acceptance Criteria

- [ ] Task 373 closes the state vocabulary as strict producer codes:
  `review_required`, `review_complete`, `teacher_modified`,
  `validation_required`.
- [ ] Task 373 closes key origin as strict producer codes:
  `none`, `source_provided`, `reviewed_advisory`, `teacher_authored`,
  `teacher_edited_advisory`, `mixed`.
- [ ] Task 373 emits both the first-pass named artifact
  `answer_key_review_state_report` and top-level correction-apply
  `answer_key_review_state`.
- [ ] Task 373 exposes bounded `provenance_detail` only; schema/tests reject
  generic `history`, `review_decision`, and accepted-current-state substitute
  fields.
- [ ] Task 373 uses one shared projection builder for bundle generation and
  correction apply/replay result generation.
- [ ] Task 373 keeps target readiness separate from item review state; the
  compact projection cannot unlock PDF/QTI.
- [ ] PR-0406 consumes the producer projection through one narrow adapter and
  fails closed on unknown schema versions, unknown state/origin/reason codes,
  missing projection, or missing replay artifact references.
- [ ] PR-0406 proves list/detail/report/mobile labels from producer state:
  pending advisory -> `Granska`; reviewed complete -> plain `Klart`; teacher
  modified -> teacher-owned with no AI marker; missing key/value ->
  `Kontrollera` with current validation reason.
- [ ] PR-0406 proves local saved intent is draft/readback only until Sir
  Convert replay returns fresh projection/readiness evidence.
- [ ] Final production browser proof uses a real browser against the production
  Skriptoteket surface and records redacted evidence for each step in the gate
  below.

## Final Live Browser Gate

Run this only after Task 373, PR-0406, retained reviews, deploys, and health
checks are complete.

1. Authenticate through the HuleEdu browser-session ceremony at production
   Skriptoteket. Do not use direct product-backend credential posts, direct
   browser-authored identity headers, or browser-direct Sir Convert calls.
1. Upload the named DXE fixture through the production Exam Converter UI.
1. Verify the first-pass Sir Convert job returns
   `answer_key_review_state_report`, `target_readiness_report_v1`, PDF, and
   QTI artifacts where readiness permits.
1. Verify the question list and detail view render compact state from the
   producer projection across desktop and mobile viewport checks.
1. Exercise every supported teacher interaction available for the fixture:
   accept an unchanged advisory key, edit a suggested key or keyed content,
   create/fix a missing choice or gap/open-cloze key, save facit, navigate
   between items, open report, open files, and return to questions.
1. Verify Skriptoteket persists the teacher intents, replays the complete
   supported correction set through Gateway/Sir Convert correction apply, and
   renders the returned `answer_key_review_state` without local review-state
   inference.
1. Verify PDF/QTI download and save actions remain disabled until Sir Convert
   target readiness and replay artifact references allow them.
1. Download and save the corrected PDF and QTI when readiness allows it; verify
   downloaded artifacts are replay-scoped and not original stale job artifacts.
1. Reload the app and reopen the conversion; verify readback plus Sir Convert
   replay/projection still drives visible state.
1. Retain a redacted proof bundle with request ids/correlation ids, screenshots,
   artifact names, projection snippets, readiness snippets, download/save
   evidence, and a no-forbidden-browser-authority grep/check.

## Test Requirements

- [ ] Red-first Sir Convert tests for bundle artifact, apply response,
  state/origin/reason vocabulary, missing key/value reasons, rejected legacy
  fields, replay artifact references, and OpenAPI/schema export.
- [ ] Red-first Skriptoteket tests for parser rejection, exhaustive state
  mapping, desktop/mobile rendering, stale replay/local draft behavior, report,
  files, and replay artifact authority.
- [ ] Retained independent review artifacts approve Task 373 and PR-0406 before
  final production proof starts.

## Done Definition

This story is done only when Sir Convert Task 373 and Skriptoteket PR-0406 are
implemented, independently approved, deployed as needed, and the final live
browser gate passes with retained redacted evidence linked from both repos.

## Checklist

- [ ] Task 373 approved
- [ ] PR-0406 approved
- [ ] Production deploys healthy
- [ ] Final live browser proof retained
- [ ] Docs synchronized
