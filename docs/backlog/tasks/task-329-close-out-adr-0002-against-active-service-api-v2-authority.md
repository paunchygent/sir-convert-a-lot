---
id: task-329-close-out-adr-0002-against-active-service-api-v2-authority
title: Close out ADR-0002 against active Service API v2 authority
type: task
status: proposed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/service_api_v1_v2_compatibility_policy.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md
  - docs/backlog/tasks/task-44-remove-v1-api-cli-clients-and-contracts-clean-break-to-v2.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/backlog/tasks/task-328-audit-open-proposed-adr-product-decisions-before-further-architecture-expansion.md
  - docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md
labels:
  - adr
  - v2
  - decision-closeout
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close ADR-0002's stale proposed state against current Service API v2 authority.

Task 328 and Review 21 identified ADR-0002 as the only proposed ADR whose state
is stale against implemented/runtime contract truth. ADR-0002 introduced Service
API v2 on 2026-02-18, but the active converter contract, v1-removal tasks, and
accepted follow-on ADRs have moved beyond the original proposal.

This task must compare the original ADR-0002 text with the current v2 contract
and then explicitly close the decision state. The recommended closeout path is
to preserve ADR-0002 as historical proposed pivot work, mark it superseded, and
create a new accepted current-state decision for active Service API v2
authority.

## PR Scope

- Compare ADR-0002 against the current normative v2 contract:
  `docs/converters/multi_format_conversion_service_api_v2.md`.
- Compare ADR-0002 against the generated OpenAPI/runtime route set:
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json` and canonical
  FastAPI router registrations.
- Compare ADR-0002 against v1 clean-break authority from Tasks 44 and 51.
- Compare ADR-0002 against accepted follow-on v2 ADRs:
  - ADR-0003, async push delivery;
  - ADR-0004, PDF layout presets, preview rendition, and `docx -> pdf`;
  - ADR-0005, long-job progress/checkpoints/partials/cancel/resume/retention;
  - ADR-0006, Hemma sidecar TTS and non-PDF GPU governance;
  - ADR-0007, reusable multi-backend TTS sidecar capability contract;
  - ADR-0008, curated app-owned PDF exports stay out of Sir Convert v2.
- Decide the closeout form explicitly:
  - accept ADR-0002 only if its text can be amended without erasing historical
    truth; or
  - supersede ADR-0002 with a new accepted current-state decision.
- Update affected links/status sections in ADR, converter, backlog, and handoff
  docs in the same slice.
- Create a review artifact after the ADR status/new-decision edit, because
  status changes must not be accepted silently.

Out of scope:

- Runtime implementation or route changes.
- Hemma deploy/prod changes.
- HuleEdu or Skriptoteket repo changes.
- Accepting ADR-0009 or ADR-0011.
- Widening operator-only, exam-authoring, or Gateway cutover contracts under
  ADR-0002 without their own governed authority.

## Evidence Matrix

| Question | Current evidence | Required closeout handling |
| --- | --- | --- |
| Is ADR-0002 accepted authority today? | ADR-0002 frontmatter still says `status: proposed`. | Do not cite ADR-0002 as accepted until this task closes it or supersedes it. |
| Does ADR-0002 match current v1/v2 truth? | ADR-0002 says to keep v1 endpoints unchanged; active v2 docs and Tasks 44/51 say `/v1/convert/jobs*` was removed from the runtime surface. | Prefer supersession over direct acceptance, or document every amendment if acceptance is chosen. |
| Is Service API v2 active? | `multi_format_conversion_service_api_v2.md` is `status: active` and names v2 as the single active conversion contract surface. | New accepted decision should make this explicit as decision authority. |
| Has the v2 route surface expanded since ADR-0002? | Active contract includes `pdf -> md`, `pdf -> docx`, template/DOCX paths, async push, partial/checkpoint endpoints, DigiExam migration, and approved-not-implemented TTS route planning. | New decision should summarize extension policy and link accepted follow-on ADRs instead of rewriting them. |
| Is runtime route truth available without live Hemma work? | Generated OpenAPI and FastAPI route registrations expose current local contract routes. | Use static OpenAPI/router proof for the ADR closeout; stop before live deploy claims unless drift is found. |
| Do downstream contracts assume v2-only? | Downstream integration contract says conversion integrations are v2-only and `/v1/convert/jobs*` is unsupported. | Closeout should align downstream authority with the accepted decision state. |

## Open Questions and Recommendations

1. Closeout form

   Options:

   - Accept ADR-0002 after amending it to current v2-only reality.
   - Supersede ADR-0002 with a new accepted current-state decision.

   Recommendation: supersede ADR-0002. The original proposal is historically
   useful, but the v1-preservation language and later v2 extension surface no
   longer match active truth closely enough for a clean acceptance.

1. Scope of "Service API v2"

   Options:

   - Treat every `/v2/*` route as covered by the ADR-0002 closeout.
   - Cover the multi-format conversion authority surface and explicitly linked
     route-specific converter extensions only.

   Recommendation: cover conversion authority plus linked route-specific
   extensions. Do not silently bless operator settings, Gateway access, or
   exam-authoring routes under ADR-0002 unless their own governed docs already
   establish that relationship.

1. V1 handling

   Options:

   - Rewrite ADR-0002 to remove its original v1-preservation decision.
   - Leave ADR-0002 as a historical record, mark it superseded, and point to
     the new accepted current-state decision.

   Recommendation: leave historical text intact and add a status/supersession
   note. Tasks 44 and 51 are the clean-break evidence; the new ADR should carry
   the current decision state.

1. Evidence bar

   Options:

   - Docs-only comparison.
   - Docs plus OpenAPI/router proof.
   - Docs plus live Hemma proof.

   Recommendation: docs plus OpenAPI/router proof. This is a decision-governance
   closeout, not a deploy task. Live Hemma proof is required only if the static
   contract comparison uncovers runtime/doc divergence.

1. Follow-on ADR handling

   Options:

   - Fold ADR-0003 through ADR-0008 into the new decision body.
   - Link and summarize them as accepted v2 extensions.

   Recommendation: link and summarize. The new decision should declare base v2
   authority, v2-only clean-break state, additive extension policy, and the
   extension boundary, while leaving each accepted ADR as the detailed authority
   for its own contract.

1. Review requirement

   Options:

   - Close the task with internal validation only.
   - Require a separate review artifact before treating the ADR status/new
     accepted decision as closed.

   Recommendation: require a review. Task 328 and Review 21 explicitly guarded
   against silent ADR acceptance/supersession.

## Deliverables

- [ ] ADR-0002 comparison table covering original claims, current contract
  truth, runtime/OpenAPI route truth, and follow-on ADR authority.
- [ ] Chosen closeout form recorded with rationale.
- [ ] Recommended implementation: new accepted current-state Service API v2
  decision created and ADR-0002 marked `superseded`.
- [ ] Converter/backlog/handoff links updated so Service API v2 decision
  authority is no longer split between active runtime docs and proposed ADR
  state.
- [ ] Review artifact created for the status-changing closeout.
- [ ] Validation evidence recorded.

## Acceptance Criteria

- [ ] ADR-0002 is no longer silently stale as a proposed ADR.
- [ ] If ADR-0002 is accepted, every divergence from current runtime/contract
  truth is amended explicitly and linked to evidence.
- [ ] If ADR-0002 is superseded, the replacement accepted decision names current
  v2 authority, v2-only clean-break state, accepted follow-on ADR boundaries,
  and the route-extension policy.
- [ ] No runtime, Hemma, Gateway, HuleEdu, Skriptoteket, ADR-0009, or ADR-0011
  change is bundled into this task.
- [ ] OpenAPI/router proof is captured or, if skipped, the task records why
  static docs evidence was sufficient.
- [ ] A review record approves the ADR status/new-decision closeout before the
  task is marked completed.
- [ ] Validation passes with:
  - `pdm run docs-sync`
  - `pdm run docs-validate`
  - `pdm run skills-validate`
  - `pdm run handoff-validate`
  - `git diff --check`

## Stop Conditions

- Stop if the current OpenAPI/runtime route set contradicts the active converter
  contract; create a runtime/docs drift task instead of forcing an ADR closeout.
- Stop before changing service runtime behavior or generated OpenAPI snapshots
  unless a separate implementation task authorizes that work.
- Stop before treating operator-only structured LLM settings, Gateway cutover,
  or exam-authoring correction APIs as covered by the base v2 conversion ADR
  without explicit linked authority.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
