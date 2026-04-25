---
id: review-06-ruthless-review-of-adr-0009-gateway-cutover-readiness
title: Ruthless review of ADR-0009 gateway cutover readiness
type: review
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
labels:
  - review
  - adr-0009
  - gateway
  - auth
  - cutover
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Reviewed working-tree docs changes for the ADR-0009 readiness slice, with
  focus on Task 256 caller/access-lane inventory closeout, Task 259
  `InternalIdentityContextV1` authorization profile closeout, and whether Task
  257 can safely accept ADR-0009.
- Public/contract surfaces under review:
  - ADR-0009 Gateway-fronted public access and internal service boundary.
  - Sir Convert downstream/internal adapter docs.
  - Caller inventory and new auth-aware public-edge evidence task.
  - Sir Convert `InternalIdentityContextV1` authorization profile.
- Compatibility posture:
  - Docs-only planning/contract change in this slice.
  - The eventual runtime cutover is a clean, governed security hardening: global
    API-key ownership is not preserved for user-originated work, while direct
    internal and local operator lanes remain first-class if their identity
    profile is explicit and testable.
- External contract checked:
  `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/reference/ref-internal-identity-context-v1-contract.md`
  and the corresponding `InternalIdentityContextV1` model. The canonical
  contract requires nonblank `iss`, `aud`, `sub`, `session_id`,
  `policy_version`, and `jti`, and states that Gateway produces the signed
  context for downstream services.
- Validation evidence gathered:
  - `pdm run docs-validate`: passed.
  - `pdm run skills-validate`: passed.
  - `pdm run handoff-validate`: passed.
  - `pdm run index-tasks --root docs/backlog --out /tmp/sir_tasks_index_review_adr0009.md --fail-on-missing`: passed.
  - `git diff --check`: passed.

## Findings

1. `blocker` - Non-browser service/operator identity is named but not
   contract-complete enough to accept ADR-0009.

   - Evidence:
     `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
     lines 80-88 define non-browser internal service and local operator caller
     classes as Sir-profiled contexts using the canonical HuleEdu identity
     headers. Lines 113-130 then list Sir owner fields for service/operator
     workloads, but do not define the minting authority, route to obtain those
     contexts, required canonical payload values, or how mandatory HuleEdu
     fields such as nonblank `session_id` are represented for service and
     operator actors. The upstream HuleEdu contract and model require nonblank
     `session_id` and describe the context as produced by API Gateway for
     downstream service requests.
   - Why it matters:
     This leaves the exact gap Task 259 was supposed to close. Runtime
     implementers still have discretion to invent an operator/service signer,
     overload browser-session fields with ad hoc values, keep API-key-only
     authorization for retained internal callers, or route local operator work
     through a browser-adjacent ceremony. Any of those would weaken the ADR's
     central rule: no parallel Sir identity transport and no global API-key
     ownership for jobs/artifacts.
   - Required fix:
     Reopen or amend Task 259 before accepting Task 257. The profile must
     explicitly define one of these clean shapes:
     either service/operator contexts are minted by an accepted HuleEdu
     Gateway/service-token authority using the existing Gateway signing key and
     a documented non-browser field mapping, or service/operator identity is
     deferred to a separate ADR/task and ADR-0009 is narrowed to
     Gateway/user-originated workloads only. If service/operator contexts stay
     in scope, specify `iss`, `aud`, `sub`, `session_id`, `org_id`,
     `tenant_id`, `roles`, `grants`, `source_app`, `active_app`,
     `policy_version`, `jti`, TTL/skew, key trust, lane restrictions, and audit
     semantics for each retained caller class.
   - Proof requirement:
     Add implementation-test requirements that prove service and operator
     contexts are accepted only from the chosen minting authority, satisfy the
     upstream `InternalIdentityContextV1` verifier without spoofed fields, and
     cannot be used on public/browser routes. Re-run the docs gates plus the
     future Task 258/260 route tests that cover wrong audience, invalid
     signature, API-key-only calls, and cross-owner artifact reads.

## Decision

approved

## Response

ADR-0009 is ready for acceptance by Task 257 after the second re-review. Earlier
changes-requested findings are retained below as review history and are resolved
by the follow-up profile changes.

## Follow-up Actions

1. Completed: amended
   `docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md`
   to lock the non-browser service/operator minting authority and canonical
   field mapping.
1. Completed: kept
   `docs/backlog/tasks/task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access.md`
   proposed until the Task 259 blockers were resolved.
1. Keep
   `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`
   as a Task 263 cutover blocker, but it does not by itself block ADR
   acceptance now that the identity-profile gap is fixed.

## Completion

Initial review completed on 2026-04-19 with changes requested. The second
re-review on 2026-04-19 approved ADR-0009 acceptance readiness after the
minting-authority and HuleEdu v1 schema blockers were resolved.

## Re-review Addendum 2026-04-19

The follow-up resolves the original minting-authority blocker: the profile now
states that non-browser service/operator contexts are minted only by a
HuleEdu-owned Gateway/internal identity authority using the canonical HuleEdu
signing key set and `iss == "api_gateway_service"`.

New finding:

1. `blocker` - Sir-specific top-level context fields violate the upstream
   `InternalIdentityContextV1` schema.

   - Evidence:
     `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`
     lines 156-158 define `sir_convert_context_kind`,
     `sir_convert_registered_caller`, and `sir_convert_workload_purpose` as
     signed fields inside `X-Huledu-Identity-Context`. The canonical HuleEdu
     model at
     `/Users/olofs_mba/Documents/Repos/huledu-reboot/libs/common_core/src/common_core/internal_identity_context.py`
     lines 28-58 uses `ConfigDict(extra="forbid")` and does not include those
     fields. The HuleEdu reference contract lists the allowed required and
     optional payload fields, and these Sir-specific names are not among them.
   - Why it matters:
     A HuleEdu-minted context that includes those top-level fields will fail the
     canonical `InternalIdentityContextV1` verifier before Sir Convert can
     derive ownership. If implementers instead bypass the canonical verifier to
     accept them, ADR-0009 silently creates a forked Sir-specific identity
     contract, which is exactly what the ADR forbids.
   - Required fix:
     Keep Sir Convert on the accepted HuleEdu schema. Encode service/operator
     kind, registered caller, and workload purpose using existing allowed fields
     such as `sub`, `source_app`, `active_app`, `roles`, `grants`,
     `policy_version`, and/or `active_context`; or first extend the upstream
     HuleEdu `InternalIdentityContextV1` contract/model through its own accepted
     governance path and then consume that version explicitly. Do not add
     undeclared top-level `sir_convert_*` fields to v1.
   - Proof requirement:
     Add or name a contract test that builds representative service and operator
     contexts with the final mapping and verifies them through the canonical
     HuleEdu `InternalIdentityContextV1` verifier. Also prove malformed contexts
     with unknown top-level `sir_convert_*` fields fail closed.

Re-review decision: `changes_requested`. ADR-0009 remains denied for
acceptance until the new schema-compatibility blocker is resolved.

## Second Re-review Addendum 2026-04-19

The schema-compatibility blocker is resolved. The Sir Convert profile no longer
defines top-level `sir_convert_context_kind`, `sir_convert_registered_caller`,
or `sir_convert_workload_purpose` fields inside `InternalIdentityContextV1`.
It keeps the top-level payload within HuleEdu v1 by deriving:

- context kind from `sub` prefix plus `roles`;
- registered caller from `source_app`, with `active_app` as an optional
  discriminator;
- workload purpose from route family and `sir-convert:*` grants, optionally
  narrowed by signed `active_context.sir_convert`.

The original minting-authority blocker also remains resolved: service/operator
contexts must be minted by a HuleEdu-owned Gateway/internal identity authority
using the canonical HuleEdu signing key set and `iss == "api_gateway_service"`.
Sir Convert, service callers, and operator CLI tooling are explicitly forbidden
from signing their own contexts.

No new findings.

Second re-review decision: `approved`. Review 06 is closed for ADR-0009
acceptance readiness. ADR-0009 itself remains `proposed` until Task 257 performs
the acceptance update.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
