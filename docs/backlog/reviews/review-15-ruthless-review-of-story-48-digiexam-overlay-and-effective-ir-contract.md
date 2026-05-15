---
id: review-15-ruthless-review-of-story-48-digiexam-overlay-and-effective-ir-contract
title: Ruthless review of Story 48 DigiExam overlay and effective IR contract
type: review
status: responded
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
labels:
  - review
  - story-48
  - digiexam
  - overlay
  - effective-ir
  - answer-key-completion
  - changes-requested
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless docs-as-code contract review of Story 48.
- Governing authority:
  - `AGENTS.md`
  - `docs/backlog/README.md`
  - `docs/_meta/docs-contract.yaml`
  - `docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md`
  - `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `docs/converters/digiexam-intermediate-exam-representation-contract.md`
  - `docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md`
  - `docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md`
- File reviewed:
  - `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
- Public surfaces affected:
  - `digiexam_migration_bundle_v2`
  - optional multipart `digiexam_ingestion_overlay`
  - `digiexam_ingestion_overlay_v1`
  - `digiexam_effective_exam_v1`
  - `target_readiness_report_v1`
  - named artifacts `effective_ir_json`, `ingestion_overlay_report`, and
    `target_readiness_report`
  - QTI/manual-unkeyed export readiness after
    `accept_current_state_for_export`
- Compatibility posture:
  - Story 48 deliberately carries a hard
    `digiexam_migration_bundle_v2` contract break with no v1 compatibility
    shim, source-only fallback lane, or dual-version response mode.
  - Source IR remains parser-owned. Teacher overlays, review decisions, and
    reviewed completion may affect only effective renderer input and effective
    provenance.
- Evidence reviewed:
  - Line-numbered inspection of Story 48.
  - Related Task 294, 295, 298, 303, 305, and 306 docs.
  - Converter contract sections for overlay, effective IR, bundle entries, and
    target readiness.
  - QTI reference sections for Task 303 manual/unkeyed profile status.
  - `pdm run docs-validate` -> `Validated 384 backlog files` and
    `Validated docs=450 rules=11`.

## Findings

1. [ ] `blocker` - Story 48 omits required privacy and provenance exclusions
   from the overlay acceptance surface.

   - Evidence:
     Story 48 only requires the service API contract to reject
     `raw/base64 asset payloads` at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:84`
     and repeats only `forbidden raw/base64 payloads` in test requirements at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:115`.
     Task 295 and the converter contract are stricter: overlays and
     product-visible outputs must not expose raw `.dxe`, raw PDF text,
     result-PDF content/student data, raw overlay JSON, raw model responses,
     identity markers, earned scores, wrong selections, free-text student
     answers, performance history, or raw/base64 assets.
   - Why it matters:
     Story 48 is the governing story for the overlay/effective-IR lane. If its
     acceptance surface only names raw/base64 assets, a future remediation can
     satisfy the story while still allowing raw result-PDF or student-derived
     data to leak through overlay, report, effective IR, manifest, or product
     outputs. That breaks the established DigiExam privacy/provenance contract.
   - Required fix:
     Harden Story 48 scope, acceptance criteria, and test requirements so the
     story explicitly forbids raw `.dxe`, raw PDF text, result-PDF content,
     student data, raw overlay JSON, raw model responses, full exam-level
     metadata where not route-owned, identity markers, scores, wrong
     selections, free-text student answers, performance history, and raw/base64
     asset payloads from overlay input and product-visible outputs.
   - Proof requirement:
     Add or update contract tests for overlay validation and emitted reports
     proving those forbidden payload classes are rejected or absent. Run
     `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
     plus `pdm run docs-validate`.

1. [ ] `high` - Story 48's unkeyed/manual QTI wording is stale after completed
   Task 303.

   - Evidence:
     Story 48 still says to define a later governed unkeyed/manual QTI profile
     so `accept_current_state_for_export` can enable QTI only when the selected
     QTI package is schema-valid and target-valid at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:71`.
     It also marks the Task 303 acceptance item complete at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:107`.
     Task 303 is now completed and defines the `unkeyed_manual_qti_2_1_v1`
     preservation profile, validation semantics, and remaining limits.
   - Why it matters:
     A future implementer can read Story 48 as both saying the QTI profile is
     future work and saying that work is already accepted. That muddies the
     target-readiness contract for `accept_current_state_for_export`, especially
     for consumers deciding whether QTI can be enabled after teacher acceptance.
   - Required fix:
     Replace the stale "later governed profile" language with current-state
     wording: Task 303 has defined the first manual/unkeyed QTI profile, and
     Story 48 remediation must preserve the profile's validation, unsupported
     resource, target-readiness, and vendor-unproven constraints.
   - Proof requirement:
     Keep or add QTI readiness tests for accepted-current-state under the
     manual/unkeyed profile and run the focused Task 303/API tests named in the
     task, plus `pdm run docs-validate`.

1. [ ] `medium` - The matching and gapped/open-cloze sequencing is not enforced
   by Story 48 acceptance criteria.

   - Evidence:
     Story 48 scope says matching pair and gapped/open-cloze accepted-value
     answer-key shapes must be first-class contracts before reviewed completion
     or target export may treat those shapes as automatically evaluated at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:77`.
     The acceptance criteria and test requirements do not explicitly require
     Task 306 to remain disabled for matching/gapped completion until Tasks 298
     and 305 are complete.
   - Why it matters:
     The story can appear satisfied while leaving the critical sequencing guard
     as prose only. That invites an implementation where reviewed completion
     applies matching pairs or gap accepted values before the IR has exact
     ID-bound fields, which would collapse advisory/manual review into
     target-specific or prompt-text inference.
   - Required fix:
     Add Story 48 acceptance criteria and tests requiring reviewed completion to
     reject or leave manual-follow-up state for matching and gapped/open-cloze
     items until Task 298 and Task 305 provide first-class IR/effective-IR
     fields and validation rules.
   - Proof requirement:
     Add focused tests proving Task 306 application cannot apply matching pairs
     or gap accepted values without the completed pair/value contracts. Run the
     focused answer-key completion tests once those surfaces exist, plus
     `pdm run docs-validate`.

1. [ ] `medium` - Story 48 state mixes completed child slices with remaining
   proposed blockers.

   - Evidence:
     Story 48 is `status: proposed` at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:5`,
     but several related child tasks are completed and several acceptance
     criteria are checked at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:104`.
     The story still has unchecked implementation, validation, and docs
     checklist items at
     `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md:133`.
   - Why it matters:
     The story is now a mixed roll-up of completed Tasks 294, 295, 302, 303,
     and 304 plus remaining proposed Tasks 298, 305, and 306. Without a
     "completed versus remaining slices" section, the next agent can either
     re-open completed runtime work or skip the proposed blockers because the
     story already has checked acceptance items.
   - Required fix:
     Add an explicit current-state section naming completed child tasks,
     remaining blockers, and the exact task order for the remaining story
     closeout. Keep Story 48 status/checklist aligned with that state.
   - Proof requirement:
     Run `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check` after the story state is corrected.

## Decision

changes_requested

## Response

Story 48 remediation was applied on 2026-05-15:

- privacy/provenance exclusions were expanded in Story 48 scope, acceptance,
  and test requirements to cover raw `.dxe`, raw PDF text, result-PDF content
  or student data, raw overlay JSON, raw model responses, unowned full
  exam-level metadata, identity markers, scores, wrong selections, free-text
  student answers, per-student performance history, and raw/base64 assets;
- stale Task 303 wording was replaced with the completed
  `unkeyed_manual_qti_2_1_v1` profile and its validation,
  unsupported-resource, manual/unkeyed follow-up, and vendor-unproven import
  limits;
- Story 48 acceptance and test requirements now require Task 306 to keep
  matching and gapped/open-cloze reviewed completion disabled until Tasks 298
  and 305 provide first-class pair/value contracts and validators;
- Story 48 now separates completed child slices from remaining proposed
  blockers so completed Tasks 294, 295, 302, 303, and 304 are not reopened by
  default and remaining closeout order is explicit.

This response does not close the review; an independent re-review must verify
the remediation before the decision changes.

## Follow-up Actions

1. Harden Story 48 privacy/provenance acceptance and tests so they match Task
   295 and the converter contract.
1. Refresh Story 48 QTI wording against completed Task 303 and the current
   manual/unkeyed profile.
1. Add Story 48 acceptance gates for Tasks 298, 305, and 306 sequencing.
1. Clarify Story 48 current state by separating completed child slices from
   remaining blockers.

## Completion

Review retained on 2026-05-15 with `changes_requested`. Response and closeout
are pending.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [ ] Follow-up tasks linked
- [ ] Review closed
