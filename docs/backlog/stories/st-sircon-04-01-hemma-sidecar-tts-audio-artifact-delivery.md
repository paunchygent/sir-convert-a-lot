---
type: story
id: ST-SIRCON-04-01
title: Hemma sidecar TTS audio artifact delivery
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-04
links:
  decisions: []
acceptance_criteria:
- ADR-0006 is accepted and explicitly forbids in-process TTS in the main service image.
- Hemma benchmark scope is concrete enough to prove sidecar viability on the live
  R9700 host.
- Chatterbox is the explicit current Hemma production-candidate sidecar for the English-first
  TTS delivery track while other TTS containers remain experiment-only.
- md to wav is the first documented implementation route and includes request/response
  contract, output content type, TTS options shape, fail-closed acceleration behavior,
  and phase-1 language and voice limits.
- Story links make clear that Story 07's old auxiliary-converter framing is not canonical
  for TTS delivery.
retired_ids:
- story-22-hemma-sidecar-tts-audio-artifact-delivery
---

## Context

State the actor or consumer need and the parent epic outcome this story serves.

## Epic Contract Slice

Define one independently reviewable observable behavior or capability slice.

## ADR Coverage

No new governing direction is introduced by this contract.

Applicable ADR IDs must equal the unique IDs in `links.decisions`; this section
records semantic coverage only and does not enforce readiness.

## Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this story.

## Live Verification Plan

- Story checkpoint and applicable acceptance criteria.
- Real route and expected observable result.
- Task evidence consumed and retained story-level verification evidence.

## Non-Goals

- Adjacent behavior or implementation work this story must not absorb.

## Notes

Record current story-local interpretation that does not belong in the contract,
ledger, or non-goals.

## Decision And Assumption Ledger

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

## Story Closeout Review

Record verification result, evidence, permitted next step, unavailable mandatory
evidence, and residual risk. The `closeout_review` frontmatter mapping is the
machine authority for gate status and approval evidence.

## Historical Source Content

Implementation slice with acceptance-driven scope.

## Objective

Lock the next Sir Convert-a-Lot audio feature around a Hemma sidecar TTS architecture and publish
the first implementation slice as a provider-neutral `md -> wav` v2 job contract.

## Scope

- Sidecar-only architecture:
  - the main Sir Convert-a-Lot service remains free of TTS model/runtime dependencies,
  - TTS is served through an internal Docker-network sidecar on Hemma,
  - no public direct sidecar exposure.
- Contract-first sequence:
  - publish ADR and route policy before implementation,
  - benchmark compatibility on the real Hemma R9700/gfx1201 host,
  - publish `md -> wav` request/response semantics before code changes.
- Product boundary for phase 1:
  - English-first,
  - preset voices only,
  - `wav` contract first,
  - `pdf -> wav` deferred to a follow-up composition slice after `md -> wav` is stable.
- Governance:
  - fail-closed GPU behavior for TTS routes,
  - Python runtime policy of "newest supported upstream version" with Python `3.12` as the
    current proven floor until Task 79 verifies a newer target,
  - provider-neutral public contract (no Qwen-specific task taxonomy in v2).

## Tasks (Ordered)

1. `docs/backlog/tasks/task-78-adr-for-hemma-sidecar-tts-architecture-and-route-policy.md`
1. `docs/backlog/tasks/task-80-publish-md-to-wav-v2-contract-for-sidecar-backed-tts.md`
1. `docs/backlog/tasks/task-79-benchmark-hemma-tts-sidecar-compatibility-and-audio-formats-on-r9700.md`
1. `docs/backlog/tasks/task-92-promote-chatterbox-sidecar-to-hemma-production-candidate-and-mark-experimental-sidecars-explicitly.md`

## Acceptance Criteria

- [x] ADR-0006 is accepted and explicitly forbids in-process TTS in the main service image.
- [ ] Hemma benchmark scope is concrete enough to prove sidecar viability on the live R9700 host.
- [x] Chatterbox is the explicit current Hemma production-candidate sidecar for the
  English-first TTS delivery track, while the other TTS containers remain experiment-only.
- [x] `md -> wav` is the first documented implementation route and includes:
  - request/response contract,
  - output content type,
  - TTS options shape,
  - fail-closed acceleration policy behavior,
  - phase-1 language/voice limits.
- [x] Story links make it clear that Story 07's old auxiliary-converter framing is not the
  canonical architecture for TTS delivery anymore.

## Test Requirements

- [x] Docs validations pass for epic/story/task/ADR/reference additions.
- [ ] The benchmark task defines deterministic Hemma evidence artifacts and command surfaces.
- [ ] The contract task defines required API contract tests for create-job validation, result
  payloads, and artifact content type before implementation starts.

## Done Definition

The team can start implementation without reopening the architecture choice, route ordering, or
public contract shape for phase-1 TTS delivery on Hemma.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [x] Docs synchronized
