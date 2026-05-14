---
id: 'task-293-capture-machine-marked-answer-key-completion-architecture-and-tranche-plan'
title: 'Capture machine-marked answer-key completion architecture and tranche plan'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - inputs/implementation-of-llm-enrichment-of-mcq-items.md
labels:
  - docs-governance
  - planning
  - answer-key-completion
  - llm
  - cross-repo
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Translate the offline answer-key completion architecture into Sir Convert
docs-as-code authority before implementation begins.

## PR Scope

- Read `inputs/implementation-of-llm-enrichment-of-mcq-items.md` as the strong
  decision shape.
- Reframe the feature as machine-marked answer-key completion rather than MCQ
  enrichment.
- Create the Sir Convert epic/story/task spine and reference architecture.
- Check current Skriptoteket LLM provider and HuleEdu LLM Provider shapes enough
  to make the first provider recommendation.
- Verify current third-party structured-output syntax for OpenAI and llama.cpp
  before writing provider-contract guidance.
- Update active Sir Convert docs pointers and generated indexes.

## Deliverables

- [x] `EPIC-11` for machine-marked answer-key completion.
- [x] Overlay/effective IR story.
- [x] Structured provider harness story.
- [x] Skriptoteket/HuleEdu cross-product workflow story.
- [x] PR-sized follow-up tasks for contract, runtime, provider, advisory,
  applied, and cross-repo slices.
- [x] Reference architecture with explicit HuleEdu provider assessment.

## Acceptance Criteria

- [x] Source-bound parser provenance remains immutable.
- [x] Default route behavior remains `source_evidence_only`.
- [x] Remote provider fallback remains forbidden unless a later signed policy
  explicitly permits it.
- [x] Skriptoteket is documented as a consumer/UI overlay owner, not the answer
  inference authority.
- [x] HuleEdu LLM Provider reuse is represented as a later decision checkpoint,
  not a first-slice dependency.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Verification

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
