---
id: task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff
title: Publish cross-repo Skriptoteket and HuleEdu answer-key completion handoff
type: task
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py
  - /Users/olofs_mba/Documents/Repos/huleedu/services/llm_provider_service/README.md
labels:
  - cross-repo
  - skriptoteket
  - huleedu
  - handoff
  - provider-decision
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish the downstream integration handoff that lets Skriptoteket and HuleEdu
create their own governed docs/tasks from the Sir Convert answer-key completion
contract.

## PR Scope

- Write a Sir Convert-owned integration reference or handoff section that names
  exactly what Skriptoteket may send and consume.
- Identify the Skriptoteket docs/backlog surfaces that should receive the
  teacher-review UI and adapter work.
- Identify the HuleEdu decision/task needed only if LLM Provider Service should
  add a generic structured-completion API.
- Preserve the recommendation that Sir Convert implements the first
  service-backed local-first provider harness rather than blocking on HuleEdu.
- Keep public Exam Converter grant behavior and remote-provider consent
  requirements explicit.

## Deliverables

- [ ] Skriptoteket handoff prompt with required reads, scope, out-of-scope,
  adapter/UI contract, proof gates, and stop conditions.
- [ ] HuleEdu handoff prompt or task seed for generic structured-completion API
  evaluation.
- [ ] Cross-repo dependency map linked from Sir Convert docs.
- [ ] Updated `.codex/handoff.md` active pointer.

## Acceptance Criteria

- [ ] Skriptoteket is instructed to consume Sir Convert manifest and overlay
  contract data, not duplicate parser or provider inference.
- [ ] HuleEdu provider reuse is framed as optional/future and requires a new API
  shape, not reuse of comparison-only callback results.
- [ ] Public/grant and authenticated routes keep separate consent and remote
  fallback semantics.
- [ ] The handoff contains exact validation expectations for each repo.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
