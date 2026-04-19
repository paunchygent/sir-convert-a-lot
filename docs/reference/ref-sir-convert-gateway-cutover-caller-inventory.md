---
type: reference
id: REF-sir-convert-gateway-cutover-caller-inventory
title: Sir Convert Gateway Cutover Caller Inventory
status: active
created: 2026-04-19
updated: 2026-04-19
owners:
  - platform
tags:
  - gateway
  - inventory
  - migration
  - access-lanes
  - huledu
  - skriptoteket
  - hemma
links:
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/tasks/task-256-inventory-sir-convert-callers-and-access-lanes-before-gateway-cutover.md
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/internal_adapter_contract_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
---

## Purpose

Store migration-relevant facts for deciding and executing the Sir Convert
gateway cutover. This document is the working inventory for current callers,
transport lanes, credentials, route usage, proof gaps, and migration decisions.

The inventory task must update this reference before any public access lane is
removed or repointed.

## Target Access Lanes

| Lane | Caller class | Target posture | Notes |
| --- | --- | --- | --- |
| Product/browser | HuleEdu and Skriptoteket browser flows | Gateway-only | Gateway owns session, CSRF, roles, entitlement, and public audit. |
| Backend internal | Hemma services and sanctioned backend jobs | Direct internal service allowed with HuleEdu `InternalIdentityContextV1` for user-originated work and a Sir-profiled service extension for non-browser service workflows | User-originated backend jobs must carry Gateway-issued `InternalIdentityContextV1` with audience `sir-convert-a-lot`. |
| Local operator | Local CLI/devops using Hemma tunnel | Preserved with Sir-profiled operator extension to the internal identity contract | Used for heavy GPU-backed conversion offload and debugging. |
| Direct public | Anonymous internet callers to `convert.hule.education` | Reserved fail-closed/default posture | Status page or external M2M API requires a separate accepted ADR. |

## Inventory Fields

Each caller entry should capture:

- caller name and repository;
- owner;
- current entry URL or network lane;
- routes used;
- auth mechanism and secret source;
- whether the request is browser-derived, backend-internal, or operator-local;
- whether the workload is user-originated even if submitted by a backend
  worker;
- required `InternalIdentityContextV1` claims and Sir-specific
  authorization-profile fields for that caller;
- data sensitivity and expected artifact retention;
- conversion workload shape and GPU expectation;
- current validation or smoke command;
- target post-cutover lane;
- migration decision;
- blockers and follow-up tasks.

## Known Current Facts

| Caller or surface | Current evidence | Current lane | Target lane | Migration note |
| --- | --- | --- | --- | --- |
| Sir Convert public host | `https://convert.hule.education` is live and routed by nginx-proxy | direct public | fail-closed reserved/default posture | Public job routes should move behind Gateway before direct public exposure is removed. Any status page or external M2M surface requires a separate accepted ADR. |
| HuleEdu backend/service consumers | Downstream integration docs and env mirror reference shared `SIR_CONVERT_A_LOT_V2_API_KEY` | direct service API key | Gateway for browser-derived requests with `InternalIdentityContextV1`; internal direct for non-browser backend workflows | Needs exact code-path inventory in HuleEdu. |
| Skriptoteket consumers | Downstream integration docs and env mirror reference shared `SIR_CONVERT_A_LOT_V2_API_KEY` | direct service API key | Gateway for browser-derived requests with `InternalIdentityContextV1`; internal direct for non-browser backend workflows | Needs exact code-path inventory in Skriptoteket. |
| Local operator CLI | Hemma runbook documents tunnel lane `http://127.0.0.1:28085` | local tunnel | preserved local operator lane | Must remain documented after public cutover. |
| `/docs`, `/redoc`, `/openapi.json` | Live probe returned `200` without auth on 2026-04-19 | direct public metadata | internal/admin only | Must be disabled or gated in production. |
| `/metrics` | Live probe returned `200` without auth on 2026-04-19 | direct public metadata | internal monitoring only | Public exposure should be removed; scrape lane must be documented. |
| `/healthz`, `/readyz` | Live probe returned detailed revision/profile/data-root metadata on 2026-04-19 | direct public metadata | internal-only detailed readiness plus fail-closed public host behavior | ADR-0009 does not preserve a public readiness/status surface. A status page or external M2M surface requires a separate accepted ADR. |

## Open Questions

- Which HuleEdu routes currently call Sir Convert directly, and are they
  browser-derived or backend workflows?
- Which Skriptoteket routes currently call Sir Convert directly, and are they
  browser-derived or backend workflows?
- Does any external non-Hule service rely on `convert.hule.education` as a
  machine-to-machine API?
- What evidence window is sufficient for nginx-proxy/access-log classification
  before unknown public consumers can be ruled out?
- Which internal service workflows are truly non-user-originated, and which are
  backend submissions of user-originated jobs?
- Which Prometheus/Grafana scrape path should replace public `/metrics`?

## Migration Decision Log

| Date | Decision | Rationale | Follow-up |
| --- | --- | --- | --- |
| 2026-04-19 | Proposed target is Gateway for public/browser, HuleEdu `InternalIdentityContextV1` audience `sir-convert-a-lot` for user-originated workloads, Sir-profiled non-browser service/operator extensions, and fail-closed reserved direct public host. | Preserves current internal/offload use cases while making job ownership and artifact access enforceable without minting a parallel Sir identity transport. | ADR-0009, Task 256 inventory, and Task 259 identity contract. |

## Validation Checklist

- [ ] HuleEdu caller inventory complete.
- [ ] Skriptoteket caller inventory complete.
- [ ] Local operator tunnel proof captured.
- [ ] Internal service direct-call proof captured.
- [ ] Public unauthenticated deny behavior captured.
- [ ] Gateway-authenticated product flow proof captured.
- [ ] `InternalIdentityContextV1` claims and Sir-specific authorization-profile
  fields captured for every retained internal or operator caller.
- [ ] nginx-proxy/access-log evidence captured and redacted.
- [ ] Public metadata exposure decision captured.
