---
id: 'task-336-implement-correction-replay-artifact-references-for-skriptoteket-pr-0339'
title: 'Implement correction replay artifact references for Skriptoteket PR-0339'
type: 'task'
status: 'done'
priority: 'critical'
created: '2026-05-19'
last_updated: '2026-05-19'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-and-teacher-review.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-333-implement-non-matching-unified-correction-apply-runtime-for-digiexam-pr-0332.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/backlog/prs/pr-0339-st-21-04-sir-convert-replay-artifact-reference-contract.md
labels:
  - exam-authoring
  - corrections
  - artifact-authority
  - skriptoteket
---
## Implement Correction Replay Artifact References For Skriptoteket PR-0339

## Objective

Implement the Sir Convert-owned replay artifact reference contract approved in
Skriptoteket `PR-0339`.

When `POST /v2/exam-authoring/corrections/apply` receives a producer-issued
DigiExam correction source-state bundle and successfully renders corrected
target bytes, Sir Convert must return replay-scoped artifact keys on
export-enabled target readiness rows. Skriptoteket must consume those keys; it
must not guess corrected artifact locations or fall back to original target
artifacts.

## PR Scope

- Add an optional replay artifact reference field to
  `ExamAuthoringCorrectionTargetReadinessRowV1`.
- Render corrected DigiExam replay artifacts from the original job source plus
  the submitted source-bound correction batch.
- Persist replay artifacts as job-owned Sir Convert artifacts under distinct
  replay artifact keys, not as aliases for `examnet_pdf` or `qti_package`.
- Serve those replay artifacts through the existing owner-scoped
  `/v2/convert/jobs/{job_id}/artifacts/{artifact_key}` route.
- Keep the retired matching-specific route absent; do not add shims, aliases,
  wrappers, or compatibility paths.
- Update the correction apply contract, generated OpenAPI snapshot, and focused
  tests.

## Deliverables

- [x] Export-enabled correction target readiness rows include a replay artifact
      key only after corrected target bytes are written.
- [x] Non-exportable targets expose no downloadable replay artifact key.
- [x] Replay artifact keys are distinct from original artifact keys.
- [x] Owner-scoped artifact downloads return the corrected PDF/QTI bytes for
      replay artifact keys.
- [x] Focused route tests prove artifact key emission and artifact download.

## Acceptance Criteria

- [x] Given a DigiExam source-state issue/apply flow corrects a missing choice
      key, when both PDF and QTI targets are requested, then correction apply
      returns `artifact_key` on the export-enabled target readiness rows.
- [x] Given the returned replay artifact keys, when the caller downloads named
      artifacts from the source job, then the returned bytes are the corrected
      replay artifacts.
- [x] Given a target cannot be rendered, when correction apply returns target
      readiness, then that target has no replay artifact key and artifact
      availability is unavailable.
- [x] Given legacy matching-specific paths are probed, then no retired route,
      alias, shim, wrapper, or compatibility layer is exposed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Closeout

- Correction apply now writes replay-derived corrected PDF/QTI artifacts under
  distinct `correction_replay_*` artifact keys and returns those keys on
  export-enabled correction target readiness rows.
- Replay artifact downloads use the existing owner-scoped artifact route; no
  matching route, alias, shim, wrapper, or original-artifact fallback was added.
- The local development container was rebuilt/recreated with `/app/scripts`
  mounted and Uvicorn reload watching that mount, then the user confirmed the
  v13 DigiExam live flow produced enabled corrected downloads.

## Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
- `pdm run typecheck`
- Targeted Ruff formatting/checks for the changed correction apply/runtime
  files passed. Full `pdm run lint` remains blocked by unrelated pre-existing
  formatting drift in `tests/sir_convert_a_lot/test_local_compose_contract.py`.
