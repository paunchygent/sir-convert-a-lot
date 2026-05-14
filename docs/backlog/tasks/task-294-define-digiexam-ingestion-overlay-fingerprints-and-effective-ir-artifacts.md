---
id: 'task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts'
title: 'Define DigiExam ingestion overlay fingerprints and effective IR artifacts'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-05-14'
last_updated: '2026-05-14'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
labels:
  - digiexam
  - overlay
  - effective-ir
  - contract
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Define the public route, IR, manifest, review-decision, target-readiness, and
report contract for `digiexam_ingestion_overlay`, source item fingerprints, and
effective IR before runtime implementation, with Skriptoteket consumer needs
treated as first-class contract inputs rather than later UI-local state.

## PR Scope

- Amend `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  with the optional overlay multipart part, job-spec options, default behavior,
  idempotency inputs, named artifacts, reports, and access policy.
- Amend `docs/converters/digiexam-intermediate-exam-representation-contract.md`
  with source item fingerprints and the source IR versus effective IR split.
- Define `digiexam_ingestion_overlay_v1`, `overlay_report_v1`, and
  `answer_key_completion_report_v1` at contract level.
- Make the overlay/effective-IR shape directly consumable by Skriptoteket's
  teacher review workflow: manifest item summaries must carry the stable source
  binding fields needed to resubmit edits, accepted suggestions, manual answer
  keys, and accepted-current-state decisions without copying parser/provider
  policy into Skriptoteket.
- Define teacher review-decision payloads for accepting current missing
  machine-marked answer keys without adding answer data. These decisions must
  be source-bound by item ID, sequence, source item fingerprint, and item type,
  and must not mutate source IR or parser provenance.
- Define `target_readiness_report_v1` and bundle-manifest semantics that let
  Skriptoteket distinguish:
  - target available under source/effective evidence;
  - target available only under accepted-current-state policy;
  - target blocked by missing answer key that has not been accepted;
  - target blocked by unsupported target shape; and
  - target blocked by validation failure such as QTI package validation.
- State that target readiness is Sir Convert-owned. Skriptoteket must submit
  teacher edits and review decisions as an ingestion overlay, then refresh Sir
  Convert's target-readiness output before enabling PDF, QTI, or save actions.
- Decide whether `effective_ir_json` can reuse the current IR schema in the
  first slice or needs a version bump before applied completion.
- Keep matching application explicitly blocked until matching answer pairs are
  represented in IR.

## Deliverables

- [ ] Updated service API/artifact contract.
- [ ] Updated IR/manifest contract.
- [ ] Contract examples for source binding, teacher context, choice/gap-fill/
  matching item patches, and manual answer keys.
- [ ] Contract examples for accepted-current-state review decisions and
  target-readiness outcomes for PDF and QTI.
- [ ] Skriptoteket consumer checklist showing the fields it may store locally,
  the fields it must echo unchanged in overlays, and the fields it must refresh
  from Sir Convert before enabling export actions.
- [ ] Stop conditions for stale overlays, raw data leakage, and matching IR
  gaps.

## Acceptance Criteria

- [ ] Default `source_evidence_only` request/response examples remain
  backwards compatible.
- [ ] Overlay presence changes idempotency through overlay digest.
- [ ] Source item fingerprints exclude answer keys and are stable across
  answer-key-only changes.
- [ ] Contract text states that teacher context is not answer-key evidence.
- [ ] Contract text states that accepting the current state is not an answer
  key, does not satisfy parser provenance, and only enables target artifacts
  that Sir Convert can render/import validly under the accepted-state policy.
- [ ] Contract text states that `Godkänn` / accept-current-state is a
  `review_decision`, not an answer key, and cannot be treated by Skriptoteket as
  local PDF/QTI readiness.
- [ ] Contract text states that Skriptoteket must use Sir Convert manifest
  source-binding fields when submitting overlays and must use refreshed Sir
  Convert target-readiness results before exposing PDF/QTI export actions.
- [ ] Multi-gap gap-fill/lucktext and other unsupported target shapes stay
  target-readiness blockers until a governed target shape exists, even if the
  teacher accepts missing answer keys.
- [ ] Product-visible outputs do not expose raw prompt, raw model response, raw
  `.dxe`, result PDF content, or student data.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
