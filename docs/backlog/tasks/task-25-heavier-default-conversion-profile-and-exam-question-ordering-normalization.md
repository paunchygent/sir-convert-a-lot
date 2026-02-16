---
id: task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization
title: Heavier default conversion profile and exam-question ordering normalization
type: task
status: in_progress
priority: high
created: '2026-02-16'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-21-structural-markdown-quality-gate-and-hard-case-normalization.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - docling
  - conversion-quality
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden default conversion quality toward a heavier Docling profile and fix
question/alternative ordering defects observed for:
`.agents/input/Prövning i litteraturhistoria 2024.pdf`.

## PR Scope

- Upgrade default Docling layout model selection to a heavier profile for better
  reading-order fidelity.
- Keep canonical CLI defaults aligned with quality-first conversion behavior.
- Add targeted post-normalization correction for exam-style question blocks if
  ordering remains inverted (alternatives before question).
- Validate locally and on Hemma lanes after push/pull/rebuild/restart.

Out of scope:

- non-conversion product features,
- persistence/retention changes (Task 23),
- general runbook expansion beyond required evidence updates.

## Decision Lock

1. Heavier-default policy:
   - Prefer heavier Docling layout model by default.
   - Keep override capability explicit and deterministic through config/env.
1. Conversion correctness target:
   - For the target exam PDF, question heading should precede alternatives.
   - Numbering progression must remain monotonic and non-duplicated.
1. Validation path:
   - Must include Hemma deployment cycle:
     - commit + push,
     - remote pull,
     - container rebuild/restart,
     - lane verification and target-document conversion evidence.

## Deliverables

- [ ] Heavier default Docling configuration in service code.
- [ ] Regression tests for heavier-default config and exam-order normalization.
- [ ] Hemma lane execution evidence including target PDF output review.

## Acceptance Criteria

- [ ] Default conversion path uses heavier Docling layout profile by contract.
- [ ] Target PDF conversion output keeps question lines before alternatives.
- [ ] Target PDF conversion output has consistent question numbering order.
- [ ] Full quality/docs gates pass after implementation.
- [ ] Hemma deploy/rebuild/lane verification pass on pushed revision.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
