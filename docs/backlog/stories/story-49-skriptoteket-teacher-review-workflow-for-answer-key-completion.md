---
id: 'story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion'
title: 'Skriptoteket teacher review workflow for answer-key completion'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md
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
  and named artifacts.
- Keep Skriptoteket as a consumer/UI owner: it may collect teacher context,
  submit overlays, show reports, and save final artifacts, but it must not infer
  answer keys outside the governed overlay/manual-key path.
- Define teacher-review states for source evidence, teacher overlay,
  LLM-suggested answer keys, manual follow-up, accepted-current-state
  decisions, and accepted/applied keys.
- Define that Skriptoteket submits review decisions and item edits back to Sir
  Convert through the overlay contract. It must not treat local UI acceptance
  as file readiness and must refresh target readiness from Sir Convert before
  enabling PDF/QTI download or save.
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
