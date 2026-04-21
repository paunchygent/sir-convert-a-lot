---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-04-19'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes.md
  - docs/backlog/tasks/task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes.md
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/tasks/task-259-define-sir-convert-internal-caller-identity-contract.md
  - docs/backlog/tasks/task-265-disable-direct-sir-convert-public-app-route-before-gateway-cutover.md
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
  - devops
  - hemma
---

## Context

The active implementation context for this session is the Epic 03 / Story 05
DevOps lane for the Hemma-hosted Sir Convert-a-Lot service.

Current governing spine:

- Programme 01: Sir Convert-a-Lot platform foundation.
- Epic 03: Unified conversion service.
- Story 05: Dockerized service hardening with robust persistence.
- Task 254: Production public-edge recovery and detached deploy verification.
- Task 255: Service dependency image extraction from overloaded
  `pyproject.toml` cache keys.
- Epic 09: Gateway cutover and internal access contract for Sir Convert-a-Lot.
- Task 265: Pre-cutover direct public app-route isolation for
  `convert.hule.education`.
- Task 256: Caller/access-lane inventory for the Sir Convert Gateway cutover.
- Task 259: Sir Convert `InternalIdentityContextV1` authorization profile.

Task 254 remains the immediate production recovery authority. It owns the
detached Hemma deploy/public-edge proof, reserved default-host behavior, and the
canonical `hemma-deploy-and-verify` report evidence.

Task 255 is now the completed build architecture slice. It owns the dependency
image split, narrow dependency input artifacts, BuildKit pip cache mounts, and
the proof that PDM script-only changes no longer invalidate ROCm torch,
EasyOCR preload, or other heavy dependency work.

Epic 09 is the proposed access-architecture cutover. It owns the ADR-backed
migration from direct public product access on `convert.hule.education` to
HuleEdu Gateway-fronted product/browser access while preserving direct internal
Hemma service use and local operator GPU-offload tunnel workflows.

Task 239 is retained as the earlier completed partial layering slice. It
narrowed app-source/context invalidation, but Task 255 owns the unresolved
`pyproject.toml` dependency-cache boundary.

The Qwen Task 101 lane is not the active implementation lane for this session.
Its durable status remains in:

- `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
- Epic 08 and Story 31/32 backlog docs.
- The Qwen runbook and RULE-095/RULE-096.

The Task 242 Hemma Docker bind-root contract remains operational background
for Qwen runtimes only. Use its `status` and `probe` surfaces before future
Qwen Docker work, but do not let Qwen governance override the current Story 05
DevOps task authority.

## Worklog

- 2026-03-18:
  - Qwen Story 31/32 mechanism work and Task 242 bind-root governance were the
    prior active lane. The detailed task-by-task ledger was compressed into the
    Qwen reference, story docs, and runbooks.
- 2026-04-19:
  - Task 254 became the active production recovery slice after public-edge drift
    on `convert.hule.education`.
  - Production/dev compose ownership was split: `prod-*` uses `compose.yaml`
    and `sir_convert_a_lot_prod`; `dev-*` uses `compose.local.yaml` and
    `sir_convert_a_lot_dev`.
  - Long-running Hemma production deploys and shared public-edge remediation
    were reaffirmed as detached-command workflows.
  - Review feedback identified the remaining durable proof gap: the canonical
    deploy verifier must emit public HTTPS and default-host artifacts, not rely
    on manual curl evidence only.
  - A build-time RCA found that full `pyproject.toml` still invalidates the
    heavy dependency-builder chain, including ROCm torch and EasyOCR preload.
  - Story 05 was promoted as the active DevOps story under Epic 03, and Task
    255 was created as the explicit dependency-image/cache-key follow-up.
  - Task 255 implementation extracted hash-addressed ROCm/CPU dependency image
    lanes, generated narrow `docker/service-deps/` inputs, switched
    production/local runtime Dockerfiles to explicit `DEPS_IMAGE`, and added
    contract tests for PDM script-only non-invalidation.
  - Task 255 was committed and pushed to `main`, deployed into the canonical
    Hemma repo, and verified through detached dependency-build, app-only-build,
    and production-recreate proof logs. The proof artifacts live under
    `build/verification/task-255-service-deps-image-cache/`.
  - Review 05 requested one Task 255 fix: dependency-image freshness must
    include build-recipe truth. The follow-up adds recipe hashing, combined
    dependency-image identity, and Docker label verification before accepting
    existing dependency image tags.
  - The Review 05 Task 255 follow-up was committed, pushed, pulled on Hemma,
    and verified through detached recipe-aware dependency warm-up, app-only
    build, and production recreate proof from commit
    `d23855375ec848a8c45ae40d43e23c4f8b23d319`.
  - ADR-0009, Epic 09, Stories 33-37, Tasks 256-264, and
    `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md` were
    created as the planning spine for the Gateway cutover. The inventory
    reference is the durable place for migration-relevant caller/access-lane
    facts before any public route is removed or repointed.
  - Review feedback on ADR-0009 tightened the cutover boundary: Sir Convert
    must consume HuleEdu `InternalIdentityContextV1` with audience
    `sir-convert-a-lot` instead of minting a parallel identity contract, Task
    259 is a hard prerequisite for ADR acceptance, user-originated backend jobs
    must carry context-derived ownership, unknown public consumers require
    empirical public-edge evidence, and the direct public host defaults to
    fail-closed reserved posture.
  - Third-pass review approved the Epic 09 planning spine. ADR-0009 remains
    proposed until Task 259 locks the Sir-specific `InternalIdentityContextV1`
    authorization profile and proves non-browser service/operator extensions
    do not introduce a second signed issuer or browser-adjacent auth path.
  - Task 265 started the pre-cutover public-edge isolation implementation:
    `sir_convert_a_lot_prod` no longer advertises `convert.hule.education`
    directly, and the production compose/public-edge proof now routes the
    hostname to a reserved non-product response.
  - Task 265 was completed, pushed, pulled on Hemma, and redeployed from
    commit `f6eebfecd2cee273699e5b656ac49f7fb26cd248`. Live proof showed
    `sir_convert_a_lot_prod` healthy on the internal/tunnel lane,
    `sir_convert_a_lot_public_reserved` owning `convert.hule.education`, and
    public `/readyz` returning the reserved `421` response.
  - Task 256 completed the caller/access-lane inventory. HuleEdu currently has
    ops/monitoring references but no direct app caller found; Skriptoteket has
    user-originated backend callers in Conversion Hub and Klassrumskartan
    class-list PDF import; Projektveckor Portal is a retained internal Hemma
    caller; local operator tunnel/offload remains required.
  - Task 266 was created as the follow-up for auth-aware public-edge evidence.
    The 24h nginx-proxy evidence did not show a successful public conversion
    workflow, but unknown public consumers are not fully ruled out because
    current logs cannot classify API-key presence.
  - Task 259 completed the Sir Convert `InternalIdentityContextV1`
    authorization profile. The profile consumes the HuleEdu signed downstream
    identity contract with audience `sir-convert-a-lot`, defines
    context-derived ownership for jobs/artifacts, keeps `X-API-Key`
    transport-only during migration, and names implementation tests for
    spoofed headers, wrong audience, invalid signatures, cross-owner reads,
    service contexts, and operator contexts.
  - Review 06 denied ADR-0009 acceptance. The profile still needs to lock who
    mints non-browser service/operator contexts and how those contexts satisfy
    HuleEdu's mandatory `InternalIdentityContextV1` fields without inventing a
    parallel signer or browser-adjacent operator path.
  - Review 06 follow-up amended Task 259 and the authorization profile:
    service/operator contexts must be minted only by a HuleEdu-owned
    Gateway/internal identity authority using the canonical HuleEdu signing key
    set and `iss == "api_gateway_service"`. Sir Convert, service callers, and
    operator CLI tooling must not sign contexts. Non-browser contexts now have
    explicit signed field mappings, nonblank non-browser `session_id` handles,
    lane restrictions, and audit semantics.
  - Review 06 re-review kept ADR-0009 denied. The remaining blocker is schema
    compatibility: the profile adds top-level `sir_convert_*` fields to
    `InternalIdentityContextV1`, but the upstream HuleEdu v1 model forbids extra
    fields.
  - Review 06 schema follow-up amended the profile to keep the top-level
    payload valid under HuleEdu `InternalIdentityContextV1` v1. Sir Convert now
    derives context kind from `sub` and `roles`, registered caller from
    `source_app`, and workload purpose from route/grants with optional
    narrowing through signed `active_context`; unknown top-level
    `sir_convert_*` fields must fail closed.
  - Review 06 second re-review approved ADR-0009 acceptance readiness. ADR-0009
    remains proposed until Task 257 performs the explicit acceptance update.

## Next Actions

- Continue Epic 09 with Task 257: accept ADR-0009 now that Review 06 is closed
  and the Task 256/259 prerequisites are complete.
- Then move into Task 258/260 implementation planning: runtime enforcement,
  metadata hardening, Gateway route mechanics, and route tests must prove the
  profile rather than merely referencing it.
- Keep Task 266 in the cutover gate before Task 263 final proof: add
  auth-aware redacted public-edge evidence that records API-key presence only
  as `present`, `absent`, or `unavailable`.
- Keep Task 254's deploy verifier follow-up available for future public-edge
  proof hardening, but do not let it reopen the already deployed Task 265
  reserved-host posture.
- Keep Task 239 closed as historical partial layering context. Do not reopen it
  for the dependency-image work unless Task 255 explicitly supersedes or amends
  a documented Task 239 acceptance boundary.
- Preserve the Qwen lane without active edits unless the user explicitly
  returns to Epic 08 / Story 31 work.
