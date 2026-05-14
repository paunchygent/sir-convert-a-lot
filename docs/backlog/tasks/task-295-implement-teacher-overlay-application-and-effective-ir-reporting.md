---
id: 'task-295-implement-teacher-overlay-application-and-effective-ir-reporting'
title: 'Implement teacher overlay application and effective IR reporting'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
labels:
  - digiexam
  - overlay
  - runtime
  - effective-ir
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement validated teacher overlay ingestion, review-decision application,
effective IR/report artifact generation, and target-readiness reporting for the
DigiExam migration bundle route.

## PR Scope

- Add overlay multipart persistence beside the upload and reject unreferenced or
  unexpected parts.
- Add typed overlay DTOs and validation for source binding, item fingerprint,
  item type compatibility, bounded context strings, bounded patch payloads, and
  manual answer-key shapes.
- Add typed review-decision DTOs for accepting current missing machine-marked
  answer-key state without inventing answer data.
- Add a dedicated overlay application service that returns source exam,
  effective exam, accepted review decisions, and overlay report without
  mutating parser output.
- Add source item fingerprint generation to the IR manifest path.
- Wire the bundle builder to render from effective exam when overlay policy
  applies, while still writing source IR.
- Emit `effective_ir_json` and `overlay_report` named artifacts only when
  relevant.
- Emit target-readiness data that is computed after overlay/review-decision
  application and before named artifacts are marked downloadable.

## Deliverables

- [ ] Overlay DTOs and validator.
- [ ] Review-decision DTOs and validator.
- [ ] Source item fingerprint helper with unit tests.
- [ ] Overlay application service with fail-closed decisions.
- [ ] Target-readiness service/report with per-target and per-item blocker
  reasons.
- [ ] Bundle builder integration.
- [ ] Named artifact and manifest updates.

## Acceptance Criteria

- [ ] Overlay validation cannot read raw files, base64 assets, result PDF
  content, or student data from overlay JSON.
- [ ] Parser output remains source-bound and unaffected by overlay.
- [ ] Manual overlay keys can satisfy manual follow-up in the effective output.
- [ ] Accepted-current-state decisions can clear the teacher-review gate only
  for blockers Sir Convert can safely render/import under that policy; they do
  not create answer keys or satisfy parser provenance.
- [ ] Target readiness keeps unsupported target shapes and QTI validation
  failures disabled even after teacher acceptance.
- [ ] Stale overlays fail before rendering.
- [ ] Existing route tests pass unchanged for requests without overlays.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
