---
type: story
id: ST-SIRCON-08-01
title: Structured LLM provider harness for answer-key completion
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
epic: EPIC-SIRCON-08
links:
  decisions: []
acceptance_criteria:
  - Provider code is generic structured output, not edit-op-specific.
  - Chat Completions and Responses payload builders keep their schema shapes separate.
  - Local llama.cpp support is capability-configured and does not infer GBNF or JSON Schema support from host/port.
  - The completion prompt is single-turn and item-local with no full exam, result PDF, raw `.dxe`, student data, owner metadata, or artifact paths.
  - Over-budget items are not sent to a provider and produce `manual_follow_up_required` with backend failure code `over_budget`.
  - Provider failure, invalid JSON, schema mismatch, unknown IDs, duplicate IDs, or invalid answer payloads become manual follow-up with backend-owned failure codes.
  - Remote fallback is attempted only when authenticated/signed policy allows it and the request explicitly opts in.
  - Provider routing tests cover running-service settings changes that affect new requests while preserving already-admitted job lineage.
  - Hot provider settings tests prove mutation is operator/internal-identity gated, invalid or stale settings fail closed, public/grant callers cannot mutate routing, and advisory lineage records the resolved provider profile plus settings version.
retired_ids:
  - story-47-structured-llm-provider-harness-for-answer-key-completion
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Create a generic structured-output provider harness for item-local answer-key
completion while reusing the shape of Skriptoteket's local-first provider set,
budgeting, Dishka wiring, and remote fallback policy where appropriate.

### Scope

- Introduce `StructuredChatProviderProtocol`, `StructuredOutputSpec`,
  `StructuredLLMResponse`, and `StructuredChatProviderSet` separate from
  editor edit-ops.
- Support configured endpoint kinds for Chat Completions, Responses, and local
  llama.cpp-compatible chat completions.
- Keep provider capabilities explicit: JSON Schema, GBNF, remote/local, context
  window, output-token budget, parser profile, and health.
- Define item-type-specific output schemas for choice, gap-fill, and matching,
  consuming Task 298 and Task 305 contract shapes for matching pairs and
  gapped/open-cloze accepted values rather than inventing provider-only
  structures.
- Reuse Skriptoteket's budgeting idea: context window minus max output tokens
  minus safety margin, with conservative fallback for unknown/local tokenizers.
- Implement route policy where remote provider fallback is forbidden by default
  and explicit false is terminal.
- Implement provider routing so the active provider profile for new advisory
  requests can be changed through running service settings, not only through
  startup environment variables or container recreation.
- Keep production capture metadata-only unless a separate governed evaluation
  mode is added.

### Current Implementation State

Task 296 is completed. Sir Convert now has the reusable structured provider
core: source-neutral contracts, provider profiles/capabilities, local-first
routing policy, token-budget preflight, metadata-only capture, payload builders
for Chat Completions, Responses, llama.cpp JSON Schema/GBNF, and vLLM
structured choice, async HTTP provider execution, response
parsing/failure-mapping, service settings loading, and opt-in Dishka
composition.

Task 297 is completed. The DigiExam migration bundle route now supports the
opt-in `local_llm_suggest_missing_machine_marked` completion mode for advisory
choice and gap-fill answer-key candidates. The default `source_evidence_only`
route still makes no structured LLM calls and keeps
`answer_key_completion_report` as `not_requested`. Advisory mode writes a
candidate-lineage `answer-key-completion-report.json` artifact only when
requested, validates backend output strictly, and leaves source IR, effective
IR, Exam.net PDF, and QTI unchanged.

Task 312 is the provider-protocol correction required before Task 309 live
validation. It keeps answer-key orchestration provider-neutral by injecting a
candidate planner. The Granite/vLLM planner selects bounded
`structured_outputs.choice` for choice and multiple-response rows, while using
vLLM JSON Schema for gap-fill rows. Generic providers keep the JSON
Schema-backed planner.

Task 309 is the proposed live-validation checkpoint for the completed harness
and advisory path. It validates the interim Granite FP8/vLLM provider on Hemma
against a versioned pure DigiExam DXE corpus before the deferred Task 300
comparative model bake-off. MCQ/MCW live requests should prefer vLLM `choice`
values when candidate selection is clear and bounded; JSON Schema remains part
of provider microprobes and gap-fill object validation. Task 310 and Task 311
then separate validation-only force-eval from the strict service-backed
auth/public-edge mirror.

Task 318 is the follow-up for eval evidence alignment after the Qwen3.6
llama.cpp validation exposed that `evaluate-advisory-corpus` still reconstructed
Granite metadata from defaults. Provider-run metadata must be profile-driven
from the selected provider/default object so model changes inject runtime,
sampling, output-mode, capability, and vision media-path settings without
model-name branches in the evaluator.

ADR-0010 is the accepted provider-routing decision for the next API-provider
slice. Review 20 is approved. It selects direct Sir Convert API providers first,
starting with OpenAI, and requires hot service settings so CLI/API traffic can
route new advisory requests between configured local and API providers without
service restart or container recreation. Production local-provider routing formerly depended on Task 320 (Docker DNS and HuleEdu-signed service-report proof, retained as historical evidence only). Superseded for the Sir exam lane: the Task 320 Qwen provider route is removed with the sidecar under TASK-SIRCON-REP-0030 / TASK-SKRIPT-39-03-04 and must not be required; the exam-lane default is TASK-SIRCON-08-01-07 remote profiles. Authenticated/public-edge mirror readiness remains gated by Task 311 only insofar as that mirror is still pursued under Skript ownership. Generic provider-harness mechanics, generic qwen/ tooling, CJ resources, and the active GPU hold are unchanged.
ADR-0010 keeps provider route selection operator-internal unless a later
contract task adds a public `provider_route_class` field with OpenAPI and
consumer-impact proof.

Task 325 is the OpenAI-first implementation slice. It must add the direct
OpenAI Responses provider and hot running-service routing while preserving
operator/internal-identity mutation authority, atomic settings versions,
admission-time lineage, no public provider route field, and fail-closed
public/grant remote-provider policy. Its initial OpenAI model manifest is pinned
to `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`. Task 326 owns the
separate eval-harness proof and blocks Task 325 done-state plus any OpenAI
production-default promotion until both snapshots are compared against the
retained historical Qwen3.6 baseline (evidence only; not a current Sir production routing requirement under TASK-SIRCON-REP-0030 / TASK-SKRIPT-39-03-04 and TASK-SIRCON-08-01-07).

### Acceptance Criteria

- [x] Provider code is generic structured output, not edit-op-specific.
- [x] Chat Completions and Responses payload builders keep their schema shapes
  separate.
- [x] Local llama.cpp support is capability-configured and does not infer GBNF
  or JSON Schema support from host/port.
- [x] The completion prompt is single-turn and item-local with no full exam,
  result PDF, raw `.dxe`, student data, owner metadata, or artifact paths.
- [x] Over-budget items are not sent to a provider and produce
  `manual_follow_up_required` with backend failure code `over_budget`.
- [x] Provider failure, invalid JSON, schema mismatch, unknown IDs, duplicate
  IDs, or invalid answer payloads become manual follow-up with backend-owned
  failure codes.
- [x] Remote fallback is attempted only when authenticated/signed policy allows
  it and the request explicitly opts in.
- [ ] Provider routing tests cover running-service settings changes that affect
  new requests while preserving already-admitted job lineage.
- [ ] Hot provider settings tests prove mutation is operator/internal-identity
  gated, invalid or stale settings fail closed, public/grant callers cannot
  mutate routing, and advisory lineage records the resolved provider profile
  plus settings version.

### Test Requirements

- [x] Unit tests cover Chat Completions, Responses, and llama.cpp payload
  construction for the same output spec.
- [ ] Budget tests cover OpenAI-family, Mistral/Devstral-family, and unknown
  tokenizer resolver paths.
- [x] Routing tests cover local primary success, local unavailable with local
  fallback, remote fallback forbidden, explicit false, missing consent, and
  allowed signed consent.
- [x] Capture tests prove raw prompts/responses and item text are not persisted
  in normal production mode.

### Done Definition

This story is done when Sir Convert has a reusable structured provider harness
that can serve answer-key completion without binding provider mechanics to the
DigiExam parser, renderers, or artifact routes.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
