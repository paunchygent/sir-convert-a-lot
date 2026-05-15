---
id: task-295-implement-teacher-overlay-application-and-effective-ir-reporting
title: Implement teacher overlay application and effective IR reporting
type: task
status: completed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
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

This task is the first runtime implementation slice after Task 294 and the hard
`digiexam_migration_bundle_v2` break. It must implement the overlay/effective
IR path without adding a v1 shim, a source-only fallback lane, or local
Skriptoteket readiness semantics.

## PR Scope

- Add overlay multipart persistence beside the upload and reject unreferenced or
  unexpected parts.
- Add typed overlay DTOs and validation for source binding, item fingerprint,
  item type compatibility, bounded patch payloads, manual answer-key shapes,
  and review-decision shapes.
- Add typed review-decision DTOs for accepting current missing machine-marked
  answer-key state without inventing answer data.
- Add a dedicated overlay application service that returns source exam,
  effective exam, accepted review decisions, and ingestion overlay report
  without mutating parser output.
- Add source item fingerprint generation to the IR manifest path.
- Wire the bundle builder to render from effective exam when overlay policy
  applies, while still writing source IR.
- Emit `effective_ir_json` and `ingestion_overlay_report` named artifacts only
  when relevant.
- Emit target-readiness data that is computed after overlay/review-decision
  application and before named artifacts are marked downloadable.

## Implementation Roadmap

### 1. Create request-surface overlay plumbing

- Add `digiexam_ingestion_overlay_filename` and explicit overlay policy fields
  to `DigiExamMigrationOptionsV2` in
  `scripts/sir_convert_a_lot/domain/specs_v2.py`.
- Add the optional `digiexam_ingestion_overlay` multipart part to
  `interfaces/http_routes_jobs_v2.py`,
  `interfaces/http_create_job_routes_v2.py`, and
  `interfaces/http_digiexam_migration_request_v2.py`.
- Reject overlay uploads unless the job spec references the exact filename.
- Reject unknown parts and generic companion uploads as today.
- Include the overlay digest in the create-job idempotency fingerprint in
  `infrastructure/runtime_config_v2.py`.
- Persist overlay bytes beside the uploaded `.dxe` using a focused companion
  path helper, not ad hoc bundle-builder file discovery.

Checkpoint:

- no-overlay requests still produce the Task 294 v2 bundle shape;
- same `.dxe` + different overlay JSON conflicts/rekeys under idempotency;
- overlay filename mismatch fails before job creation.

### 2. Move source fingerprints into the source IR/manifest contract

- Promote the current source item fingerprint logic from target-readiness
  support into the IR/domain layer so `digiexam_ir_manifest_v2.item_summaries`
  carry `source_item_fingerprint`.
- Keep the fingerprint answer-key independent: answer-key provenance,
  correct alternative IDs, result-PDF enrichment, manual overlays, LLM
  suggestions, and review decisions must not affect the digest.
- Add unit tests that mutate only answer-key data and prove the fingerprint is
  unchanged, then mutate prompt/options/gaps/matching/assets and prove it
  changes.

Checkpoint:

- every manifest item summary has `item_id`, `sequence`, `item_type`, and
  `source_item_fingerprint`;
- target-readiness rows reuse the same fingerprint helper.

### 3. Add strict overlay DTOs and validation

- Add a bounded domain module for `digiexam_ingestion_overlay_v1` DTOs and
  validators. Keep this separate from parser DTOs and renderer DTOs.
- Validate top-level source binding:
  `source_filename`, source file SHA-256, source IR schema version, source IR
  SHA-256, overlay schema version, and overlay entry IDs.
- Validate item binding per entry: `item_id`, `sequence`, `item_type`, and
  `source_item_fingerprint`.
- Accept only governed entry kinds for this task:
  manual answer keys and review decisions. Bounded item patches may be parsed
  and reported as unsupported unless this task implements every affected
  renderer path.
- Forbid raw `.dxe`, raw PDF text, student data, raw/base64 assets, arbitrary
  prompt/context fields, and unknown properties in overlay JSON.

Checkpoint:

- stale source file digest, stale source IR digest, stale item fingerprint,
  wrong sequence, wrong item type, duplicate entry ID, oversized JSON, and
  unknown fields all fail closed before rendering.

### 4. Build effective exam application service

- Add `digiexam_effective_exam_v1` DTOs in a dedicated domain module.
- Add an overlay application service that receives source IR plus a validated
  overlay and returns:
  source exam, effective exam, applied decisions, rejected entries, and
  ingestion overlay report data.
- Manual answer keys apply only to effective answer-key fields with
  teacher/effective provenance. Parser-owned IR and parser provenance remain
  unchanged.
- `accept_current_state` review decisions apply only as reviewed policy input.
  They do not create answer keys and do not satisfy parser provenance.
- The first accepted-current-state target policy is conservative:
  Sir Convert may enable a target only after the renderer/import path can
  create and validate bytes under a governed no-answer-key policy. If PDF can
  create a valid teacher-reviewed unkeyed/manual representation, PDF may become
  exportable. QTI stays unavailable for missing machine-marked keys unless the
  QTI package profile has an explicit validated unkeyed/manual representation.

Checkpoint:

- source IR artifact bytes remain unchanged by overlay;
- effective IR appears only when renderer input differs from source IR;
- accepted-current-state decisions are visible as decisions, not answer keys.

### 5. Recompute target readiness from effective inputs

- Update `domain/digiexam_target_readiness.py` so readiness receives source IR,
  effective exam state, ingestion overlay report state, and target artifact
  outcomes.
- Distinguish at least:
  `ready`, `ready_after_accepted_current_state`,
  `needs_teacher_answer_key`, `needs_teacher_review_decision`,
  `unsupported_target_shape`, `target_validation_failed`, `not_requested`, and
  `not_implemented`.
- Keep unsupported target shape and validation failure separate from missing
  answer-key review. Teacher acceptance must not hide QTI validation failures
  or renderer unsupported-shape failures.

Checkpoint:

- readiness report is generated after overlay/effective application and after
  target creation/validation attempts;
- Skriptoteket can enable exports only from `export_enabled=true` readiness
  rows, not from bundle status or artifact availability alone.

### 6. Wire bundle artifacts and named downloads

- Update `infrastructure/digiexam_migration_bundle_builder.py` to render from
  effective exam when overlay application changes renderer input.
- Keep writing `ir_json` as parser-owned source IR.
- Emit:
  - `effective_ir_json` as available only when effective input differs;
  - `ingestion_overlay_report` as available only when overlay is submitted;
  - `target_readiness_report` for every terminal v2 bundle.
- Keep `effective_ir_json`, `ingestion_overlay_report`, and
  `answer_key_completion_report` as `not_requested` when no overlay/completion
  path ran.
- Preserve named artifact error behavior for unavailable or failed targets.

Checkpoint:

- bundle manifest source binding includes source IR digest and effective exam
  digest;
- no-overlay bundles remain v2 and do not fabricate effective/overlay reports.

### 7. Close with consumer-facing tests and docs

- Extend `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
  for valid overlay, stale overlay, manual answer key, accepted-current-state,
  no-overlay baseline, named report downloads, and idempotency digest behavior.
- Add focused domain tests for overlay validation, fingerprint stability, and
  effective exam application.
- Update the service API contract only where runtime details discovered during
  implementation require tightening. Do not add fields not backed by this
  implementation.
- Update `.codex/handoff.md` only with volatile next-step/validation evidence.

Checkpoint:

- Task 295 can hand Task 298/305 the overlay/effective IR substrate for
  answer-key contract-shape work, and later hand Task 297/306 the same
  substrate for advisory reports and reviewed application without mixing in LLM
  completion here.

## Out Of Scope

- LLM provider harness extraction, local vLLM/llama.cpp invocation, model
  benchmarking, prompts, and answer-key suggestions; those belong to Tasks 296,
  297, 300, and 301.
- Applying matching or gapped/open-cloze answer-key completion before exact
  matching pair fields and gap accepted-value fields exist; Tasks 298 and 305
  own those contract gates.
- Skriptoteket UI implementation. Task 295 must produce the Sir Convert
  contract/runtime surface that Skriptoteket consumes.
- HuleEdu provider/API changes.
- Any `digiexam_migration_bundle_v1` compatibility mode, compatibility shim, or
  source-only fallback route.

## Stop Conditions

- Stop if implementing accepted-current-state would require inventing answer
  keys, mutating parser provenance, or marking an unvalidated target as
  exportable.
- Stop if overlay JSON needs raw `.dxe`, raw PDF text, student data, or
  base64/raw asset payloads to satisfy the requested behavior.
- Stop if a target renderer/importer cannot create and validate bytes under the
  requested effective state; report readiness instead of synthesizing output.
- Stop before changing public grant semantics, remote-provider policy, or
  Skriptoteket local persistence contracts.
- Stop before widening matching or gapped/open-cloze completion beyond
  advisory/manual-review unless the exact matching answer-pair and gap
  accepted-value IR fields are implemented.

## Runtime Entry Points

- `scripts/sir_convert_a_lot/domain/specs_v2.py`
- `scripts/sir_convert_a_lot/domain/digiexam_ir_contracts.py`
- `scripts/sir_convert_a_lot/domain/digiexam_target_readiness.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_jobs_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_routes_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_digiexam_migration_request_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_config_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_job_companion_paths_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_manifest.py`
- `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay.py`
- `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay_contracts.py`
- `scripts/sir_convert_a_lot/domain/digiexam_source_fingerprints.py`
- `tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`

## Deliverables

- [x] Overlay DTOs and validator.
- [x] Review-decision DTOs and validator.
- [x] Source item fingerprint helper with unit tests.
- [x] Overlay application service with fail-closed decisions.
- [x] Target-readiness service/report with per-target and per-item readiness
  reasons.
- [x] Bundle builder integration.
- [x] Named artifact and manifest updates.
- [x] Idempotency and multipart request validation updates.
- [x] No-overlay v2 baseline regression tests.

## Acceptance Criteria

- [x] Overlay validation cannot read raw files, caller-supplied raw asset
  payloads, result PDF content, or student data from overlay JSON.
- [x] Parser output remains source-bound and unaffected by overlay.
- [x] Manual overlay keys can satisfy manual follow-up in the effective output.
- [x] Accepted-current-state decisions can clear the teacher-review gate only
  for blockers Sir Convert can safely render/import under that policy; they do
  not create answer keys or satisfy parser provenance.
- [x] Target readiness keeps unsupported target shapes and QTI validation
  failures disabled even after teacher acceptance.
- [x] Stale overlays fail before rendering.
- [x] No-overlay requests still emit v2 bundles and target readiness without
  applying overlay behavior.
- [x] Overlay digest participates in idempotency.
- [x] `effective_ir_json` and `ingestion_overlay_report` are unavailable as
  `not_requested` unless the corresponding overlay/effective path ran.
- [x] Product-visible outputs do not expose raw overlay JSON, raw model
  responses, raw `.dxe`, raw PDF text, result-PDF student data, or raw/base64
  assets.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
- focused domain tests added for overlay/fingerprint/effective exam modules
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
