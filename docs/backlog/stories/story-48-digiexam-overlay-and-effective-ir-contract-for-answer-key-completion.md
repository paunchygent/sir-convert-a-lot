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
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-308-define-examnet-pdf-manual-unkeyed-accepted-current-state-profile-and-multigap-readiness.md
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
- Break the migration bundle contract to `digiexam_migration_bundle_v3` with no
  compatibility shim or source-only fallback lane after the Task 298 matching
  cutover.
- Add `DigiExamMigrationOptionsV2` fields for overlay filename/policy and
  answer-key completion options while preserving current defaults.
- Define `digiexam_ingestion_overlay_v2` with source file SHA256, source IR
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
  uses `digiexam_effective_exam_v2`, not the source IR schema.
- Emit `target_readiness_report_v1` from Sir Convert after overlay application,
  with consumer-ready states rather than a single coarse blocker class.
  Readiness must be per target and per item, distinguish missing answer keys
  from unsupported target shapes, and state whether the artifact can actually
  be created under the accepted-current-state policy.
- Keep source answer-key provenance strict; teacher overlay provenance belongs
  to the effective layer.
- Keep overlay input, overlay reports, effective IR, manifests, target
  readiness reports, product-visible outputs, and retained public artifacts
  free of forbidden raw/private payload classes: raw `.dxe`, raw PDF text,
  result-PDF content or student-result data, raw overlay JSON, raw model
  responses, full exam-level metadata that is not route-owned, identity
  markers, earned scores, wrong selections, free-text student answers,
  per-student performance history, and raw/base64 asset payloads.
- Implement item-content repair as a separate runtime slice after Task 295:
  `effective_item_patch` changes effective renderer input only and must not
  mutate source IR or answer-key provenance.
- Preserve Task 303's completed `unkeyed_manual_qti_2_1_v1` profile:
  teacher `accept_current_state_for_export` may enable QTI only when the
  selected QTI package is schema-valid, profile-valid, target-valid, free of
  unsupported resources, and marked with vendor-unproven Exam.net import proof
  until a live vendor test path exists. The profile preserves visible content
  without claiming automatic evaluation when trusted machine-marked keys are
  absent.
- Treat Exam.net PDF accepted-current-state as a separate governed target
  profile. Task 303 does not make PDF exportable. Until Task 308 defines and
  validates a PDF manual/unkeyed profile, Sir Convert must keep PDF disabled
  when accepted-current-state cannot preserve the visible item shape without
  trusted keys. Task 308 must support user-requested PDF rendering for
  missing-key single-choice, missing-key multiple-response, and item-013-style
  multi-gap gap/open-cloze items through native PDF-to-exam shapes when proven
  or degraded manual/free-text shapes when native import is unproven.
- Publish and snapshot the generated Sir Convert v2 OpenAPI contract so
  Skriptoteket can validate overlay/effective-IR/readiness integration before
  live Docker/service tests.
- Define matching pair and gapped/open-cloze accepted-value answer-key shapes
  as first-class intermediary/effective IR contracts before reviewed
  completion or target export may treat those shapes as automatically
  evaluated.

## Current State

Story 48 is proposed as the remaining roll-up for the answer-key completion
contract shape. Several child slices are already completed and must not be
reopened by default:

- Task 294 completed the prior hard bundle break, source fingerprints,
  overlay/report schemas, effective IR, and consumer break inventory. Task 298
  supersedes those public schema versions with the current
  `digiexam_migration_bundle_v3`, `digiexam_ingestion_overlay_v2`, and
  `digiexam_effective_exam_v2` cutover for matching answer-key pairs.
- Task 295 implemented source-bound teacher overlay ingestion, effective IR
  reporting, target readiness after manual keys/review decisions, and the
  overlay privacy/provenance guard rails.
- Task 302 implemented `effective_item_patch` for visible item-content repairs
  in effective IR while preserving source IR and source answer-key provenance.
- Task 303 completed the `unkeyed_manual_qti_2_1_v1` profile for accepted
  current-state exports with local package/profile validation and
  vendor-unproven Exam.net import status.
- Task 303 is QTI-only. Task 308 remains the owner for an Exam.net PDF
  manual/unkeyed accepted-current-state profile and for item-specific
  readiness/warning precision when PDF target limitations, such as multi-gap
  `Lucktext`, coexist with missing answer-key evidence. The Task 308 outcome
  must be content-preserving PDF output under explicit accepted-current-state
  for missing-key choice and item-013-style multi-gap items unless no native or
  degraded manual representation can preserve the visible item.
- Task 304 published the generated v2 OpenAPI snapshot for the DigiExam
  overlay, effective-IR, and target-readiness contract.

Completed answer-key-shape prerequisites:

- Task 298 defines exact ID-bound matching answer-key pairs before matching can
  be treated as automatically evaluated.
- Task 305 defines gap/open-cloze accepted values before gapped items can be
  treated as automatically evaluated.

Remaining blocker for Story 48 closeout:

1. Task 306 applies reviewed completion into effective IR only through the
   completed Task 298 and Task 305 first-class pair/value contracts and
   validators.
1. Task 308 defines the accepted-current-state Exam.net PDF profile, implements
   missing-key choice and item-013-style multi-gap rendering, and fixes
   readiness reporting so native multi-gap/gap-open-cloze target limitations
   are not masked by coarse missing-key warning precedence.

## Acceptance Criteria

- [ ] The service API contract names the new optional multipart part and
  rejects unknown parts, malformed JSON, oversized overlays, missing job-spec
  references, stale source bindings, raw/base64 asset payloads, raw `.dxe`,
  raw PDF text, result-PDF content or student-result data, raw overlay JSON,
  raw model responses, unowned full exam-level metadata, identity markers,
  earned scores, wrong selections, free-text student answers, and per-student
  performance history.
- [ ] Source item fingerprints are deterministic, exclude answer keys, and are
  available in source IR manifest item summaries.
- [ ] Overlay application fails closed on item ID, sequence, fingerprint, item
  type, or source file/IR mismatch.
- [ ] Manual answer keys from overlay are represented only as teacher/effective
  provenance and never as parser evidence.
- [ ] `effective_ir_json` is emitted only when effective renderer input differs
  from source IR and uses `digiexam_effective_exam_v2`.
- [ ] Teacher review decisions such as accepting missing answer keys are
  represented as overlay decisions, not local Skriptoteket flags, and target
  artifacts remain unavailable unless Sir Convert can create valid outputs
  under that policy.
- [x] Target readiness reports keep unsupported native item/target shapes, such
  as multi-gap gap-fill without proven native PDF-to-exam import behavior,
  distinct from ordinary missing `Facit`/answer-key review and from successful
  degraded manual PDF rendering.
- [x] Accepted-current-state can enable Exam.net PDF only after Task 308
  defines a governed PDF manual/unkeyed profile, creates target bytes, and
  validates the target. Missing-key choice and item-013-style multi-gap items
  must render when a native or degraded manual shape preserves visible content;
  otherwise PDF stays unavailable with item-specific readiness reasons.
- [ ] Existing default route behavior remains source-owned, but the bundle
  schema is `digiexam_migration_bundle_v3` for every terminal bundle.
- [x] Item-content repairs through `effective_item_patch` are runtime-applied
  only after Task 302 validates source-bound patch shapes and proves PDF/QTI
  renderers consume effective content.
- [x] Missing machine-marked keys keep QTI disabled unless Task 303 or a later
  governed QTI profile validates an unkeyed/manual representation for the
  selected QTI version.
- [x] Task 304 publishes generated v2 OpenAPI with typed DigiExam migration
  bundle, overlay, effective-IR, and target-readiness schemas for consumers.
- [x] Reviewed completion stays disabled for matching answer-key pairs until
  Task 298 provides exact pair fields, validation, provenance, manifest/report,
  and target-readiness semantics.
- [x] Reviewed completion stays disabled for gapped/open-cloze accepted values
  until Task 305 provides exact gap/value fields, validation, normalization,
  provenance, manifest/report, and target-readiness semantics.
- [ ] Task 306 applies reviewed completion only through the completed Task 298
  and Task 305 contracts; it must still reject or leave items in
  manual-follow-up state rather than infer matching or gapped/open-cloze answer
  keys from prompt text, renderer labels, or provider output.

## Test Requirements

- [ ] Contract tests cover valid overlay, missing job-spec reference, stale
  source hash, stale item fingerprint, wrong item type, oversized JSON, unknown
  fields, forbidden raw/base64 payloads, raw `.dxe`, raw PDF text,
  result-PDF content or student-result data, raw overlay JSON, raw model
  responses, unowned full exam-level metadata, identity markers, earned
  scores, wrong selections, free-text student answers, and per-student
  performance history.
- [ ] Manifest tests prove item fingerprints are stable and answer-key changes
  do not alter them.
- [ ] Builder tests prove source IR remains unchanged while effective IR and
  overlay report reflect applied teacher changes.
- [ ] Idempotency tests prove the same `.dxe` with different overlays becomes a
  different conversion request.
- [x] OpenAPI contract tests prove the committed snapshot matches runtime
  schema generation and includes consumer-required DigiExam components.
- [ ] QTI readiness tests prove Task 303's `unkeyed_manual_qti_2_1_v1` profile
  can enable accepted-current-state QTI only after package/profile validation,
  unsupported-resource checks, item-level manual/unkeyed follow-up reporting,
  and vendor-unproven Exam.net import status are preserved.
- [ ] Answer-key completion tests prove Task 306 can apply matching pairs or
  gap accepted values only through the completed Task 298 and Task 305
  first-class IR/effective-IR contracts and validators.
- [x] PDF readiness tests prove Task 308 renders missing-key choice and
  item-013-style multi-gap accepted-current-state PDF output without answer-key
  claims, and reports native multi-gap target limitations distinctly from
  missing answer-key review when degraded rendering is used.

## Done Definition

This story is done when Sir Convert can safely accept, validate, persist, and
report Skriptoteket teacher overlays while preserving source-bound DigiExam IR
semantics and making effective renderer input explicit.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
