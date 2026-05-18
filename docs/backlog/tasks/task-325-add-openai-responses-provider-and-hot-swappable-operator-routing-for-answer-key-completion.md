---
id: task-325-add-openai-responses-provider-and-hot-swappable-operator-routing-for-answer-key-completion
title: Add OpenAI Responses provider and hot-swappable operator routing for answer-key completion
type: task
status: in_progress
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md
  - docs/backlog/tasks/task-326-run-openai-mini-nano-answer-key-evaluation-gate-before-provider-promotion.md
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
  - docs/backlog/reviews/review-20-ruthless-review-of-adr-0010-hot-swappable-structured-answer-key-provider-routing.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - structured-llm
  - openai
  - responses-api
  - hot-settings
  - provider-routing
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first API-backed structured answer-key provider directly inside
Sir Convert, using OpenAI Responses structured outputs behind the existing
source-neutral structured-provider harness and ADR-0010 hot-routing decision.

The slice must let operators switch new advisory requests between the proven
local Qwen3.6 production profile and configured OpenAI profiles through
running-service settings, without service restart or container recreation. The
switching surface is operator/internal-identity controlled and remains
operator-internal; this task must not add a public `provider_route_class` or
any other provider selector to the conversion job-spec contract.

## PR Scope

- Add an `openai_responses` provider profile/catalog entry that uses the
  existing source-neutral `StructuredLLMEndpointKind.RESPONSES` and JSON Schema
  output mode.
- Add the first OpenAI model manifest entries as pinned dated snapshots:
  `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`. Do not use broad
  moving aliases for the initial quality gate or default production profile.
- Pin the initial OpenAI Responses behavior settings in the manifest:
  `reasoning_effort=none` and `text_verbosity=low`. Task 326 may evaluate later
  effort/verbosity variants only through an explicit follow-up profile or
  governed eval-lane change.
- Prefer OpenAI Responses API `text.format` structured output for this provider
  profile; keep Chat Completions as existing harness support, not the first
  OpenAI product profile.
- Store API-provider secrets only through existing secret indirection
  (`api_key_env` or successor secret-source reference). Raw OpenAI API keys
  must never be persisted in runtime settings, audit events, advisory reports,
  logs, generated docs, or test fixtures.
- Ensure Hemma's canonical prod env mirror contains the provider API-key names
  needed by the manifest, especially `SIR_CONVERT_A_LOT_OPENAI_API_KEY`, by
  mirroring from sanctioned env files and verifying presence only with redacted
  output.
- Add a hot settings store/loader for structured answer-key routing that
  separates immutable provider catalog data from mutable runtime routing state.
  The active settings version must be reloadable by the running service.
- Add an operator/internal-identity-gated mutation path for the routing state.
  Public/grant callers and normal conversion job submissions must not be able
  to mutate route settings.
- Keep route classes internal to service/CLI operator policy. CLI may map an
  operator selector to internal route classes, but production CLI conversion
  must still call the Sir Convert service API and must not call OpenAI directly.
- Resolve provider profile and settings version at job admission for advisory
  completion. Already-admitted jobs keep their resolved provider profile and
  settings version even if operators switch the active route before the job
  finishes.
- Extend advisory report lineage with metadata needed to audit provider family,
  provider profile ID, provider schema version/output mode, route decision, and
  settings version. Do not persist raw prompts, item text, raw provider
  responses, raw OpenAI request payloads, or API keys.
- Keep public/grant remote-provider use fail-closed by default. A remote OpenAI
  route may be used only for authenticated/operator-authorized policy paths
  with explicit request eligibility.
- Keep Task 311 as the later full HuleEdu auth/public-edge mirror validation
  gate. This task may prove HuleEdu-signed service behavior through the service
  path, but it must not claim public-edge alpha readiness.
- Do not integrate HuleEdu LLM Provider Service in this task. ADR-0010 keeps
  that as future broker work only after HuleEdu exposes a generic structured
  completion contract.
- Keep model-quality promotion out of this implementation slice. Task 326 owns
  the eval-harness run and any eval-harness modifications needed to compare
  both OpenAI model manifest entries against the current local Qwen3.6 baseline.
  Task 325 cannot be marked done and no OpenAI profile may become an
  operator-selectable production route until Task 326 is completed.

## Deliverables

- [x] OpenAI Responses provider catalog/profiles for
  `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`, with secret
  indirection, capability flags, pinned model identifier, token budget, timeout,
  structured output mode, reasoning effort, and text verbosity.
- [x] Hot provider-routing settings storage/reload component with atomic
  versioned loads and last-valid-settings preservation.
- [x] Operator/internal-identity mutation endpoint or command surface for route
  settings, including authorization, validation, and audit emission.
- [x] Service admission wiring that resolves provider profile/settings version
  once per advisory job and passes that resolved lineage through provider calls
  and advisory reports.
- [ ] CLI-to-service operator selector for internal route classes, with no
  direct OpenAI calls and no public job-spec provider selector.
- [x] Tests and docs proving public/grant callers cannot mutate settings,
  invalid/stale settings fail closed, and already-admitted jobs keep their
  resolved provider profile/settings version.
- [ ] Sanitized OpenAI provider validation evidence using mock transport for
  payload/error tests, plus implementation support needed by the separate Task
  326 eval gate. No evidence may expose prompts, item text, raw responses,
  payloads, API keys, owner metadata, student data, or artifact paths.
- [ ] Redacted provider-error diagnostics for failed OpenAI Responses calls,
  retaining only `status_code`, OpenAI `x-request-id` when present,
  `error.type`, `error.code`, `error.param`, and a short-message digest. The
  diagnostic must not retain prompt text, item text, raw images, API keys, raw
  request payloads, or raw response bodies.

## Acceptance Criteria

- [x] Sir Convert can configure an `openai_responses` provider profile using
  Responses structured output and the same source-neutral answer-key schemas
  used by the local provider path.
- [x] The OpenAI model manifest contains pinned profiles for
  `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`; the initial eval and
  production-default decision do not depend on broad moving model aliases or
  implicit provider behavior defaults.
- [ ] OpenAI Responses payload tests prove `text.format` JSON Schema shape,
  strict schema behavior, model/profile metadata, and refusal/failure parsing
  without leaking raw provider responses into production capture.
- [ ] OpenAI HTTP failures preserve enough redacted upstream diagnostics to
  distinguish 400 request-shape defects, 401/403 credential or model-access
  failures, 404 unavailable model/profile, 429 quota/rate limits, and 5xx
  transient provider failures without storing raw provider bodies.
- [x] Task 326 is linked as the required model-quality gate and remains the owner
  for running the existing local-model answer-key evaluation harness/corpus
  against both OpenAI profiles.
- [x] No OpenAI profile becomes an operator-selectable production default, and
  Task 325 is not marked done, until Task 326 completes a sanitized eval report
  comparing both OpenAI snapshots against the current local baseline.
- [x] A running service can switch the active default route for new advisory
  requests between local Qwen3.6 and OpenAI without process restart, Docker
  recreate, or env-only mutation.
- [x] Settings mutation requires operator/internal-identity authority. Public
  conversion requests, grant requests, API-key-only calls, and unsigned callers
  cannot change route settings.
- [x] Runtime settings reload is atomic and versioned. Invalid, stale,
  unsigned, or unauthorized settings leave the last valid active settings in
  place and emit a typed failure/audit signal.
- [x] Settings audit records actor identity, authority source, previous
  settings version, new settings version, selected provider profile, allowed
  internal route classes, remote-provider authorization state, rollout label,
  timestamp, and correlation ID; it excludes raw secrets, prompts, item text,
  and raw provider payloads.
- [x] Already-admitted advisory jobs retain the provider profile and settings
  version resolved at admission time; retries and report lineage cannot drift
  to a later settings version.
- [x] Advisory report lineage records enough metadata to audit local vs OpenAI
  provider selection without exposing vendor-native response bodies or raw
  request content.
- [x] No `provider_route_class`, `service_default`, `local`, `api`, or similar
  public job-spec field is added. If implementation discovers a need for a
  public selector, this task stops and a separate contract/OpenAPI task is
  created first.
- [x] Public/grant remote-provider policy remains fail-closed by default, and
  OpenAI remote use cannot become a hidden fallback for public jobs.
- [ ] Task 320 local-provider service-backed route remains green after adding
  OpenAI. Task 311 remains the gate for full auth/public-edge mirror claims.
- [x] OpenRouter and DeepSeek are not implemented in this task.

## Implementation Checkpoint - 2026-05-18

The first implementation slice is in place:

- `scripts/sir_convert_a_lot/infrastructure/answer_key_openai_model_profiles.py`
  adds the pinned OpenAI Responses profile manifest and secret-indirected
  provider JSON generation.
- `scripts/sir_convert_a_lot/domain/structured_llm_hot_settings.py` adds the
  atomic, versioned hot-settings domain store with last-valid preservation and
  typed audit/failure events.
- `scripts/sir_convert_a_lot/interfaces/http_routes_structured_llm_settings_v2.py`
  adds operator/internal-identity read/update routes for running-service route
  settings.
- `scripts/devops/sync-prod-env-mirror.sh` preserves OpenAI, OpenRouter, and
  DeepSeek provider API-key aliases in Hemma's canonical prod env mirror.
- The OpenAPI v2 generated snapshot includes the internal operator settings
  routes without adding a public job-spec provider selector.
- Hemma prod env was updated from the local repo env on 2026-05-18 and verified
  by key name only for `SIR_CONVERT_A_LOT_OPENAI_API_KEY`, `OPENAI_API_KEY`,
  `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`,
  `SIR_CONVERT_A_LOT_OPENROUTER_API_KEY`, and
  `SIR_CONVERT_A_LOT_DEEPSEEK_API_KEY`. Values were not printed or retained.

Task 325 remains `in_progress`. The remaining implementation work is service
admission wiring, CLI-to-service operator selection, advisory report lineage,
and the already-admitted-job drift proof. Task 326 remains the separate
model-quality gate and blocks both Task 325 done-state and any OpenAI
production-default promotion.

## Implementation Checkpoint - Task 325-B Admission Snapshot

The next implementation slice resolves the open route-lineage decisions as
follows:

- Provider routing is resolved once at v2 job admission and persisted with the
  internal job manifest. Deferred worker execution, supervisor recovery, and
  retries must reuse that admitted snapshot instead of rereading mutable hot
  settings.
- Public/grant remote OpenAI use remains fail-closed. If a public/grant request
  would require a remote provider, admission fails rather than silently falling
  through to OpenAI. If a local provider is configured and allowed, the
  admitted snapshot may pin the local provider.
- Advisory report lineage is report-level, with existing per-item
  `provider_profile_id` and `model_profile` fields preserved for current
  consumers and reviewed-overlay compatibility.

Task 325-B must not add `provider_route_class` or any equivalent selector to
the public `JobSpecV2` or generated OpenAPI job-create contract.

Task 325-B implementation landed on 2026-05-18:

- `domain.structured_llm_admission` defines the persisted admitted route
  snapshot and metadata-only serialization.
- v2 job admission resolves the active hot provider settings once, persists the
  selected provider profile/settings version in the internal job manifest, and
  rejects public-grant remote provider routes before job persistence.
- DigiExam advisory completion executes through the admitted provider profile,
  not the mutable hot settings store, and writes report-level provider lineage.
- Focused tests prove a queued job admitted before a hot switch remains pinned
  to local provider lineage, while a second job admitted after the switch uses
  the OpenAI profile and settings version 2.

## Implementation Checkpoint - Redacted Provider Diagnostics

The next implementation slice adds redacted provider-error diagnostics for the
OpenAI Responses path after the item-13 vision/gap-fill lane collapsed all
upstream failures to `provider_http_error`.

Diagnostic retention is deliberately narrow:

- Keep: `status_code`, OpenAI `x-request-id` response header when present,
  provider `error.type`, `error.code`, `error.param`, and a SHA-256 digest of
  a short sanitized provider message.
- Exclude: prompt text, item text, raw image bytes or data URLs, raw provider
  request payloads, raw provider responses, API keys, owner metadata, student
  data, and artifact paths.
- Interpret status class operationally: `400` means request shape or payload
  incompatibility; `401`/`403` means credential, project, or model access;
  `404` means unavailable model/profile for the configured project; `429`
  means quota/rate limit; `500`/`503` means bounded retry/backoff before
  manual follow-up.

The focused repro source is
`inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1811577114-ekologiprov-v-49-25d-e.dxe`
with `item-013`: a gap-fill item with embedded PNG vision input routed through
the same `gpt-5.4-mini-2026-03-17` Responses profile and structured-output
schema used by the Task 326 OpenAI eval lane.

The sanctioned focused repro command is:

```bash
pdm run run-local-pdm answer-key-live-validation digiexam run-openai-advisory-corpus \
  --openai-provider-profile openai-gpt-5.4-mini-2026-03-17 \
  --api-key-env OPENAI_API_KEY \
  --source-file inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe/1811577114-ekologiprov-v-49-25d-e.dxe \
  --item-id item-013
```

Local focused evidence on 2026-05-18 using the sanctioned `.env` wrapper wrote
`build/verification/task-325-item-013-openai-diagnostics-2026-05-18/in-process-advisory-corpus-run.json`.
It proved `blocked=false`, `item_count=1`, `eligible_item_count=1`,
`suggested_count=1`, `manual_follow_up_count=0`, `backend_failure_counts=[]`,
`asset_eligible_count=1`, `multimodal_request_count=1`, and HTTP `200` for the
provider exchange. That result proves the item-013 Responses multimodal
request shape works with the local `OPENAI_API_KEY` credential source; it does
not by itself prove Hemma's credential/project/model-access lane.

## Test Requirements

- Unit tests for OpenAI Responses payload construction and response/refusal
  parsing through the existing structured-provider boundary.
- Manifest/config tests proving both pinned OpenAI model IDs are represented as
  provider profiles, broad aliases are not used in the initial eval gate, and
  `reasoning_effort=none` plus `text_verbosity=low` are serialized into the
  Responses payload.
- Runtime-config tests for OpenAI provider catalog parsing, secret indirection,
  missing secret failure, remote-provider enablement, and forbidden raw-secret
  persistence.
- Hot-settings tests for atomic version replacement, stale/invalid reload
  failure, last-valid-settings preservation, audit payload fields, and
  admission-time provider/settings-version pinning.
- Authorization tests proving public/grant/API-key-only callers cannot mutate
  settings and that operator/internal-identity mutation is required.
- Service/API tests proving new requests use the updated active route while
  already-admitted jobs keep their original route.
- CLI tests proving operator route selection calls the Sir Convert service API
  and does not call OpenAI, OpenRouter, DeepSeek, or llama.cpp directly.
- Capture/privacy tests proving raw prompts, item text, raw provider responses,
  raw provider request payloads, API keys, owner metadata, student data, and
  artifact paths are absent from normal production reports/logs.
- Integration support tests proving Task 326 can select each OpenAI profile
  through provider-profile configuration without model-name branches.
- Focused docs validation plus any code gates required by touched modules.

## Stop Conditions

- Stop if a public provider selector is needed; create a separate
  converter-contract/OpenAPI/Skriptoteket-impact task before adding it.
- Stop if a raw OpenAI API key would need to be written to docs, env mirrors,
  tests, reports, or logs.
- Stop if provider routing would require weakening HuleEdu signed-identity
  requirements or public/grant remote-provider policy.
- Stop if implementation would conflate HuleEdu LLM Provider Service broker
  work with the direct Sir Convert provider task.
- Stop before marking this task done or enabling an OpenAI production default
  unless Task 326 has completed the governed eval against both
  `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`.
- Stop before claiming full public-edge alpha readiness; that remains Task 311.

## Source Notes

- OpenAI documentation checked on 2026-05-18:
  `https://platform.openai.com/docs/guides/structured-outputs?api-mode=responses&lang=python`
  documents Responses API structured output through `text.format`.
- OpenAI Responses API reference checked on 2026-05-18:
  `https://platform.openai.com/docs/api-reference/responses/compact?api-mode=responses`
  documents `POST /v1/responses` and response format schema support.
- OpenAI model pages checked on 2026-05-18:
  `https://developers.openai.com/api/docs/models/gpt-5.4-mini` and
  `https://developers.openai.com/api/docs/models/gpt-5.4-nano` are the source
  notes for the pinned model manifest snapshots
  `gpt-5.4-mini-2026-03-17` and `gpt-5.4-nano-2026-03-17`.
- ADR-0010 source notes also record that OpenAI structured output supports
  Responses `text.format` and Chat Completions `response_format`, with
  Responses preferred for the first OpenAI provider profile.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
