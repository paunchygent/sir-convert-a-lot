---
id: task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts
title: Define DigiExam ingestion overlay fingerprints and effective IR artifacts
type: task
status: completed
priority: high
created: '2026-05-14'
last_updated: '2026-05-15'
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
  with `digiexam_migration_bundle_v2`, the optional overlay multipart part,
  job-spec options, default behavior, idempotency inputs, named artifacts,
  reports, and access policy.
- Amend `docs/converters/digiexam-intermediate-exam-representation-contract.md`
  with source item fingerprints, matching answer-pair requirements, and the
  source IR versus `digiexam_effective_exam_v1` split.
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
- Define `target_readiness_report_v1` and bundle-manifest semantics that give
  Skriptoteket direct consumer states for:
  - target available under source/effective evidence;
  - target available only under accepted-current-state policy;
  - target awaiting a teacher answer key or review decision;
  - target unavailable because the shape is unsupported; and
  - target unavailable because validation failed, such as QTI package validation.
- State that target readiness is Sir Convert-owned. Skriptoteket must submit
  teacher edits and review decisions as an ingestion overlay, then refresh Sir
  Convert's target-readiness output before enabling PDF, QTI, or save actions.
- Define `effective_ir_json` as `digiexam_effective_exam_v1`; it must not reuse
  the parser-owned source IR schema.
- Make exact matching answer-pair fields and gapped/open-cloze accepted-value
  fields critical dependencies before applied completion can be enabled for
  those item shapes.

## Deliverables

- [x] Updated service API/artifact contract.
- [x] Updated IR/manifest contract.
- [x] Contract examples for source binding, source-derived item context,
  choice/gap-fill/matching item patches, and manual answer keys.
- [x] Contract examples for accepted-current-state review decisions and
  target-readiness outcomes for PDF and QTI.
- [x] Skriptoteket consumer checklist showing the fields it may store locally,
  the fields it must echo unchanged in overlays, and the fields it must refresh
  from Sir Convert before enabling export actions.
- [x] Stop conditions for stale overlays, raw data leakage, and matching IR
  gaps.

## Acceptance Criteria

- [x] `digiexam_migration_bundle_v2` is a hard bundle contract break with no
  v1 compatibility shim or source-only fallback lane.
- [x] Overlay presence changes idempotency through overlay digest.
- [x] Source item fingerprints exclude answer keys and are stable across
  answer-key-only changes.
- [x] Contract text states that source-derived item context is parser/input
  context, not answer-key evidence.
- [x] Contract text states that accepting the current state is not an answer
  key, does not satisfy parser provenance, and only enables target artifacts
  that Sir Convert can render/import validly under the accepted-state policy.
- [x] Contract text states that `Godkänn` / accept-current-state is a
  `review_decision`, not an answer key, and cannot be treated by Skriptoteket as
  local PDF/QTI readiness.
- [x] Contract text states that Skriptoteket must use Sir Convert manifest
  source-binding fields when submitting overlays and must use refreshed Sir
  Convert target-readiness results before exposing PDF/QTI export actions.
- [x] Multi-gap gap-fill/lucktext and other unsupported target shapes stay
  target-readiness blockers until a governed target shape exists, even if the
  teacher accepts missing answer keys.
- [x] Product-visible outputs do not expose raw prompt, raw model response, raw
  `.dxe`, result PDF content, or student data.

## Breaking Consumer Inventory

Task 294 deliberately breaks `digiexam_migration_bundle_v1`; the next runtime
and consumer slices must update these known consumers instead of adding shims:

- Sir Convert:
  - `scripts/sir_convert_a_lot/application/contracts_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_migration_bundle_contracts.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_manifest.py`
  - `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py`
  - `tests/sir_convert_a_lot/test_public_exam_converter_grant_runtime_v2.py`
- Skriptoteket:
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/conversion_hub_saved_artifacts.py`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/public_exam_converter.py`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/public_exam_converter_artifacts.py`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/application/curated_apps/handlers/public_exam_converter_jobs.py`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/src/skriptoteket/web/api/v1/public_apps.py`
- HuleEdu:
  - `/Users/olofs_mba/Documents/Repos/huleedu/services/api_gateway_service/app/public_exam_converter_grant_contract.py`
  - `/Users/olofs_mba/Documents/Repos/huleedu/services/api_gateway_service/tests/test_public_exam_converter_grant_routes.py`
  - `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
