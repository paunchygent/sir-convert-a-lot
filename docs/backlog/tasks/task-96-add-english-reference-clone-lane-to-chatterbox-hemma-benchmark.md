---
id: task-96-add-english-reference-clone-lane-to-chatterbox-hemma-benchmark
title: Add English reference-clone lane to Chatterbox Hemma benchmark
type: task
status: in_progress
priority: high
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/backlog/tasks/task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
labels:
  - chatterbox
  - english
  - benchmark
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Allow the canonical Task 86 Hemma Chatterbox benchmark surface to run an
English reference-clone lane as a first-class benchmark path, without
mislabelling the main clone output as Swedish in the evidence.

## PR Scope

- Add a probe-language control to the committed Task 86 benchmark CLI.
- Make the main clone artifact naming and report fields language-neutral.
- Keep the existing Swedish default behavior intact.
- Preserve the optional English-reference-to-Swedish cross-language lane.
- Add local tests for the new English main-clone path.

## Deliverables

- [ ] Task 86 benchmark supports `--probe-language en`.
- [ ] Task 86 report and markdown no longer hardcode the main clone lane as
  Swedish.
- [ ] One English reference-clone run can be executed through the canonical
  Hemma wrapper path.

## Acceptance Criteria

- [ ] A main English clone run can be executed without ad hoc scripts.
- [ ] Report JSON clearly records the probe language.
- [ ] Existing Swedish benchmark behavior remains the default path.
- [ ] Local tests cover the new probe-language option and reporting shape.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
