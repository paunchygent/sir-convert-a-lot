---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-04-19'
---

## Purpose

Keep only volatile Sir Convert-a-Lot agent state, blockers, validation evidence,
and next actions. Move durable session history to
`.codex/long-term-memory/entries/` and governed doctrine to docs, rules,
runbooks, or skills.

## Current State

- The current active implementation lane is now the Epic 03 / Story 05 DevOps
  lane for Hemma-hosted service operations.
- Task 254 remains the immediate production recovery authority for detached
  deploy verification, public HTTPS proof, and reserved default-host behavior.
- Task 255 is completed and pushed to `main`. Dependency image inputs live
  under `docker/service-deps/`, `Dockerfile.deps` owns ROCm/CPU dependency
  images, and production/local runtime Dockerfiles consume explicit
  `DEPS_IMAGE` app layers.
- Review 05 Task 255 follow-up is completed and pushed to `main`. Dependency
  image freshness now includes build-recipe truth through a separate recipe
  hash, a combined dependency-image hash, and Docker label verification before
  accepting existing dependency image tags.
- Epic 09 is proposed for the Sir Convert Gateway cutover. ADR-0009, Stories
  33-37, Tasks 256-264, and
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md` now
  govern the planning path.
- ADR-0009 review feedback has been incorporated into the planning spine:
  Sir Convert consumes HuleEdu `InternalIdentityContextV1` with audience
  `sir-convert-a-lot` instead of minting a parallel identity contract, Task 259
  is a hard prerequisite for ADR acceptance, user-originated backend jobs must
  carry context-derived ownership, unknown public consumers require empirical
  public-edge evidence, and `convert.hule.education` defaults to a fail-closed
  reserved posture after cutover.
- Third-pass review approved the Epic 09 planning spine. Keep ADR-0009
  proposed until Task 259 locks the Sir-specific `InternalIdentityContextV1`
  authorization profile and proves non-browser service/operator extensions do
  not introduce a second signed issuer or browser-adjacent auth path.
- Task 265 is completed, pushed, pulled on Hemma, and redeployed from commit
  `f6eebfecd2cee273699e5b656ac49f7fb26cd248`. `sir_convert_a_lot_prod` remains
  healthy on the internal/tunnel lane, while `sir_convert_a_lot_public_reserved`
  owns `convert.hule.education` and returns the reserved non-product public
  response until the Gateway cutover deliberately re-enables the intended
  public edge.
- Task 256 is completed. The caller inventory found no direct HuleEdu app
  caller, found Skriptoteket user-originated backend callers in Conversion Hub
  and Klassrumskartan class-list PDF import, found Projektveckor Portal as a
  retained internal Hemma caller, and preserved the local operator tunnel/offload
  lane.
- Task 266 is proposed as the follow-up for auth-aware public-edge evidence.
  The Task 256 24h nginx-proxy evidence did not show successful public
  conversion traffic, but unknown public consumers remain a Task 263 cutover
  blocker until API-key presence can be classified without logging secrets.
- Task 259 is completed as a contract/profile definition task. The Sir Convert
  authorization profile consumes HuleEdu `InternalIdentityContextV1` with
  audience `sir-convert-a-lot`, defines context-derived job/artifact ownership,
  keeps `X-API-Key` transport-only during migration, and names implementation
  tests for spoofed headers, wrong audience, invalid signatures, cross-owner
  reads, service contexts, and operator contexts.
- Review 06 denied ADR-0009 acceptance. The remaining blocker is that
  non-browser service/operator contexts are named but not contract-complete:
  the docs must lock the minting authority and canonical field mapping,
  including mandatory HuleEdu `session_id`, without introducing a parallel Sir
  signer or browser-adjacent operator path.
- Review 06 follow-up amended Task 259 and the authorization profile:
  service/operator contexts must be minted only by a HuleEdu-owned
  Gateway/internal identity authority using the canonical HuleEdu signing key
  set and `iss == "api_gateway_service"`. Sir Convert, internal service
  callers, and operator CLI tooling must not sign contexts. Non-browser
  contexts now have explicit signed field mappings, nonblank non-browser
  `session_id` handles, lane restrictions, and audit semantics.
- Review 06 re-review kept ADR-0009 denied. The remaining blocker is schema
  compatibility: the profile adds top-level `sir_convert_*` fields to
  `InternalIdentityContextV1`, but the upstream HuleEdu v1 model forbids extra
  fields.
- Review 06 schema follow-up amended the profile to keep the top-level payload
  valid under HuleEdu `InternalIdentityContextV1` v1. Sir Convert now derives
  context kind from `sub` and `roles`, registered caller from `source_app`, and
  workload purpose from route/grants with optional narrowing through signed
  `active_context`; unknown top-level `sir_convert_*` fields must fail closed.
- Review 06 second re-review approved ADR-0009 acceptance readiness. ADR-0009
  remains proposed until Task 257 performs the explicit acceptance update.
- `TASK-0046` compacted this handoff, moved durable March 2026 history into
  long-term memory, and added the real `pdm run handoff-validate` command
  surface.
- `TASK-0043` completed the direct governance cutover from `.agents/` paths to
  `.codex/` paths. Do not recreate compatibility shims.
- `TASK-0045` added the shared command grammar now available in this repo:
  `pdm run docs-validate` and `pdm run skills-validate`.
- Generated repomix packages belong under ignored `.codex/repomix_packages/`;
  do not track generated XML packages.

## Active Pointers

- Active planning log: `docs/backlog/current.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active public-edge recovery task: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- Active dependency-image follow-up task: `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
- Active Gateway cutover planning epic:
  `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Gateway cutover inventory reference:
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`.
- Sir Convert identity authorization profile:
  `docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md`.
- Completed Gateway cutover profile task:
  `docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md`.
- Auth-aware public-edge evidence follow-up:
  `docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md`.
- ADR-0009 readiness review:
  `docs/backlog/reviews/review-06-ruthless-review-of-adr-0009-gateway-cutover-readiness.md`.
- Active Qwen Task 101 ledger:
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Qwen experiment governance:
  `.codex/rules/096-qwen-experiment-governance.md`.
- Hemma/Qwen runbook:
  `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`.
- Durable session-history index:
  `.codex/long-term-memory/index.md`.

## Durable Memory

- TASK-0043 governance cutover memory:
  `.codex/long-term-memory/entries/session-2026-04-16-task-0043.md`.
- March 2026 service, local runtime, service image, and Qwen operator
  history compacted from the former long handoff:
  `.codex/long-term-memory/entries/session-2026-03-25-service-and-qwen-operator-history.md`.

## Next Actions

1. Continue Epic 09 with Task 257: accept ADR-0009 now that Review 06 is closed
   and the Task 256/259 prerequisites are complete.
1. Then move into Task 258/260 implementation planning: runtime enforcement,
   metadata hardening, Gateway route mechanics, and route tests must prove the
   profile rather than merely referencing it.
1. Keep Task 266 in the cutover gate before Task 263 final proof: collect
   auth-aware public-edge evidence with API-key presence represented only as
   `present`, `absent`, or `unavailable`.
1. Keep Task 254's deploy verifier follow-up available for future public-edge
   proof hardening without reopening the completed Task 265 reserved-host
   deployment posture.
1. Before any future Hemma Qwen run, use:
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   and
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`.

## Validation

- 2026-04-19 Task 255, Review 05, and the initial Epic 09 docs-governance
  gates/proofs passed; durable details live in governed task/review docs.
- 2026-04-19 Task 256 inventory and Task 259 authorization-profile slices
  passed docs/skills/handoff/index validation plus `git diff --check`; durable
  details live in the governed task/reference docs.
- 2026-04-19 Review 06 ADR-0009 readiness review denied acceptance until its
  identity-profile blockers are resolved.
- 2026-04-19 Review 06 follow-up amended Task 259 and the profile to lock
  HuleEdu-owned service/operator context minting, required field mapping,
  non-browser `session_id` handling, lane restrictions, and proof requirements.
  Closeout validation passed:
  `pdm run docs-validate`;
  `pdm run skills-validate`;
  `pdm run handoff-validate`;
  `pdm run index-tasks --root docs/backlog --out /tmp/sir_tasks_index_review06_followup.md --fail-on-missing`;
  `git diff --check`.
- 2026-04-19 Review 06 re-review kept ADR-0009 denied because the profile's
  top-level `sir_convert_*` context fields are outside the HuleEdu v1 schema.
- 2026-04-19 Review 06 schema follow-up removed undeclared top-level Sir fields
  from the profile and mapped those semantics through allowed HuleEdu v1
  fields. Closeout validation passed docs/skills/handoff/index and
  `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
