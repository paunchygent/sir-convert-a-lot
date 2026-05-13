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
  - docs/backlog/tasks/task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover.md
  - docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md
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
| Sir Convert public host | `https://convert.hule.education` was routed by nginx-proxy to the app before Task 265; Task 265 now routes it to `sir_convert_a_lot_public_reserved` | reserved public host | fail-closed reserved/default posture until Gateway live proof | Public job routes must move behind Gateway before any public product lane is re-enabled. Any status page or external M2M surface requires a separate accepted ADR. |
| HuleEdu app/backend consumers | Repo search on 2026-04-19 found no HuleEdu application code calling Sir Convert directly; HuleEdu owns public ingress monitoring and optional host-wide startup references for Sir Convert | monitoring/ops only in inspected HuleEdu repo state | Gateway route owner for future product/browser Sir Convert public lane | HuleEdu Gateway implementation remains required, but no current HuleEdu product caller was found to migrate in this inventory pass. |
| Skriptoteket Conversion Hub | `apps_conversion_hub.py`, `conversion_hub_jobs.py`, and `sir_convert_client_v2.py` submit user-owned conversion jobs to `/v2/convert/jobs`, poll status, and download artifacts; production env defaults to `https://convert.hule.education` with `SIR_CONVERT_A_LOT_V2_API_KEY` | backend call using direct service API key to public URL by default | Gateway/user-originated context with `InternalIdentityContextV1` audience `sir-convert-a-lot`; same-host internal transport can be retained only with verified context-derived ownership | Browser-derived product workload. Must not remain global service-key scoped; local Skriptoteket job owner maps into the Sir authorization profile. |
| Skriptoteket Klassrumskartan class-list PDF import | `class_list_document_extractor.py` falls back to `SirConvertALotClientV2.extract_text_direct` for PDF text extraction after local fast path fails | backend call using shared Sir client settings | Same target as Conversion Hub for user-originated teacher uploads; prefer internal transport plus Gateway-issued context | Teacher/browser-derived backend workload even when submitted from the backend. Needs context propagation and owner/audit mapping. |
| Skriptoteket webhook subscription helpers | `sir_convert_client_v2.py` supports create/list/delete webhook subscription routes; historical seating export docs describe legacy subscription cleanup, while current code no longer shows active seating export submission through Sir Convert | internal/admin helper surface | Sir-profiled service/operator extension, not browser public | Treat as admin/internal migration surface. Must not become a public browser route. |
| Projektveckor Portal document exports | `projektveckor_portal` uses `PVP_SIR_CONVERT_A_LOT_BASE_URL=http://sir_convert_a_lot_prod:8085`, `PVP_SIR_CONVERT_A_LOT_API_KEY`, and `SirConvertALotV2Client` for `POST /v2/convert/jobs`, status, and artifact download | direct Docker-network service API key | preserved direct internal lane with Sir-profiled service context or Gateway-issued context for teacher/user-originated exports | This is an internal Hemma consumer outside the original HuleEdu/Skriptoteket pair and must remain supported or be explicitly migrated. |
| Local operator CLI | Hemma runbook documents tunnel lane `http://127.0.0.1:28085` | local tunnel | preserved local operator lane | Must remain documented after public cutover. |
| `/docs`, `/redoc`, `/openapi.json` | Public-edge evidence captured `200` responses from operator curl probes before Task 265 | former direct public metadata | internal/admin only | Must stay unreachable through direct public host; Task 258 should also gate production app exposure for internal proxy mistakes. |
| `/metrics` | Public-edge evidence captured `200` from operator curl probe before Task 265 | former direct public metadata | internal monitoring only | Public exposure should remain removed; scrape lane must be documented. |
| `/healthz`, `/readyz` | Public-edge evidence captured detailed `200` readiness before Task 265 and reserved `421` after Task 265 | former direct public metadata; now reserved host | internal-only detailed readiness plus fail-closed public host behavior | ADR-0009 does not preserve a public readiness/status surface. A status page or external M2M surface requires a separate accepted ADR. |

## Evidence Snapshot: 2026-04-19 Task 256

Task 256 inspected the Sir Convert, HuleEdu, Skriptoteket, and Projektveckor
Portal repositories plus Hemma nginx-proxy Docker logs.

Durable local artifacts:

- `build/verification/task-256-gateway-cutover-caller-inventory/convert-hule-education-nginx-proxy-24h-redacted.log`
- `build/verification/task-256-gateway-cutover-caller-inventory/public-edge-usage-summary.json`
- `build/verification/task-256-gateway-cutover-caller-inventory/public-edge-usage-summary.md`

Evidence window:

- `2026-04-18T20:00:00Z..2026-04-19T20:42:00Z`, captured from
  `nginx-proxy` Docker logs with `--since 24h`.

Public-edge summary:

| Class | Count | Interpretation |
| --- | ---: | --- |
| Operator curl probes | 25 | Task 254/265 metadata, readiness, reserved-host, and job-route probes. |
| Unknown browser/scanner-like access | 2 | `GET /` before the reserved host was active; no product conversion route was observed. |
| Successful public product conversion flows | 0 | No successful `POST /v2/convert/jobs` or artifact workflow appeared in the public-edge evidence window. |

API-key presence is unavailable from the current nginx-proxy and app log
formats because request headers are not logged. Task 266 owns adding a safe
auth-aware evidence surface that records only API-key presence/absence, never
secret values.

Unknown public consumers are therefore **not fully ruled out**. They are
tracked as a cutover blocker until Task 266 and Task 263 provide a sufficient
pre-cutover evidence window.

## Caller Migration Matrix

| Caller | Workload class | Current routes | Current auth | Target decision | Blocker/follow-up |
| --- | --- | --- | --- | --- | --- |
| HuleEdu public ingress monitor | ops/monitoring | `GET https://convert.hule.education/healthz` | none | Retire or change to reserved-host proof; Gateway product route monitoring must be separate | HuleEdu monitor update in HuleEdu `ST-01-07` or Task 263 handoff. |
| HuleEdu Gateway | future product/browser public entry | `/sir-convert/v2/convert/...` Gateway route family planned by HuleEdu `ST-01-07` | HuleEdu browser session + CSRF | Implement Gateway routes that sign `InternalIdentityContextV1` with audience `sir-convert-a-lot` | `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`. |
| Skriptoteket Conversion Hub | user-originated product/backend | `POST /v2/convert/jobs`, `GET /v2/convert/jobs/{job_id}`, `GET /v2/convert/jobs/{job_id}/artifact` | `SIR_CONVERT_A_LOT_V2_API_KEY` transport key | Preserve local Skriptoteket job ledger, but Sir Convert must receive verified user context and enforce context-derived upstream ownership | Tasks 259, 264, Task 282, and HuleEdu `ST-01-07`. |
| Skriptoteket class-list PDF import | user-originated product/backend | `POST /v2/convert/jobs`, status, artifact via `extract_text_direct` | `SIR_CONVERT_A_LOT_V2_API_KEY` transport key | Same as Conversion Hub; treat backend submission as user-originated teacher work | Tasks 259, 264. |
| Skriptoteket webhook subscription helpers | service/operator administration | `/v2/push/webhooks/subscriptions` create/list/delete | `SIR_CONVERT_A_LOT_V2_API_KEY` | Keep internal/admin only under Sir-profiled service/operator authorization | Task 259. |
| Projektveckor Portal exports | user-originated/internal service | `POST /v2/convert/jobs`, `GET /v2/convert/jobs/{job_id}`, `GET /v2/convert/jobs/{job_id}/artifact` | `PVP_SIR_CONVERT_A_LOT_API_KEY`; Docker-network base URL | Preserve direct internal service lane; add Sir-profiled service/user context before global API-key authorization is retired | Task 259 plus downstream Projektveckor follow-up. |
| Local operator CLI/tunnel | operator/local GPU offload | CLI/job routes via `http://127.0.0.1:28085` tunnel | explicit operator API key today | Preserve; add operator extension to Sir authorization profile and avoid public direct host | Task 261. |
| Anonymous public internet | unknown/direct public | any `convert.hule.education` path | none or unknown | Reserved fail-closed/default response only | Tasks 266 and 263 must rule out or keep blocked. |

## Open Questions

- Should HuleEdu public ingress monitoring remove `convert.hule.education` from
  product-health expectations until the Gateway route exists, or keep a
  reserved-host assertion?
- Does the `/sir-convert/v2/convert/...` Gateway route family from HuleEdu
  `ST-01-07` cover every Skriptoteket Conversion Hub operation, or does
  Skriptoteket also need a HuleEdu-owned delegated identity exchange for
  backend-mediated save-to-user-files work?
- Does any external non-Hule service rely on `convert.hule.education` as a
  machine-to-machine API?
- What evidence window is sufficient after Task 266 adds API-key-presence-safe
  access classification before unknown public consumers can be ruled out?
- Which internal service workflows are truly non-user-originated, and which are
  backend submissions of user-originated jobs?
- Which Prometheus/Grafana scrape path should replace public `/metrics`?

## Migration Decision Log

| Date | Decision | Rationale | Follow-up |
| --- | --- | --- | --- |
| 2026-04-19 | Proposed target is Gateway for public/browser, HuleEdu `InternalIdentityContextV1` audience `sir-convert-a-lot` for user-originated workloads, Sir-profiled non-browser service/operator extensions, and fail-closed reserved direct public host. | Preserves current internal/offload use cases while making job ownership and artifact access enforceable without minting a parallel Sir identity transport. | ADR-0009, Task 256 inventory, and Task 259 identity contract. |
| 2026-04-19 | Treat Skriptoteket Conversion Hub and class-list PDF import as user-originated backend workloads even though the HTTP call to Sir Convert is made by the Skriptoteket backend. | The actor is a signed-in product user and artifacts are user-facing; the backend must not collapse these jobs into global service-key ownership. | Tasks 259, 260, and 264. |
| 2026-04-19 | Treat Projektveckor Portal as a retained internal Hemma consumer that must be included in the authorization profile. | It uses direct Docker-network Sir Convert routes for teacher-facing document exports and is not covered by the HuleEdu/Skriptoteket-only wording. | Task 259 and a downstream Projektveckor follow-up. |
| 2026-04-19 | Unknown public consumers are not fully ruled out by the available 24h nginx-proxy evidence. | The evidence shows no successful public conversion flow, but the log format cannot record API-key presence/absence and the window is short. | Task 266 and Task 263. |
| 2026-04-19 | Sir Convert authorization profile is defined as HuleEdu `InternalIdentityContextV1` plus Sir-specific ownership/grant rules. | Locks the ADR-0009 identity boundary without minting a parallel signed Sir transport. | Task 258 runtime enforcement, Task 282 runtime artifact routes, and HuleEdu `ST-01-07` Gateway route mechanics. |
| 2026-05-13 | The former Task 260 Gateway-route planning lane moved to HuleEdu `ST-01-07`, with Sir Convert Task 282 owning the service-runtime artifact bundle side. | Keeps HuleEdu auth-edge implementation in the repo that owns Gateway while preventing drift from the concrete EPIC-10 artifact-bundle API contract. | `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/stories/story-01-07-expose-sir-convert-artifact-bundle-routes-through-huleedu-auth-edge.md`; `docs/backlog/tasks/task-282-implement-digiexam-migration-service-runtime-artifact-bundle-routes.md`. |

## Validation Checklist

- [x] HuleEdu caller inventory complete.
- [x] Skriptoteket caller inventory complete.
- [ ] Local operator tunnel proof captured.
- [x] Internal service direct-call inventory captured.
- [x] Public unauthenticated deny behavior captured for Task 265 reserved host.
- [ ] Gateway-authenticated product flow proof captured.
- [x] `InternalIdentityContextV1` claims and Sir-specific authorization-profile
  fields captured for every retained internal or operator caller.
- [x] nginx-proxy/access-log evidence captured and redacted.
- [x] Public metadata exposure decision captured.
