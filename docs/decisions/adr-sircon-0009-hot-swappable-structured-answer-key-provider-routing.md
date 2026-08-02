---
type: adr
id: ADR-SIRCON-0009
title: Hot-swappable Structured Answer-key Provider Routing
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: accepted
links:
  governing: []
deciders:
- platform
retired_ids:
- ADR-0010
---

## Context

## Decision

## Non-Decisions

## Consequences

## Historical Source Content

### Purpose

Define the provider-routing decision for machine-marked answer-key completion
before adding API-based LLM providers to the existing local Qwen3.6 advisory
path.

The decision preserves the product intent: Sir Convert may use local or API LLM
providers to suggest missing machine-marked answer keys, but suggestions remain
advisory, backend-validated, source-bound, and teacher-reviewed before they can
change effective renderer input.

### Status

- Accepted
- Date: 2026-05-18
- Acceptance evidence: Review 20 approved the ADR constraints on 2026-05-18.

### 1. Problem and Context

Sir Convert currently supports local structured answer-key completion through
the Epic 11 provider harness and the guarded Qwen3.6 MTP runtime. Task 319
proved the host-local Qwen3.6 path. Task 320 is the productionization gate for
the same local provider when the running service must reach it through Docker
DNS instead of container-local loopback. As of 2026-05-18, Task 320 is done and
contains fresh Hemma proof that `sir_convert_a_lot_prod` reaches
`sir_convert_qwen_answer_key` through Docker DNS, receives constrained JSON
output, and produces advisory report suggestions through a HuleEdu-signed
service request. Task 311 remains the separate gate for strict authenticated and
public-edge mirror validation.

The local path works well enough for advisory completion, but it is still
operationally heavy: GPU availability, local container health, service-network
reachability, and model quality gates affect whether teachers receive
suggestions.

The product needs an API-provider lane as well, starting with OpenAI, then
adding OpenRouter and DeepSeek behind the same Sir-owned provider contract. The
API lane must not fork the answer-key domain model or duplicate parser,
renderer, overlay, or review semantics.

The system also needs operational switching. Operators must be able to route
new advisory requests between configured local and API providers through
running service settings, without restarting or recreating the service
container. Production local routing is acceptable only when the Task 320
service-backed Docker DNS provider path is green; authenticated/public-edge
claims remain blocked until Task 311 is green. This is required for live
fallback, cost/quality tests, provider outage response, and operator-controlled
validation runs.

HuleEdu's LLM Provider Service remains useful prior art, but its current
public shape is queue-first and comparison-specific: callers enqueue
comparative-judgement work and receive callback results. That is not the first
implementation target for Sir's item-local, schema-specific answer-key
completion requests.

### 2. Decision

Sir Convert will add API-based providers directly behind the existing
structured-provider harness before considering HuleEdu LLM Provider Service as
a broker.

The first API provider is OpenAI. OpenRouter and DeepSeek are planned follow-on
providers, but they must declare their concrete structured-output capability
instead of being treated as interchangeable with OpenAI.

Provider selection for new answer-key advisory requests must be controlled by
hot service settings. Runtime provider routing must not be limited to
environment variables that require process restart, service recreation, or a
new Docker deployment.

### 3. Provider Boundary

Sir Convert owns one source-neutral structured provider protocol and one
answer-key completion orchestration path.

Provider implementations must plug in below that boundary:

- `local_qwen36_mtp`, backed by the current local llama.cpp runtime;
- `openai_responses`, backed by OpenAI's Responses API structured output;
- `openrouter_chat`, backed by OpenRouter's OpenAI-compatible chat completion
  API for models that advertise structured outputs;
- `deepseek_json_object`, backed by DeepSeek JSON Output and stricter backend
  schema validation because the provider exposes JSON-object mode rather than
  strict JSON Schema as the primary documented mode.

The public and internal conversion contracts stay provider-neutral for
ADR-0010. Provider route selection is operator-internal runtime policy unless a
later governed contract task explicitly adds a public request field.

If Sir Convert later exposes a job-spec route selector, that task must add a
governed `provider_route_class` contract with allowed values, default
semantics, an auth/public-grant matrix, lineage behavior, generated OpenAPI
snapshot updates, request-validation tests, and a Skriptoteket consumer-impact
check. Consumers must never depend on raw model IDs, vendor endpoints, API
keys, or provider-native response shapes.

### 4. Hot Settings Contract

The implementation must separate immutable or sensitive provider catalog data
from mutable routing state.

Provider catalog data includes:

- provider ID;
- endpoint kind;
- structured-output mode;
- model/profile identifier;
- capability flags;
- token budgets;
- timeout and retry limits;
- secret indirection, never raw secrets in persisted runtime settings.

Runtime routing state includes:

- the active default provider profile for new advisory requests;
- allowed provider route classes, such as local-only, API-only, or automatic
  local-first selection;
- per-route remote-provider authorization;
- optional provider weights or priority order for evaluation-only runs;
- rollout labels and operator notes for audit.

Runtime routing state must be reloadable in the running service. Mutation is
operator-only and must be gated by internal identity or an equivalent
deployment-operator authority path. Public/grant callers must not be able to
change provider routing state.

Settings reload must be atomic and versioned. A successful reload emits an audit
event that records at least actor identity, authority source, previous settings
version, new settings version, selected default provider profile, allowed route
classes, remote-provider authorization state, rollout label, timestamp, and
correlation ID. Raw secrets and raw prompts remain excluded from the audit
event.

Invalid, stale, unsigned, or unauthorized settings must fail closed and leave
the last valid active settings version in place. A settings change affects only
new provider calls. Jobs already admitted keep the provider profile and settings
version resolved at admission time so result lineage, retries, and idempotency
remain stable.

If credentials for a brand-new API provider are not already available through
the sanctioned secret source, adding that secret is a separate operations
change. The product requirement here is that switching among configured and
authorized provider profiles does not require restart or container recreation.

### 5. CLI to API Routing

CLI-initiated conversion must route through the same service API and the same
hot settings as browser or backend service calls.

The CLI may expose an operator-facing selector that maps to internal route
classes, for example:

- service default;
- local provider only;
- API provider only;
- named evaluation profile when a governed validation task authorizes it.

This selector is not a public conversion job-spec field in ADR-0010. A public
selector requires the separate contract/OpenAPI/test work described above.

The CLI must not bypass Sir Convert's provider policy by calling OpenAI,
OpenRouter, DeepSeek, or local llama.cpp directly for production answer-key
completion. Direct provider probes remain devops/evaluation tooling only.

### 6. Privacy and Provenance Rules

Remote providers stay forbidden by default for public/grant jobs. Remote API
use requires an authenticated or operator-authorized policy path and explicit
request eligibility.

Every provider lane keeps the existing Epic 11 privacy rules:

- item-local prompt only;
- no full exam;
- no raw `.dxe`;
- no result-PDF content;
- no owner metadata;
- no student data;
- no artifact paths;
- no raw prompt or raw provider response persistence in normal production
  capture.

Provider output remains candidate lineage, not parser evidence. The backend
must validate every candidate against the item-specific schema, source IDs, and
answer payload rules before it can appear in an advisory completion report.
Effective IR changes still require a reviewed completion overlay.

### 7. Provider Capability Decisions

OpenAI is the first API provider because its current structured-output APIs
support strict JSON Schema through:

- Responses API `text.format`;
- Chat Completions `response_format`.

The OpenAI implementation should prefer the Responses API for the first
OpenAI provider profile unless a governed task proves a reason to use Chat
Completions for a specific answer-key request class.

OpenRouter is a second provider profile, not a separate product path. It uses
OpenAI-compatible chat completions and supports both JSON-object and JSON
Schema response formats for compatible models. OpenRouter provider routing
must set required-parameter or model-capability constraints so a request does
not silently land on a model that lacks structured-output support.

DeepSeek is a guarded third provider profile. Its JSON Output mode can be used
only when Sir Convert treats provider output as untrusted JSON and applies the
same backend schema validation, failure mapping, and manual-follow-up behavior
used for all other providers. DeepSeek must not be declared strict JSON Schema
capable unless a later source-backed task proves that exact API support for the
selected model and endpoint.

### 8. HuleEdu LLM Provider Service Position

Do not use the current HuleEdu LLM Provider Service comparison API as Sir
Convert's first API-provider implementation.

A future HuleEdu broker integration may be added only if HuleEdu exposes a
generic structured-completion API or callback contract that can carry:

- schema name and version;
- provider-neutral JSON Schema or declared JSON mode;
- item-local payloads;
- typed provider failure codes;
- metadata-only capture semantics;
- correlation and authorization compatible with Sir Convert's Gateway/internal
  identity model.

Until then, Sir Convert should avoid coupling answer-key completion to
comparison-specific fields such as winner, confidence, justification, and
comparative-judgement callback envelopes.

### 9. Consequences

### Positive

- Sir Convert can add OpenAI quickly through the existing structured-provider
  harness instead of waiting for cross-repo broker work.
- Provider mechanics remain below the DDD/application boundary.
- Operators can switch provider lanes for new jobs without redeploying the
  service after the target route has live service-backed reachability proof.
- Local Qwen3.6 remains available as the guarded default while API quality,
  cost, and reliability are evaluated, with Task 320 carrying the production
  Docker DNS reachability proof.
- OpenRouter and DeepSeek can be added through capability-specific profiles
  instead of broad vendor-specific branches.

### Costs

- Sir Convert needs a hot settings provider, internal mutation authority, and
  audit trail for provider routing changes.
- Tests must prove settings changes affect new requests only and cannot mutate
  in-flight job lineage.
- Secret indirection and provider catalog management need a clear operations
  boundary.
- Remote-provider policy must be wired through CLI, API, and service defaults
  without creating a hidden public fallback.

### 10. Follow-up Implementation Slices

The next governed implementation task should:

- define the hot settings storage/reload contract for structured-provider
  routing;
- add an OpenAI Responses provider profile using existing structured-output
  payload semantics;
- prove that a running service can switch new advisory requests between local
  and OpenAI API profiles without restart or container recreation, after the
  Task 320 Docker DNS local-provider route is green;
- expose CLI-to-API provider route selection through operator-internal route
  classes only, unless the same task adds a governed public contract and
  OpenAPI update;
- retain provider profile ID, provider family, schema version, and route
  decision settings version in advisory report lineage;
- prove public/grant callers cannot mutate route settings, invalid settings do
  not change active routing, already-admitted jobs keep their resolved provider
  profile/settings version, and settings changes emit the required audit event;
- keep public/grant remote-provider policy fail-closed by default.

Task 326 separately owns the model-quality eval gate for
`gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`. Task 325 can implement
the OpenAI provider and hot settings, but no OpenAI profile may become an
operator-selectable production default until Task 326 compares both snapshots
against the current Qwen3.6 baseline through the existing answer-key evaluation
harness/corpus.

OpenRouter and DeepSeek should be separate follow-up tasks after OpenAI is
validated through the same settings and policy boundary.

### 11. Source Notes

- OpenAI documentation checked on 2026-05-18:
  `https://developers.openai.com/api/docs/guides/responses-vs-chat-completions`
  and `https://developers.openai.com/api/docs/guides/structured-outputs`.
  Responses structured output uses `text.format` with JSON Schema, and Chat
  Completions structured output uses `response_format` with `json_schema`.
- OpenRouter documentation checked on 2026-05-18:
  `https://openrouter.ai/docs/features/structured-outputs`,
  `https://openrouter.ai/docs/api-reference/overview`, and
  `https://openrouter.ai/docs/guides/routing/provider-selection/`. Structured
  outputs use `response_format` with `json_schema` for compatible models, with
  model support and required-parameter routing constraints.
- DeepSeek documentation checked on 2026-05-18:
  `https://api-docs.deepseek.com/guides/json_mode/`. JSON Output uses
  `response_format: {"type": "json_object"}` and requires prompt guidance for
  JSON output.
