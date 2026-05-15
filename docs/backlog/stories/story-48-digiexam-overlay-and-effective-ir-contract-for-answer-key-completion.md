---
id: story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion
title: DigiExam overlay and effective IR contract for answer-key completion
type: story
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-examnet-qti-import-contract-and-validation-strategy.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
labels:
  - digiexam
  - overlay
  - effective-ir
  - answer-key-completion
  - skriptoteket
---

Implementation slice with acceptance-driven scope.

## Objective

Define and implement the source-bound ingestion overlay and effective IR
contract that lets Skriptoteket provide bounded item patches, manual answer
keys, and review decisions without mutating the parser-owned source IR.

## Scope

- Add contract authority for optional multipart
  `digiexam_ingestion_overlay`.
- Break the migration bundle contract to `digiexam_migration_bundle_v2` with no
  v1 compatibility shim or source-only fallback lane.
- Add `DigiExamMigrationOptionsV2` fields for overlay filename/policy and
  answer-key completion options while preserving current defaults.
- Define `digiexam_ingestion_overlay_v1` with source file SHA256, source IR
  SHA256/schema version, item IDs, sequence numbers, source item fingerprints,
  bounded effective item patches, manual answer keys, and review decisions.
- Define teacher review decisions in the overlay contract, including
  accepting the current source/effective state for export without adding an
  answer key. Review decisions must be source-bound by item fingerprint and
  must not be reclassified as parser evidence.
- Add stable source item fingerprints to source IR manifest item summaries.
- Persist overlay bytes beside uploads and include overlay digest in
  idempotency.
- Emit `ingestion_overlay_report` when an overlay is submitted and
  `effective_ir_json` when overlay changes renderer input. `effective_ir_json`
  uses `digiexam_effective_exam_v1`, not the source IR schema.
- Emit `target_readiness_report_v1` from Sir Convert after overlay application,
  with consumer-ready states rather than a single coarse blocker class.
  Readiness must be per target and per item, distinguish missing answer keys
  from unsupported target shapes, and state whether the artifact can actually
  be created under the accepted-current-state policy.
- Keep source answer-key provenance strict; teacher overlay provenance belongs
  to the effective layer.
- Implement item-content repair as a separate runtime slice after Task 295:
  `effective_item_patch` changes effective renderer input only and must not
  mutate source IR or answer-key provenance.
- Define a later governed unkeyed/manual QTI profile so teacher
  `accept_current_state_for_export` can enable QTI only when the selected QTI
  2.1 or QTI 3.0 package is schema-valid and target-valid under that profile.
- Publish and snapshot the generated Sir Convert v2 OpenAPI contract so
  Skriptoteket can validate overlay/effective-IR/readiness integration before
  live Docker/service tests.

## Acceptance Criteria

- [ ] The service API contract names the new optional multipart part and
  rejects unknown parts, malformed JSON, oversized overlays, missing job-spec
  references, stale source bindings, and raw/base64 asset payloads.
- [ ] Source item fingerprints are deterministic, exclude answer keys, and are
  available in source IR manifest item summaries.
- [ ] Overlay application fails closed on item ID, sequence, fingerprint, item
  type, or source file/IR mismatch.
- [ ] Manual answer keys from overlay are represented only as teacher/effective
  provenance and never as parser evidence.
- [ ] `effective_ir_json` is emitted only when effective renderer input differs
  from source IR and uses `digiexam_effective_exam_v1`.
- [ ] Teacher review decisions such as accepting missing answer keys are
  represented as overlay decisions, not local Skriptoteket flags, and target
  artifacts remain unavailable unless Sir Convert can create valid outputs
  under that policy.
- [ ] Target readiness reports keep unsupported item/target shapes, such as
  multi-gap gap-fill without a governed renderer/import shape, distinct from
  ordinary missing `Facit`/answer-key review.
- [ ] Existing default route behavior remains source-owned, but the bundle
  schema is `digiexam_migration_bundle_v2` for every terminal bundle.
- [x] Item-content repairs through `effective_item_patch` are runtime-applied
  only after Task 302 validates source-bound patch shapes and proves PDF/QTI
  renderers consume effective content.
- [ ] Missing machine-marked keys keep QTI disabled unless Task 303 or a later
  governed QTI profile validates an unkeyed/manual representation for the
  selected QTI version.
- [x] Task 304 publishes generated v2 OpenAPI with typed DigiExam migration
  bundle, overlay, effective-IR, and target-readiness schemas for consumers.

## Test Requirements

- [ ] Contract tests cover valid overlay, missing job-spec reference, stale
  source hash, stale item fingerprint, wrong item type, oversized JSON, unknown
  fields, and forbidden raw/base64 payloads.
- [ ] Manifest tests prove item fingerprints are stable and answer-key changes
  do not alter them.
- [ ] Builder tests prove source IR remains unchanged while effective IR and
  overlay report reflect applied teacher changes.
- [ ] Idempotency tests prove the same `.dxe` with different overlays becomes a
  different conversion request.
- [x] OpenAPI contract tests prove the committed snapshot matches runtime
  schema generation and includes consumer-required DigiExam components.

## Done Definition

This story is done when Sir Convert can safely accept, validate, persist, and
report Skriptoteket teacher overlays while preserving source-bound DigiExam IR
semantics and making effective renderer input explicit.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
