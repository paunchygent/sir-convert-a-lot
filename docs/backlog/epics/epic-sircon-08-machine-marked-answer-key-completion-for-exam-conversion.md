---
type: epic
id: EPIC-SIRCON-08
title: Machine-marked answer-key completion for exam conversion
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
links:
  decisions: []
outcome: Machine-marked answer-key completion for exam conversion
retired_ids:
- epic-11-machine-marked-answer-key-completion-for-exam-conversion
---

## Scope

## Epic Contract

## ADR Coverage

## Contract Inputs

## Stories

## Epic Verification Plan

## Exceptions And Follow-Ups

## Risks

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Epic Closeout Review

## Historical Source Content

Major capability increment managed through linked stories.

### Goal

Add policy-gated machine-marked answer-key completion to the DigiExam exam
migration lane without weakening source-bound parser semantics, privacy policy,
or Skriptoteket/Sir Convert ownership boundaries.

The capability starts from teacher-controlled overlays and local-first
structured LLM suggestions for missing machine-marked answer keys. It must keep
source IR distinct from effective renderer input and make every non-source
answer-key change visible through artifacts, reports, provenance, and manual
review gates.

### In Scope

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
- Hot service settings for provider routing so sanctioned CLI/API flows can
  switch new advisory requests between configured local and API providers
  without service restart or container recreation.
- Completion reports and manual-follow-up artifacts that let Skriptoteket show
  teachers exactly which items need review.
- A cross-repo handoff that lets Skriptoteket add the teacher review UI and
  lets HuleEdu decide whether its LLM Provider Service should expose a generic
  structured-completion API later.

### Out of Scope

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

### Stories

1. `docs/backlog/stories/st-sircon-08-02-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
   defines source-bound overlay, item fingerprint, effective IR, and contract
   report semantics.
1. `docs/backlog/stories/st-sircon-08-01-structured-llm-provider-harness-for-answer-key-completion.md`
   defines the reusable structured provider harness, provider capabilities,
   token budgeting, failover policy, and item-type output schemas.
1. `docs/backlog/stories/st-sircon-08-03-skriptoteket-teacher-review-workflow-for-answer-key-completion.md`
   defines the cross-product teacher review workflow and the HuleEdu provider
   decision checkpoint.
1. `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
   tracks Task 373, Skriptoteket PR-0406, and the final production browser
   proof with a tracked DXE fixture.
1. `docs/backlog/stories/st-sircon-08-04-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
   owns the follow-up replay/idempotency hardening after production showed that
   stale succeeded jobs can mask current compact review-state artifacts.

### Roadmap

Use
`docs/reference/ref-sircon-plan-machine-marked-answer-key-completion-implementation-roadmap-machine-marked-answer-key-completion-implementation-roadmap.md`
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
Task 323 is the producer-owned prerequisite before Skriptoteket matching
manual-key consumer work. It exposes the source-neutral
`ExamAuthoringMatchingManualAnswerKey` DTO through Sir Convert's generated
OpenAPI surface while keeping DigiExam ingestion overlays choice/gap-only and
forbidding consumer-local matching-pair inference.
Task 324 made the source-neutral matching DTO callable while matching lacked the
unified correction route; that route is now superseded and abandoned as a
product path. ADR-0011 is the accepted source-neutral correction/apply decision.
Task 327 defines one source-neutral correction/apply contract for item text,
point corrections, manual choice keys, manual gap/open-cloze accepted values,
manual matching keys, review decisions, and candidate suppression. Task 330
adds the unified runtime route, moves matching into `manual_matching_answer_key`,
and removes the Task 324 route rather than preserving it as a transitional route or
compatibility layer. Future HuleEdu/Skriptoteket work should build around that
unified contract instead of adding more item-specific Gateway routes.
Task 337 supersedes the review-decision portion of that contract: accepted
current state is an export policy concern, not authoring/correction state.
The unified correction contract must remove `review_decision` /
`accept_current_state_for_export`, keep missing keys blocked until real
authoring corrections supply them, and leave any future incomplete export mode
to a separate export-only contract.
Task 373 completed the compact review-state projection follow-up. Sir Convert
now derives a versioned item review-state report from producer-owned source,
effective, advisory, correction, and readiness state so Skriptoteket no longer
assembles review semantics from multiple producer artifacts and local UI state.
Story 57 is the cross-repo overseer tracking surface for Task 373 plus
Skriptoteket PR-0406. It is not a replacement for either task; it records the
shared final state goals and the required production browser proof gate.
Story 58 follows Story 57 without reopening it: it hardens Service API v2
idempotent succeeded replay, route artifact compatibility, and correction replay
artifact identity so compact review-state contracts cannot be bypassed by old
terminal jobs.
Task 328 is the separate proposed-decision audit slice. It keeps ADR-0002 and
ADR-0009 status cleanup out of ADR-0011 and preserves the rule that ADR-0009
requires its explicit Gateway acceptance path before acceptance.
ADR-0010 is the proposed decision for API provider expansion and hot-swappable
provider routing. It keeps local Qwen3.6 as the guarded default while requiring
future OpenAI/OpenRouter/DeepSeek provider work to route through service
settings for new requests without service restart or container recreation.
Task 325 is the OpenAI-first implementation slice under ADR-0010: direct Sir
Convert OpenAI Responses provider, hot running-service settings,
operator/internal-identity mutation, admission-time lineage, no public
`provider_route_class`, and no HuleEdu LLM Provider Service broker integration.
Task 326 is the linked eval gate: it runs the existing answer-key model
evaluation harness/corpus against `gpt-5.4-mini-2026-03-17` and
`gpt-5.4-nano-2026-03-17` and blocks Task 325 done-state plus OpenAI
production-default promotion until both snapshots are compared against the
current Qwen3.6 baseline.
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

### Acceptance Criteria

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
- [ ] Provider routing can be changed for new advisory requests through
  running service settings without restart or container recreation.
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

### Checklist

- [x] Stories linked
- [x] Acceptance criteria defined
- [x] Execution gate defined
