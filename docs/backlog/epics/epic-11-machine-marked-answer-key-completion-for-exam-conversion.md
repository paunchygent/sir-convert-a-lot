---
id: epic-11-machine-marked-answer-key-completion-for-exam-conversion
title: Machine-marked answer-key completion for exam conversion
type: epic
status: proposed
priority: high
created: '2026-05-14'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-293-capture-machine-marked-answer-key-completion-architecture-and-tranche-plan.md
  - docs/backlog/tasks/task-294-define-digiexam-ingestion-overlay-fingerprints-and-effective-ir-artifacts.md
  - docs/backlog/tasks/task-295-implement-teacher-overlay-application-and-effective-ir-reporting.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-305-define-gapped-open-cloze-accepted-value-ir-contract.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/backlog/tasks/task-321-purge-reviewed-answer-key-export-fallbacks-for-pr-0331.md
  - docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md
  - docs/backlog/tasks/task-299-publish-cross-repo-skriptoteket-and-huleedu-answer-key-completion-handoff.md
  - docs/backlog/tasks/task-309-live-validate-granite-answer-key-completion-on-versioned-digiexam-dxe-corpus.md
  - docs/backlog/tasks/task-310-add-validation-only-force-eval-mode-for-source-keyed-answer-key-live-validation.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-300-benchmark-local-llama-cpp-model-shortlist-for-answer-key-completion.md
  - docs/backlog/tasks/task-301-smoke-test-granite-4-1-8b-fp8-on-rocm-vllm-preview.md
  - docs/backlog/tasks/task-302-implement-teacher-item-content-overlay-application-for-effective-ir.md
  - docs/backlog/tasks/task-303-define-unkeyed-manual-qti-profile-for-accepted-current-state-exports.md
  - docs/backlog/tasks/task-304-publish-generated-sir-convert-v2-openapi-contract-for-digiexam-migration-bundles.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-local-llama-answer-key-completion-model-shortlist-and-benchmark-plan.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/digiexam-intermediate-exam-representation-contract.md
labels:
  - exam-migration
  - digiexam
  - examnet
  - answer-key-completion
  - llm
  - skriptoteket
---

Major capability increment managed through linked stories.

## Goal

Add policy-gated machine-marked answer-key completion to the DigiExam exam
migration lane without weakening source-bound parser semantics, privacy policy,
or Skriptoteket/Sir Convert ownership boundaries.

The capability starts from teacher-controlled overlays and local-first
structured LLM suggestions for missing machine-marked answer keys. It must keep
source IR distinct from effective renderer input and make every non-source
answer-key change visible through artifacts, reports, provenance, and manual
review gates.

## In Scope

- Optional `digiexam_ingestion_overlay` multipart input for the existing
  `digiexam_dxe -> examnet_migration_bundle` route.
- Source item fingerprints and overlay source binding so Skriptoteket can
  round-trip teacher edits, manual answer keys, and review decisions safely.
- A hard `digiexam_migration_bundle_v2` break with no v1 compatibility shim,
  so consumers migrate to target readiness and effective-exam semantics.
- A distinct `effective_ir_json` artifact when teacher overlay or applied
  completion changes renderer input, using `digiexam_effective_exam_v1`.
- Runtime application of teacher item-content repair only through source-bound
  `effective_item_patch` in the effective layer.
- Teacher/manual answer-key overlay semantics that remain authoritative only in
  the effective layer.
- Local-first structured LLM answer-key completion for missing machine-marked
  answer keys in single choice, multiple choice, multiple response, gap-fill,
  and eventually matching items.
- Explicit remote provider policy where remote fallback is forbidden by default
  and explicit false is terminal.
- Completion reports and manual-follow-up artifacts that let Skriptoteket show
  teachers exactly which items need review.
- A cross-repo handoff that lets Skriptoteket add the teacher review UI and
  lets HuleEdu decide whether its LLM Provider Service should expose a generic
  structured-completion API later.

## Out of Scope

- Reclassifying LLM output as DigiExam parser evidence.
- Reconstructing free-text rubrics, scoring policies, marking matrices, or
  open-ended answer keys.
- Sending full exams, result PDF text, raw `.dxe` files, owner metadata, student
  data, or artifact paths to LLM providers.
- Enabling remote provider fallback for anonymous/public jobs before a signed
  public grant version explicitly authorizes it.
- Moving parser, renderer, artifact-route, and provider responsibilities into a
  shared procedural module.
- Implementing Skriptoteket UI or HuleEdu LLM Provider API changes inside Sir
  Convert tasks.

## Stories

1. `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
   defines source-bound overlay, item fingerprint, effective IR, and contract
   report semantics.
1. `docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md`
   defines the reusable structured provider harness, provider capabilities,
   token budgeting, failover policy, and item-type output schemas.
1. `docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md`
   defines the cross-product teacher review workflow and the HuleEdu provider
   decision checkpoint.

## Roadmap

Use
`docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md`
as the tranche sequence and checkpoint ledger for this epic. It orders the work
from contract foundation through overlay runtime, provider harness, local model
benchmarking, advisory reports, reviewed application, and cross-repo handoff.
Task 298 matching pair and Task 305 gapped/open-cloze accepted-value contracts
are completed preconditions before reviewed application may write those
answer-key shapes into effective IR.
Task 321 owns the PR-0331 cleanup that prevents reviewed/accepted keys from
being dropped by target-specific QTI/PDF fallbacks after they have been applied
to effective renderer input.
Task 322 is the small Sir Convert producer-owned prerequisite immediately
before Skriptoteket PR-0332. It adds the source-bound points/scoring correction
DTO and proof surface needed before Skriptoteket can expose point-editing in the
full teacher correction workflow.
Task 301 is an experimental Hemma runtime smoke checkpoint for Granite 4.1 8B
FP8 on the ROCm vLLM preview image; it can inform provider viability, but it
does not replace Task 300's `llama.cpp` GGUF benchmark matrix or authorize
production model selection.
Task 309 is the Granite/vLLM production-path live-validation checkpoint over
the versioned pure DigiExam DXE corpus. It precedes any model bake-off and uses
teacher-verified goldens, strict wrong-but-valid reporting, and no raw
prompt/response retention. Task 310 owns validation-only force-eval over
source-keyed items as a follow-up gate, and Task 311 owns the strict
service-backed auth/public-edge mirror validation. Task 300's comparative
model benchmark remains deferred until the full app path is working and
deployed.

## Acceptance Criteria

- [x] The offline implementation shape is captured as a governed Sir Convert
  reference and backlog spine.
- [ ] The route contract can accept a bounded, source-bound ingestion overlay
  without changing default `source_evidence_only` behavior.
- [ ] The source IR and effective IR are separate artifacts with explicit
  semantics in manifests and named artifact routes.
- [x] Teacher item-content patches can repair effective renderer input without
  mutating source IR, parser provenance, or answer-key evidence.
- [x] Generated OpenAPI publishes the v2 DigiExam overlay/effective-IR/readiness
  schemas needed by consumer type-generation and live-test preflight.
- [ ] Teacher/manual overlay can remove manual follow-up only when source
  binding and type compatibility are proven.
- [x] Structured LLM completion is local-first, item-local, schema-specific,
  non-explanatory, and metadata-only in normal capture.
- [x] Remote fallback cannot occur unless policy and signed authenticated/public
  consent explicitly allow it.
- [x] Advisory completion can be produced without changing renderer input.
- [ ] Applied completion requires effective provenance, review/report artifacts,
  and tests proving source provenance remains strict.
- [ ] Reviewed/accepted keys that reach effective renderer input are preserved
  in QTI/PDF artifacts; target proof gaps may be reported but must not remove
  accepted key values.
- [x] Matching answer application waits for Task 298's exact pair contract,
  and gapped/open-cloze application waits for Task 305's accepted-value
  contract.
- [x] Accepted-current-state can enable QTI only under a governed
  unkeyed/manual QTI profile with schema/profile validation and target
  readiness proof.
- [ ] Skriptoteket and HuleEdu follow-up tasks are explicitly separated from
  Sir Convert runtime tasks.

## Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
