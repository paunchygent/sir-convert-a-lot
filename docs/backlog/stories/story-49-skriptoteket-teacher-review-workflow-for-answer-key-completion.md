---
id: story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion
title: Skriptoteket teacher review workflow for answer-key completion
type: story
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/protocols/llm/chat.py
  - /Users/olofs_mba/Documents/Repos/huleedu/services/llm_provider_service/README.md
labels:
  - skriptoteket
  - huleedu
  - teacher-review
  - conversion-hub
  - provider-decision
---

Implementation slice with acceptance-driven scope.

## Objective

Define the cross-product workflow that lets Skriptoteket teachers review,
accept, or override answer-key completion while Sir Convert remains the
conversion producer and HuleEdu remains an optional future provider/API owner.

## Scope

- Publish the Sir Convert contract details Skriptoteket needs for overlay
  creation: source IR manifest item summaries, source item fingerprints,
  overlay schema, completion modes, manual follow-up report, completion report,
  target readiness report, `digiexam_migration_bundle_v2`, and named artifacts.
- Keep Skriptoteket as a consumer/UI owner: it may collect teacher edits,
  submit overlays, show reports, and save final artifacts, but it must not infer
  answer keys outside the governed overlay/manual-key path.
- Define teacher-review states for source evidence, teacher overlay,
  LLM-suggested answer keys, manual follow-up, accepted-current-state
  decisions, and accepted/applied keys.
- Define that Skriptoteket submits review decisions and item edits back to Sir
  Convert through producer-owned correction contracts. It must not treat local
  UI acceptance as file readiness and must refresh target readiness from Sir
  Convert before enabling PDF/QTI download or save.
- Define that `Godkänn` triggers or resubmits a Sir Convert-owned
  `review_decision` flow; it does not locally unlock files until refreshed
  target readiness returns export-enabled rows.
- Use Sir Convert's unified `manual_matching_answer_key` correction entry for
  matching-capable source flows. Skriptoteket must not invent a local matching
  key shape, submit retired `left_id`/`right_id` aliases, or add matching to
  DigiExam overlays.
- Treat the Task 324 matching route as superseded and abandoned. It must not be
  proxied, consumed, or preserved as an adapter, shim, alias, wrapper, temporary
  bridge, or compatibility layer.
- ADR-0011 accepts the next Sir Convert producer direction as one
  source-neutral correction/apply contract, expected at
  `POST /v2/exam-authoring/corrections/apply`, with typed entries for item
  text/stem/prompt correction, point correction, manual choice keys, manual
  gap/open-cloze accepted values, manual matching keys, review decisions, and
  candidate suppression.
- Task 327 published the Sir Convert contract artifact in
  `docs/converters/exam-authoring-corrections-apply-contract.md`; Task 330 adds
  the initial runtime/OpenAPI implementation for `manual_matching_answer_key`.
- Skriptoteket must not build new teacher-correction surfaces around the
  abandoned adapter/route-per-item pattern. After the Sir Convert runtime hard
  cut and a governed consumer implementation slice, new consumer work should
  target the unified correction/apply contract.
- Keep HuleEdu as the authenticated edge proxy for that one contract and
  Skriptoteket as its teacher-correction consumer. Do not add more
  item-specific HuleEdu Gateway routes unless a future governed task proves
  why the unified contract cannot cover the case.
- Preserve public/authenticated access boundaries from the existing Exam
  Converter grant lane; remote LLM fallback for public jobs requires a future
  signed grant contract.
- Record the HuleEdu LLM Provider decision checkpoint: use Sir Convert's
  service-backed provider harness first, then evaluate a new HuleEdu generic
  structured-completion API only after the local-first contract exists.

## Acceptance Criteria

- [ ] Skriptoteket contract docs can be created from Sir Convert authority
  without duplicating parser/provider rules.
- [ ] The UI flow distinguishes source-bound answers, teacher/manual answers,
  LLM suggestions, applied reviewed answers, and unresolved manual follow-up.
- [ ] Teacher acceptance of a suggestion is represented as a manual overlay on
  a subsequent request, not retroactively as parser evidence.
- [ ] Teacher acceptance of the current missing-answer-key state is represented
  as an overlay review decision, not a local UI flag, and only Sir Convert
  target-readiness output can enable target artifacts.
- [ ] The UI consumes readiness classes such as `ready`,
  `ready_after_accepted_current_state`, `needs_teacher_answer_key`,
  `needs_teacher_review_decision`, `unsupported_target_shape`, and
  `target_validation_failed` without collapsing them into one generic blocked
  state.
- [ ] The durable teacher-correction API direction is source-neutral and
  producer-owned; the matching-specific transport is superseded and abandoned
  rather than treated as a route-per-item-type architecture, temporary bridge,
  or compatibility layer. PR-0332 waits for the Sir Convert runtime hard cut
  and its own governed implementation slice.
- [ ] Public Exam Converter jobs remain remote-provider-forbidden unless a
  signed public grant version explicitly opts in.
- [ ] HuleEdu LLM Provider reuse is treated as a future provider-surface task,
  not as a blocker for the first Sir Convert implementation.

## Test Requirements

- [ ] Skriptoteket adapter tests must prove overlay source binding is sent
  exactly as supplied by Sir Convert manifest data.
- [ ] Consumer tests must prove the UI cannot submit raw `.dxe`, result PDF
  text, student data, or raw artifacts inside overlay context.
- [ ] Cross-repo proof must include authenticated and public/grant routes where
  applicable, with explicit remote-provider policy evidence.
- [ ] If HuleEdu LLM Provider is extended later, conformance tests must prove it
  returns schema-specific structured JSON or typed failure without
  comparison-only result fields.

## Done Definition

This story is done when the Sir Convert-owned contract is sufficient for
Skriptoteket to build a teacher review workflow and for HuleEdu to make an
informed provider-API decision without duplicating conversion policy.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
