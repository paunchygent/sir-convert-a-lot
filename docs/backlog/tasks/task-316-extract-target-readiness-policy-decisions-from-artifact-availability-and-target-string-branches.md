---
id: task-316-extract-target-readiness-policy-decisions-from-artifact-availability-and-target-string-branches
title: Extract target readiness policy decisions from artifact availability and target string branches
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
  - scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py
  - scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py
labels:
  - solid
  - ddd
  - exam-converter
  - target-readiness
  - target-policy
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extract target-readiness business policy from artifact availability and
target-name branch ladders into typed readiness decisions owned by the target
profile.

The current path correctly reports consumer-ready rows, but the policy that
decides artifact availability, teacher action, unsupported target shapes, and
retryability is concentrated in one function family. That makes every new target
or unresolved item profile a change to the same branch ladder.

Historical accepted-current-state readiness classes and reason codes are not a
target policy to preserve. Task 337 owns their removal from authoring/correction
state and target-readiness unlocks. If Task 316 lands before Task 337, it may
isolate that current behavior only to make deletion safer; it must not promote
accepted-current-state into the durable target-readiness policy model.

## PR Scope

- Introduce a target-readiness policy/protocol that converts artifact state and
  item context into `DigiExamTargetReadinessRow` values.
- Replace raw `unavailable_code` string checks with a typed reason surface or a
  method on artifact entries before readiness rows are built.
- Move unsupported gap/open-cloze and other target-profile decisions into the
  target profile. Keep accepted-current-state reason codes out of the durable
  model unless a future export-only request contract explicitly reintroduces
  incomplete export.
- Keep named artifact availability, manifest schema, target labels, localized
  message keys, and Skriptoteket-facing row fields compatible.
- Do not add new renderer support or relax unsupported-target-shape failures.

## Deliverables

- [ ] Typed readiness decision or policy contract.
- [ ] Target-specific readiness profile for the current Exam.net PDF and QTI
  package targets.
- [ ] Artifact unavailable reasons exposed without raw string matching in the
  readiness builder.
- [ ] Focused tests for available, not requested, not implemented, failed,
  provider unavailable, missing answer key, and unsupported target shape rows.
  If legacy accepted-current-state rows still exist when this task starts, add
  temporary characterization coverage only to support Task 337 removal.

## Acceptance Criteria

- [ ] Adding a new target does not require adding target-name branches to
  `_rows_for_target` or `_accepted_current_state_reason_code`.
- [ ] Item-level readiness rows still carry target, item binding, reason code,
  `export_enabled`, `teacher_action`, retryability, and message key.
- [ ] Accepted-current-state rows are not part of the durable readiness policy.
  Existing rows, if still present at task start, are isolated as legacy behavior
  and removed by Task 337 rather than normalized into the new policy surface.
- [ ] Unsupported multi-gap/open-cloze behavior stays fail-closed unless a
  governed target profile explicitly supports it.
- [ ] Existing API/artifact contracts and generated OpenAPI schemas remain
  additive-compatible.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
