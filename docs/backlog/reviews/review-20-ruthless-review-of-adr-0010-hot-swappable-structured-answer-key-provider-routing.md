---
id: review-20-ruthless-review-of-adr-0010-hot-swappable-structured-answer-key-provider-routing
title: Ruthless review of ADR-0010 hot-swappable structured answer-key provider routing
type: review
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md
  - docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md
labels:
  - review
  - adr-0010
  - answer-key-completion
  - provider-routing
  - hot-settings
  - openai
  - approved
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless docs-as-code decision review of ADR-0010.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md`
  - `docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md`
  - `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md`
  - `docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md`
- Primary files reviewed:
  - `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md`
  - `docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md`
  - `docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md`
  - `docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md`
  - `docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md`
  - `docs/reference/ref-machine-marked-answer-key-completion-implementation-roadmap.md`
- Public surfaces affected:
  - `digiexam_dxe -> examnet_migration_bundle` job-spec provider routing.
  - Structured answer-key provider profile selection.
  - Runtime service settings for new advisory requests.
  - CLI/API route-class selection for local/API providers.
  - Advisory report provider lineage.
- Compatibility posture:
  - ADR-0010 is proposed and must not be treated as accepted production
    behavior until review findings are remediated.
  - Existing public job-spec fields are `completion_mode` and
    `remote_provider_policy`; any new provider route selector is a public
    contract change unless explicitly kept operator-internal.
  - Public/grant remote-provider use remains forbidden by default and must fail
    closed.
- Evidence reviewed:
  - Line-numbered inspection of ADR-0010 and adjacent Epic 11, Story 47,
    converter contract, reference, roadmap, Task 311, and Task 320 surfaces.
  - `pdm run docs-validate` -> `Validated 406 backlog files` and
    `Validated docs=476 rules=11`.
  - `pdm run skills-validate` -> ok.
  - `pdm run handoff-validate` -> ok.
  - `git diff --check` -> no whitespace errors.
  - Primary third-party documentation checked for the API syntax claims:
    OpenAI Responses/structured outputs, OpenRouter structured outputs, and
    DeepSeek JSON Output.

## Findings

1. [x] `high` - ADR-0010 treats local Qwen3.6 as an available routed baseline
   without carrying the service-backed production precondition from Task 320.

   Evidence:

   - ADR-0010 states that Sir Convert currently supports local structured
     answer-key completion through the guarded Qwen3.6 MTP runtime at
     `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md:50`.
   - ADR-0010 then requires operators and sanctioned CLI/API flows to switch new
     advisory requests between local and API providers through running service
     settings at
     `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md:61`.
   - Task 320 says the production failure is namespace-specific: Task 319 proved
     the provider on host `127.0.0.1:8082`, while the production Sir Convert
     container tried to use that loopback address from inside its own namespace,
     causing `provider_request_failed` at
     `docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md:38`.
   - Task 320's production reachability acceptance items are still unchecked at
     `docs/backlog/tasks/task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production.md:97`.

   Why it matters:
   Hot routing between local and API profiles is only meaningful if both routed
   profiles are reachable from the running service path. Without a Task 320 or
   Task 311 precondition, ADR-0010 can authorize a settings switch that looks
   successful while local-provider calls still fail inside production networking.

   Required fix:
   Amend ADR-0010 so hot production routing depends on the Task 320/Task 311
   service-backed provider reachability proof. If the ADR wants to proceed
   before that proof, scope local routing as dev/in-process only and block
   production `local`/`service_default` claims until the Docker DNS provider path
   is proven.

   Proof requirement:
   Update ADR-0010, the roadmap, and the next implementation task with an
   explicit service-backed reachability gate. Run `pdm run docs-sync`,
   `pdm run docs-validate`, `pdm run skills-validate`,
   `pdm run handoff-validate`, and `git diff --check`.

   Re-review:
   Addressed. ADR-0010 now links Task 320 and Task 311, records that Task 320
   is the production Docker DNS local-provider route gate, and states that
   authenticated/public-edge mirror claims remain blocked until Task 311 is
   green. Task 320 is now marked `done` and retains the service-backed proof
   details for `sir_convert_a_lot_prod -> sir_convert_qwen_answer_key:8082`,
   constrained JSON microprobe output, API-key-only rejection, and a
   HuleEdu-signed service job with 0 `provider_request_failed` rows.

1. [x] `high` - ADR-0010 introduces public provider route classes before the
   service API contract owns the field, values, auth matrix, and OpenAPI
   migration.

   Evidence:

   - ADR-0010 says consumer job specs may request governed provider route
     classes such as `service_default`, `local`, or `api` at
     `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md:103`.
   - The current converter contract only documents `completion_mode` and
     `remote_provider_policy` for answer-key provider behavior at
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:481`.
   - The current contract still says public/grant jobs must keep
     `remote_provider_policy` forbidden until a later signed grant version
     explicitly allows otherwise at
     `docs/converters/digiexam-migration-service-api-artifact-contract.md:487`.

   Why it matters:
   `service_default`/`local`/`api` is a new public request surface if exposed in
   job specs. Without a contract field, OpenAPI snapshot, strict validation,
   and consumer migration note, strict consumers can drift or operators can
   enable API-provider use through a selector that is not governed by the
   existing remote-provider policy.

   Required fix:
   Either keep provider route selection operator-internal for ADR-0010, or add a
   governed `provider_route_class` contract with allowed values, default
   semantics, auth/public-grant matrix, lineage behavior, generated OpenAPI
   update, and Skriptoteket consumer-impact check. Treat the field as a clean
   contract addition governed by the next task, not as incidental ADR prose.

   Proof requirement:
   Add or amend the next implementation task so it updates the converter
   contract and OpenAPI snapshot, then add request-validation tests for allowed
   and forbidden route classes across public/grant and authenticated/operator
   paths. Run `pdm run openapi-export-v2` if the public schema changes, focused
   contract tests, and the docs gates.

   Re-review:
   Addressed. ADR-0010 now says public/internal conversion contracts stay
   provider-neutral for ADR-0010 and that provider route selection is
   operator-internal unless a later governed contract task explicitly adds a
   public request field. It also names the required future
   `provider_route_class` contract, OpenAPI update, request-validation tests,
   and Skriptoteket consumer-impact proof before any public selector exists.

1. [x] `medium` - ADR-0010 requires reloadable hot settings but does not define
   the mutation authority, atomicity, audit fields, or fail-closed stale-settings
   behavior tightly enough for paid remote-provider routing.

   Evidence:

   - ADR-0010 requires runtime routing state to be reloadable in the running
     service at
     `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md:133`.
   - ADR-0010 lists mutable routing state such as active default provider,
     allowed route classes, remote-provider authorization, weights/priority, and
     rollout labels/operator notes at
     `docs/decisions/0010-hot-swappable-structured-answer-key-provider-routing.md:124`.
   - ADR-0010 separates secret indirection from raw secrets, but does not define
     who may mutate settings, how a settings version is atomically loaded, what
     audit event is emitted, or what happens when a reload is invalid or stale.

   Why it matters:
   The hot settings path can redirect traffic to remote paid providers and can
   change privacy/cost/runtime identity for new advisory requests. Soft wording
   like sanctioned CLI/API flows and operator notes is not enough to prevent
   fail-open route changes, unaudited switches, or lineage that cannot prove
   which settings version admitted a job.

   Required fix:
   Amend ADR-0010 to require operator-only or internal-identity-gated mutation,
   atomic versioned settings, explicit audit fields, fail-closed invalid/stale
   reload behavior, and provider-profile resolution captured at job admission.

   Proof requirement:
   The implementation task must add tests proving public/grant callers cannot
   mutate route settings, invalid settings do not change active routing,
   already-admitted jobs keep their resolved provider profile/settings version,
   and advisory reports include enough lineage to audit the selected provider
   route.

   Re-review:
   Addressed for ADR readiness. ADR-0010 now requires operator-only mutation
   gated by internal identity or equivalent deployment-operator authority,
   atomic versioned settings, audit fields, fail-closed handling for invalid,
   stale, unsigned, or unauthorized settings, preservation of the last valid
   active settings version, and admission-time provider profile/settings-version
   lineage for in-flight jobs.

## Decision

approved

## Response

ADR-0010 is not accepted yet. The decision shape is directionally sound, and the
review did not find a blocker in the basic OpenAI/OpenRouter/DeepSeek structured
output syntax claims. Approval is blocked on repo contract boundaries: production
local-provider reachability must be made an explicit precondition, public route
classes must be either kept internal or promoted into the converter/OpenAPI
contract, and hot settings need a stronger authority/audit/fail-closed contract.

### 2026-05-18 Follow-up Response

The follow-up docs response keeps the review open for re-check but addresses the
requested changes in the governed surfaces:

- ADR-0010 now links Task 320 and Task 311, records that Task 320 has fresh
  Hemma Docker DNS reachability proof for the production local provider route,
  and keeps Task 311 as the authenticated/public-edge mirror gate.
- Task 320 now has fresh live status for the running Hemma production provider:
  `sir_convert_a_lot_prod` reaches
  `http://sir_convert_qwen_answer_key:8082`, `/v1/models` returns
  `qwen3.6-27b-q6k-mtp`, and a JSON Schema MCQ microprobe returns constrained
  JSON from the production namespace.
- Task 320 was then completed with HuleEdu-signed service proof:
  `jobv2_6843fafd02f0402285763eb6e7` produced an available
  `answer_key_completion_report_v1` with 19 rows, 8 suggestions, and 0
  `provider_request_failed` rows. The proof also confirmed API-key-only access
  is rejected with `auth_invalid_internal_identity`, preserving the HuleEdu auth
  edge contract.
- ADR-0010 no longer introduces `service_default`, `local`, or `api` as public
  job-spec fields. Route selection is operator-internal unless a later governed
  contract task adds `provider_route_class`, OpenAPI, validation tests, and
  Skriptoteket consumer-impact proof.
- ADR-0010 now requires operator/internal-identity mutation authority, atomic
  versioned settings, explicit audit fields, fail-closed invalid/stale settings,
  and admission-time provider profile/settings-version lineage.

### 2026-05-18 Re-review

The retained findings are closed. ADR-0010 remains a proposed decision until the
repo's decision workflow accepts it, but Review 20 no longer blocks it on the
three contract issues from the initial review.

## Follow-up Actions

1. Keep ADR-0010 proposed until the explicit decision acceptance step promotes
   it. The next implementation task must still prove the hot-settings runtime
   behavior and OpenAI provider path with focused tests before production use.

## Completion

Review retained on 2026-05-18 with `changes_requested`, then re-reviewed on
2026-05-18 and closed as `approved`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
