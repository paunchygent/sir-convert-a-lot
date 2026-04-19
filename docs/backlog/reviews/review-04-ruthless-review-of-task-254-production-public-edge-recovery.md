---
id: review-04-ruthless-review-of-task-254-production-public-edge-recovery
title: Ruthless review of Task 254 production public edge recovery
type: review
status: completed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
  - docs/backlog/tasks/task-43-publish-convert-domain-and-centralize-prod-env-mirroring-across-internal-repos.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/devops/dev-compose.sh
  - scripts/devops/prod-compose.sh
  - scripts/devops/compose-actions.sh
  - scripts/devops/hemma-public-edge-default-host-remediate.sh
  - scripts/sir_convert_a_lot/devops/hemma_deploy_and_verify.py
  - scripts/sir_convert_a_lot/devops/hemma_deploy_report.py
  - scripts/sir_convert_a_lot/devops/public_edge_verification.py
  - tests/sir_convert_a_lot/test_dev_compose_wrapper.py
  - tests/sir_convert_a_lot/test_local_compose_contract.py
  - tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py
  - tests/sir_convert_a_lot/test_public_edge_verification.py
  - tests/sir_convert_a_lot/test_hemma_detached_command_surface.py
labels:
  - review
  - hemma
  - devops
  - public-edge
  - task-254
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Reviewed as a planning and readiness review for
  `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- No implementation branch was present. The worktree was on `main` with
  `task-254` as an untracked proposed task document.
- Public surfaces under review:
  - Hemma deploy/recreate command surfaces in `pyproject.toml`,
    `scripts/devops/dev-compose.sh`, and
    `scripts/sir_convert_a_lot/devops/hemma_deploy_and_verify.py`.
  - Production Compose ingress contract in `compose.yaml`.
  - Public HTTPS readiness proof for `https://convert.hule.education/readyz`.
  - Shared nginx-proxy default-host behavior when no product vhost is active.
- Compatibility posture:
  - Clean hardening change. No compatibility shim should preserve the broken
    default-host behavior.
  - `dev-*` local CPU compose behavior must not be silently repurposed as the
    production Hemma surface; add a distinct production surface or rename
    deliberately with docs and tests updated together.
- Validation evidence gathered:
  - `pdm run docs-validate`: pass.
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`: fail, because
    `test_dev_compose_wrapper.py` expects `compose.yaml` while the local
    compose contract requires `compose.local.yaml`.

## Findings

1. `blocker` - Default-host hardening is cross-repo infrastructure work but the
   task gives it no owning implementation surface.

   - Evidence:
     `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`
     lines 54-58 and 100-102 require a fail-closed reserved placeholder for
     unknown hosts, but the task only relates Sir Convert-a-Lot files and does
     not name the `~/infrastructure` compose/config files, an infrastructure
     task, or an ADR that owns nginx-proxy default-host policy.
   - Why it matters:
     An implementer can restart Sir Convert and pass the product host checks
     while the shared edge still falls through to a product app whenever a vhost
     disappears. That leaves the root incident class open.
   - Required fix:
     Split or link an explicit infrastructure-owned task/ADR for the reserved
     default host, or expand Task 254 with the exact infrastructure files,
     compose service name, `DEFAULT_HOST`/nginx-proxy contract, and deployment
     command. Keep product apps out of the default-host role unless a separate
     accepted ADR deliberately rejects the reserved-placeholder design.
   - Proof requirement:
     Add deterministic evidence that an absent or unknown vhost reaches the
     reserved placeholder and not Skriptoteket, HuleEdu, or Sir Convert. Include
     a command that captures the nginx-proxy effective default host plus the
     unknown-host HTTP/TLS response artifact.

1. `high` - The task does not require resolving the current contradictory
   compose command-surface tests.

   - Evidence:
     `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`
     lines 107-109 only require the deploy-and-verify test. The targeted review
     run fails because `tests/sir_convert_a_lot/test_dev_compose_wrapper.py`
     lines 129 and 176 expect `dev-compose.sh` to use `compose.yaml`, while
     `tests/sir_convert_a_lot/test_local_compose_contract.py` line 132 requires
     `dev-compose.sh` to target `compose.local.yaml`.
   - Why it matters:
     Task 254's core fix is separating the production Hemma recreate surface
     from the local CPU dev wrapper. If the task does not force this test
     contract closed, the implementation can either keep deploy recovery broken
     or regress the local compose lane.
   - Required fix:
     Amend Task 254 to require a distinct production compose command surface
     (for example `prod-recreate`/`hemma-prod-recreate`) backed by
     `compose.yaml`, update `hemma-deploy-and-verify` to call that surface, and
     rewrite the wrapper tests so `dev-*` remains local while the new production
     surface is tested separately.
   - Proof requirement:
     Run and record:
     `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_compose_contract.py -q`.

1. `high` - The public-edge proof is ephemeral curl output, not a durable
   deploy-and-verify artifact.

   - Evidence:
     `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`
     lines 86-87 require verification artifacts for public HTTPS readiness, but
     lines 109-111 only list manual `curl` commands. The existing Task 76 report
     shape records host-lane readyz, metrics, and remote HEAD, but not public
     TLS SAN/issuer, public readyz payload, effective `server_name`, or the
     unknown-host placeholder response.
   - Why it matters:
     The incident was specifically public-edge drift. A pasted curl success is
     easy to lose and does not prove that the canonical deploy-and-verify report
     will catch the same regression next time.
   - Required fix:
     Extend `hemma-deploy-and-verify` with a `public_edge` verification section
     and deterministic evidence files, or add a committed companion verifier
     that the deploy-and-verify workflow invokes. Capture at least public
     `/readyz`, certificate subject/SAN/issuer for `convert.hule.education`,
     nginx-proxy `server_name convert.hule.education`, restart policy, and
     unknown-host placeholder response.
   - Proof requirement:
     Add tests for the public-edge report fields and run the live command for
     the pushed revision. The closeout report must include file paths for the
     public evidence, not just command transcripts.

1. `medium` - The unknown-host acceptance test is underspecified for the
   no-DNS-change constraint.

   - Evidence:
     `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`
     lines 65-70 make DNS changes out of scope, while lines 100-102 require an
     unknown or deliberately unowned host reaching Hemma to return the reserved
     placeholder. The validation command for that host is not specified.
   - Why it matters:
     Normal TLS hostname validation cannot succeed for a deliberately unowned
     host unless a valid certificate exists for that name. Without an explicit
     test lane, reviewers cannot distinguish "unknown-host fallback is safe"
     from "curl never reached nginx because TLS/DNS failed first."
   - Required fix:
     Specify the exact unknown-host probe. For example, use public HTTP with a
     temporary `--resolve` to Hemma, or use HTTPS with an explicit exception that
     `--insecure` is allowed only for default-host route-selection proof while
     `convert.hule.education` remains strict TLS.
   - Proof requirement:
     Record the command, response status/body, and the reason the probe proves
     default-host routing rather than DNS or certificate state.

## Decision

approved

## Response

Task 254 remediation addressed the review findings. The governing task now owns
the infrastructure default-host surface, separates `dev-*` from `prod-*`,
defines the unknown-host probe policy, and requires durable public-edge evidence
inside the canonical deploy-and-verify report.

## Follow-up Actions

1. Completed in the addressed Task 254 slice: shared nginx-proxy default-host
   ownership is explicit, compose command-surface tests cover `dev-*` and
   `prod-*`, and the deploy report now includes durable public-edge evidence.
1. No additional review follow-up is required before live Hemma acceptance
   evidence is captured.

## Completion

Initial review completed with changes requested. Re-review approved the
addressed slice on 2026-04-19.

## Re-review Addendum (2026-04-19)

- Finding 1 / default-host owner: addressed. Task 254 now names
  `~/infrastructure/docker-compose.yml`, `nginx-proxy`, the detached
  remediation command, and `hemma-reserved-default-host`.
- Finding 2 / compose split: addressed. `dev-*` stays on `compose.local.yaml`,
  `prod-*` uses `compose.yaml`, and `hemma-deploy-and-verify` calls
  `prod-recreate`.
- Finding 3 / durable public-edge proof: addressed. `hemma-deploy-and-verify`
  now emits public-edge checks and the evidence files
  `public_edge.json`, `public_readyz.json`, `public_tls.json`,
  `nginx_proxy_default.conf`, `nginx_proxy_env.txt`, and
  `unknown_host_response.txt`.
- Finding 4 / unknown-host probe: addressed. Task 254 permits `--insecure`
  only for the deliberately unowned host probe and keeps strict TLS for
  `convert.hule.education`.
- Re-review validation:
  - `pdm run docs-validate`: pass.
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/test_public_edge_verification.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_hemma_detached_command_surface.py -q`: pass, `32 passed`.
  - `pdm run typecheck-all`: pass.
  - `git diff --check`: pass.
  - `pdm run lint`: pass after formatting the pre-existing drift.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
