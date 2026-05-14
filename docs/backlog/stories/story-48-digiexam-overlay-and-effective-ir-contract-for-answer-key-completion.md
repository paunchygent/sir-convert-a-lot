---
id: 'story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion'
title: 'DigiExam overlay and effective IR contract for answer-key completion'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
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
contract that lets Skriptoteket provide teacher context, bounded item patches,
and manual answer keys without mutating the parser-owned source IR.

## Scope

- Add contract authority for optional multipart
  `digiexam_ingestion_overlay`.
- Add `DigiExamMigrationOptionsV2` fields for overlay filename/policy and
  answer-key completion options while preserving current defaults.
- Define `digiexam_ingestion_overlay_v1` with source file SHA256, source IR
  SHA256/schema version, item IDs, sequence numbers, source item fingerprints,
  teacher context, bounded effective item patches, and manual answer keys.
- Define teacher review decisions in the overlay contract, including
  accepting the current source/effective state for export without adding an
  answer key. Review decisions must be source-bound by item fingerprint and
  must not be reclassified as parser evidence.
- Add stable source item fingerprints to source IR manifest item summaries.
- Persist overlay bytes beside uploads and include overlay digest in
  idempotency.
- Emit `overlay_report` and `effective_ir_json` when overlay changes renderer
  input.
- Emit target-readiness semantics from Sir Convert after overlay application.
  Readiness must be per target and per item, distinguish missing answer keys
  from unsupported target shapes, and state whether the artifact can actually
  be created under the accepted-current-state policy.
- Keep source answer-key provenance strict; teacher overlay provenance belongs
  to the effective layer.

## Acceptance Criteria

- [ ] The service API contract names the new optional multipart part and
  rejects unknown parts, malformed JSON, oversized overlays, missing job-spec
  references, stale source bindings, and raw/base64 asset payloads.
- [ ] Source item fingerprints are deterministic, exclude answer keys, and are
  available in source IR manifest item summaries.
- [ ] Overlay application fails closed on item ID, sequence, fingerprint, item
  type, or source file/IR mismatch.
- [ ] Teacher context can enrich candidate construction without becoming answer
  evidence.
- [ ] Manual answer keys from overlay are represented only as teacher/effective
  provenance and never as parser evidence.
- [ ] `effective_ir_json` is emitted only when effective renderer input differs
  from source IR.
- [ ] Teacher review decisions such as accepting missing answer keys are
  represented as overlay decisions, not local Skriptoteket flags, and target
  artifacts remain unavailable unless Sir Convert can create valid outputs
  under that policy.
- [ ] Target readiness reports keep unsupported item/target shapes, such as
  multi-gap gap-fill without a governed renderer/import shape, distinct from
  ordinary missing `Facit`/answer-key review.
- [ ] Existing default route behavior remains `source_evidence_only` with no
  overlay application unless requested.

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

## Done Definition

This story is done when Sir Convert can safely accept, validate, persist, and
report Skriptoteket teacher overlays while preserving source-bound DigiExam IR
semantics and making effective renderer input explicit.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
