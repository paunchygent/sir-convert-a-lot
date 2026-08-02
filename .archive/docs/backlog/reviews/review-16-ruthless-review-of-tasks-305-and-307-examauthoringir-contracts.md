---
id: review-16-ruthless-review-of-tasks-305-and-307-examauthoringir-contracts
title: Ruthless review of Tasks 305 and 307 ExamAuthoringIR contracts
type: review
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md
  - docs/converters/exam-authoring-ir-v1-contract.md
labels:
  - review
  - task-305
  - task-307
  - exam-authoring-ir
  - accepted
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-implementation review of Tasks 305 and 307.
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/000-rule-index.md`
  - `docs/backlog/README.md`
  - `docs/_meta/docs-contract.yaml`
  - `docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md`
  - `docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md`
  - `docs/converters/exam-authoring-ir-v1-contract.md`
- Primary files reviewed:
  - `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`
  - `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py`
  - `tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
  - `tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`
  - `docs/converters/exam-authoring-ir-v1-contract.md`
- Public surfaces affected:
  - `ExamAuthoringIR v1` matching and gap/open-cloze value objects.
  - Source-adapter boundary for DigiExam and future Exam.net PDF, DOCX, and
    Markdown source adapters.
  - Target-readiness rows for unsupported gap/open-cloze target shapes.
- Compatibility posture:
  - These are additive source-neutral authoring slices, but they become
    contract authority for later source adapters, reviewed completion, and
    target validators. Invalid or under-specified shapes must fail closed now.
- Evidence reviewed:
  - Line-numbered inspection of task docs, converter contract docs, runtime
    value objects, adapters, target readiness, and focused tests.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`
    -> 14 passed.
  - `pdm run python` probe showing negative matching bounds currently validate
    as `valid=True`.

## Findings

1. [x] `blocker` - Task 305's accepted-value contract cannot preserve mixed
   source/manual/reviewed provenance per value.

   Evidence:

   - Task 305 requires source-bound parser provenance to remain separate from
     teacher/manual or reviewed effective answer-key provenance at
     `docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md:94`.
   - The task also marks complete the criterion that neutral data can carry
     teacher/manual or later reviewed accepted values without rewriting
     source-adapter provenance at
     `docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md:136`.
   - The implementation puts typed provenance only on
     `ExamAuthoringGapAnswerKey.provenance` at
     `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:92`.
     Individual `ExamAuthoringGapAcceptedValue` entries carry only `gap_id`,
     `value`, and untyped evidence at
     `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:83`.
   - The DigiExam adapter maps the whole answer key to one provenance value at
     `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py:86`,
     while accepted values only receive evidence records at
     `scripts/sir_convert_a_lot/domain/digiexam_exam_authoring_adapter.py:89`.

   Why it matters:
   Multi-gap and multi-value items can legitimately mix source-provided values,
   teacher-provided values, and later reviewed values. With one item-level
   provenance, a later overlay or reviewed application must either relabel the
   whole key as teacher/reviewed and lose source provenance, or keep the whole
   key source-provided and hide manual/reviewed intervention. That breaks the
   effective-IR provenance contract before Task 306 consumes this surface.

   Required fix:
   Move answer-key provenance to the accepted-value granularity, or introduce a
   typed accepted-value provenance record that includes `gap_id`, `value`,
   provenance, and evidence. Keep any aggregate answer-key provenance as a
   derived summary only. Validation must count trusted accepted values per
   required gap from per-value provenance and reject accepted values whose typed
   provenance is absent or inconsistent with evidence.

   Proof requirement:
   Add focused tests for an interaction where one required gap has a
   source-provided value and another has a teacher-provided or reviewed value.
   Prove automatic evaluation readiness stays true without rewriting the
   source value's provenance. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`.

1. [x] `blocker` - Task 307's matching validator accepts invalid association
   bounds.

   Evidence:

   - Task 307 requires source-neutral matching source choices, target choices,
     and per-choice association bounds at
     `docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md:88`.
   - The converter contract says the neutral validator rejects interaction
     association-count violations and per-choice association-limit violations
     at `docs/converters/exam-authoring-ir-v1-contract.md:72`.
   - The runtime model exposes `match_min`, `match_max`,
     `min_associations`, and `max_associations` as unconstrained integers at
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:66` and
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:92`.
   - Validation only checks observed pair counts through `_within_bounds(...)`
     at `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:184`
     and `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:197`;
     `_within_bounds(...)` treats `maximum == 0` as unbounded but never rejects
     negative minimums, negative maximums, or `max < min` at
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:339`.
   - A live probe with `min_associations=-1` and source `match_min=-1`
     returned `ExamAuthoringMatchingValidationResult(valid=True, issues=())`.

   Why it matters:
   Future source adapters can emit nonsensical bounds and still receive a valid
   `ExamAuthoringIR v1` interaction. Target exporters then have to guess
   whether `-1`, `max < min`, or invalid per-choice bounds mean unbounded,
   impossible, or malformed. That is exactly the source-neutral contract drift
   Task 307 was meant to prevent.

   Required fix:
   Add explicit bound-shape validation before pair-count validation. Require
   all minimums to be non-negative, all maximums to be non-negative, and every
   non-zero maximum to be greater than or equal to its minimum. Keep `0` as the
   documented unbounded maximum only if that is the intended contract, and add
   stable issue codes for invalid interaction bounds and invalid choice bounds.

   Proof requirement:
   Add matching tests for negative interaction minimum, negative choice
   minimum, negative maximum, and `max < min` for both source and target
   choices. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`.

1. [x] `blocker` - Task 307 now accepts opaque `mixed` matching provenance
   without per-pair provenance.

   Evidence:

   - The Task 305 remediation added `mixed` to the shared
     `ExamAuthoringAnswerKeyProvenance` enum in
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`.
   - That enum is also used by `ExamAuthoringMatchingAnswerKey`, whose public
     shape still has only aggregate `provenance` and `pairs` fields.
   - Task 298 and Task 307 require matching provenance/evidence hooks and
     source-bound parser provenance to remain separable from teacher/manual or
     reviewed effective provenance.
   - A re-review probe built a matching interaction with
     `ExamAuthoringAnswerKeyProvenance.MIXED` and one directed pair; the
     validator returned `ExamAuthoringMatchingValidationResult(valid=True, issues=())`.

   Why it matters:
   `mixed` is meaningful only when the contract can say which pair or value is
   source-provided, teacher-provided, or reviewed. The gap contract now has
   value-level provenance, but matching pairs do not. Accepting aggregate
   `mixed` on matching therefore creates an opaque provenance state that later
   exporters and reviewed-completion code cannot audit. It reintroduces the
   same provenance collapse Task 305 just fixed, now on Task 307's matching
   surface.

   Required fix:
   Either keep `mixed` out of the shared provenance enum used by matching, or
   make the matching validator reject `MIXED` until matching pairs carry typed
   per-pair provenance. If mixed matching provenance is required now, add a
   first-class per-pair provenance/evidence shape and derive the aggregate
   summary from those pairs, mirroring the accepted-value gap contract.

   Proof requirement:
   Add a matching contract test proving `ExamAuthoringMatchingAnswerKey` with
   aggregate `MIXED` is rejected unless per-pair provenance exists. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`.

1. [x] `blocker` - Task 305 still accepts opaque `mixed` provenance on an
   individual gap accepted value.

   Evidence:

   - The shared `ExamAuthoringAnswerKeyProvenance` enum includes `MIXED` at
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:37`.
   - `ExamAuthoringGapAcceptedValue` uses that enum directly at
     `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:92`.
   - The gap validator only rejects `ABSENT` accepted-value provenance at
     `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:349`;
     it does not reject value-level `MIXED`.
   - Required-gap readiness counts any non-`ABSENT` value as trusted at
     `scripts/sir_convert_a_lot/domain/exam_authoring_gap_contracts.py:411`.
   - A live re-review probe built one required gap with one accepted value whose
     provenance was `MIXED`; validation returned
     `ExamAuthoringGapValidationResult(valid=True, automatic_evaluation_ready=True, target_export_ready=True, issues=())`.

   Why it matters:
   Review 16's original Task 305 blocker was about avoiding opaque aggregate
   provenance by moving trust to each accepted value. Letting one value itself
   be `mixed` recreates the same opacity at the trust unit Task 306 must consume:
   the effective IR cannot tell whether that answer came from source evidence,
   a teacher key, or reviewed completion.

   Required fix:
   Keep `mixed` as a derived `ExamAuthoringGapAnswerKey.provenance` summary only.
   Reject `ExamAuthoringGapAcceptedValue.provenance == MIXED`, or split the enum
   so accepted values can only use concrete trust states:
   `source_provided`, `teacher_provided`, or `reviewed`. The summary may remain
   `absent` for no values and `mixed` when multiple concrete value provenances
   are present.

   Proof requirement:
   Add a gap contract test proving a value-level `MIXED` accepted value fails
   validation and blocks automatic evaluation, while a source-plus-teacher
   multi-value key still derives aggregate `MIXED`. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`.

1. [x] `blocker` - Task 307 still accepts keyed matching pairs with `absent`
   answer-key provenance.

   Evidence:

   - `ExamAuthoringMatchingAnswerKey` stores aggregate provenance and directed
     pairs at `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:90`.
   - Task 298 says absent provenance is the state when no trusted matching pairs
     exist at
     `docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md:70`.
   - The matching validator only rejects aggregate `MIXED` provenance at
     `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py:337`; it
     does not reject non-empty pairs with `ABSENT` provenance.
   - A live re-review probe built one exact source-target pair with
     `ExamAuthoringAnswerKeyProvenance.ABSENT`; validation returned
     `ExamAuthoringMatchingValidationResult(valid=True, issues=())`.

   Why it matters:
   `ABSENT` means no trusted answer key. If the validator accepts concrete pairs
   while provenance says absent, Task 306 and target exporters can machine-apply
   or export matching answers with no trust state. That collapses the source,
   teacher, and reviewed provenance boundary Review 16 is supposed to protect.

   Required fix:
   Add a matching validation issue for non-empty `pairs` with `ABSENT`
   provenance. Reviewed application can still emit whole-key `REVIEWED`; teacher
   overlays can emit `TEACHER_PROVIDED`; source adapters with real matching
   evidence can emit `SOURCE_PROVIDED`. `ABSENT` must remain the no-key state.

   Proof requirement:
   Add a matching contract test proving non-empty pairs with `ABSENT` provenance
   fail validation, and keep the existing reviewed whole-key proof green. Run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`.

## Decision

approved

## Response

Remediation implemented on 2026-05-15 and ready for re-review.

- Task 305 gap/open-cloze accepted values now carry typed provenance on each
  `ExamAuthoringGapAcceptedValue`. `ExamAuthoringGapAnswerKey.provenance` is a
  derived summary only and may become `mixed` when one item combines
  source-provided, teacher-provided, or reviewed accepted values.
- Gap validation counts trusted required gaps from value-level provenance,
  rejects values with `absent` provenance, and rejects values whose known
  evidence origin contradicts their typed provenance.
- Task 307 matching validation now rejects malformed interaction bounds and
  malformed source/target choice bounds before pair-count checks. `0` remains
  the documented unbounded maximum; negative bounds and non-zero `max < min`
  fail as invalid neutral IR.
- Focused regression proof added for mixed source/teacher gap provenance,
  absent/inconsistent gap provenance, negative interaction bounds, negative
  choice bounds, negative maximums, and `max < min` for source and target
  choices.

Re-review on 2026-05-15 accepted the remediation:

- `ExamAuthoringGapAcceptedValue` now carries typed value-level provenance, and
  `ExamAuthoringGapAnswerKey.provenance` is derived as `absent`, a single
  concrete provenance, or `mixed`.
- Gap validation rejects accepted values with `absent` provenance and known
  evidence/provenance mismatches while preserving mixed source/teacher values
  as automatically evaluable when all required gaps have trusted values.
- Matching validation rejects negative interaction bounds, negative choice
  bounds, negative maximums, and non-zero `max < min` before pair-count checks.
- Re-review probe confirmed the old negative-bounds case now returns
  `valid=False`, and a mixed source/teacher gap case returns `valid=True` with
  derived `mixed` provenance.

The same re-review found one new blocking issue: `mixed` provenance now leaks
into matching answer keys through the shared provenance enum, but matching
pairs do not carry per-pair provenance. Task 307 therefore remains blocked
until aggregate `mixed` matching provenance is rejected or matching pairs gain
first-class typed provenance.

Second remediation implemented on 2026-05-15 and ready for re-review:

- Task 307 matching validation now rejects aggregate
  `ExamAuthoringAnswerKeyProvenance.MIXED` with
  `mixed_matching_provenance_without_pair_provenance` until matching pairs
  carry first-class per-pair provenance/evidence.
- Reviewed whole-key matching provenance remains valid, so future reviewed
  LLM-derived matching keys can be applied as one complete reviewed pair set
  without claiming opaque mixed pair provenance.
- Contract docs now state that LLM completion metadata is candidate lineage,
  not parser/source provenance. Teacher-accepted unchanged candidates become
  reviewed effective keys with lineage; teacher-edited candidates become
  teacher-provided effective keys with lineage; neither path uses aggregate
  `mixed` matching provenance.
- Proof run: focused ExamAuthoringIR matching/gap tests passed with
  `21 passed`; `format-all`, `lint-fix`, `typecheck-all`, `docs-sync`,
  `docs-validate`, `skills-validate`, `handoff-validate`, `coverage-gate`
  (`1240 passed, 5 skipped`, coverage `95.43%`), and `git diff --check`
  passed.

Second re-review on 2026-05-15 requested changes:

- Focused tests still pass (`21 passed`), but live probes found two remaining
  provenance trust bypasses before Task 306 can consume the contract:
  value-level `mixed` gap provenance is accepted as automatically evaluable,
  and non-empty matching pairs are accepted with aggregate `absent` provenance.

Third remediation implemented on 2026-05-15 and ready for re-review:

- Task 305 gap validation now rejects
  `ExamAuthoringGapAcceptedValue.provenance == MIXED` with
  `accepted_gap_open_cloze_value_with_mixed_provenance`. Mixed provenance remains
  a derived `ExamAuthoringGapAnswerKey.provenance` summary only.
- Required-gap automatic evaluation now counts only concrete accepted-value
  provenance states: `source_provided`, `teacher_provided`, and `reviewed`.
- Task 307 matching validation now rejects non-empty directed pair sets with
  `ExamAuthoringAnswerKeyProvenance.ABSENT` using
  `absent_matching_provenance_with_pairs`. `ABSENT` remains the no-trusted-key
  state.
- Focused regression proof:
  `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py tests/sir_convert_a_lot/test_exam_authoring_gap_contracts.py`
  passed with `23 passed`.
- Live probes for the two re-review bypasses now fail closed:
  `gap_mixed_probe False False` with
  `accepted_gap_open_cloze_value_with_mixed_provenance`, and
  `matching_absent_pairs_probe False` with
  `absent_matching_provenance_with_pairs`.
- Closeout gates passed: `format-all`, `lint-fix`, `typecheck-all`,
  `coverage-gate` (`1250 passed, 5 skipped`, coverage `95.46%`),
  `docs-sync`, `docs-validate`, `skills-validate`, `handoff-validate`, and
  `git diff --check`.

Third re-review on 2026-05-15 accepted the remediation:

- Value-level `mixed` gap provenance now fails contract validation and blocks
  automatic evaluation; aggregate gap `mixed` remains a derived summary only.
- Non-empty matching pairs with `absent` provenance now fail validation.
- Live probes confirmed the two previously accepted bypass shapes now return
  `valid=False`.

## Follow-up Actions

1. Completed: fix the Task 305 per-accepted-value provenance shape before Task 306 consumes
   gapped/open-cloze values.
1. Completed: fix the Task 307 matching bound-shape validator before new matching-capable
   source adapters are implemented.
1. Completed: reject aggregate `mixed` matching provenance before new
   matching-capable source adapters are implemented.
1. Completed: reject value-level `mixed` gap accepted-value provenance before
   Task 306 consumes accepted values.
1. Completed: reject non-empty matching pairs with `absent` provenance before
   Task 306 consumes matching pairs.

## Completion

Review opened on 2026-05-15 with blocking findings. Original blocker
remediation was re-reviewed on 2026-05-15, but the shared provenance change
introduced one remaining Task 307 blocker. Second remediation was implemented
on 2026-05-15. Second re-review on 2026-05-15 found two remaining provenance
trust blockers. Third remediation was re-reviewed and accepted on 2026-05-15.
Review closed as `approved`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
