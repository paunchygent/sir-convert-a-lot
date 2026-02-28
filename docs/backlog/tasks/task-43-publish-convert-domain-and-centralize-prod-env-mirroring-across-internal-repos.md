---
id: 'task-43-publish-convert-domain-and-centralize-prod-env-mirroring-across-internal-repos'
title: 'Publish convert.hule.education and centralize prod env mirroring across internal repos'
type: 'task'
status: 'done'
priority: 'high'
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - domaingateway
  - hemmasecrets
  - docs-governance
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Publish Sir Convert-a-Lot on the canonical public domain `convert.hule.education`,
remove superseded operator guidance (local-only lanes), and enforce centralized
Hemma production `.env` mirroring across:

- `~/apps/sir-convert-a-lot`
- `~/apps/huleedu`
- `~/apps/skriptoteket`
- `~/apps/projektveckor-portal`

## PR Scope

1. Domain and ingress

- Ensure Sir Convert-a-Lot `prod` container is proxy-addressable via:
  - `VIRTUAL_HOST=convert.hule.education`
  - `VIRTUAL_PORT=8085`
  - `LETSENCRYPT_HOST=convert.hule.education`
- Ensure persistent network attachment to `hule-network` through compose config.

2. Hemma production env mirroring + symlink policy

- Create and enforce canonical secret root:
  - `~/infrastructure/env/prod/`
- Mirror full project-specific prod `.env` payloads into canonical files under that root.
- Replace repo-local prod `.env` files with symlinks to canonical env files.
- Ensure Sir Convert-a-Lot key is mirrored into all prod env bundles:
  - `SIR_CONVERT_A_LOT_API_KEY` in Sir/HuleEdu/Skriptoteket envs
  - `PVP_SIR_CONVERT_A_LOT_API_KEY` in Projektveckor env (same secret value)

3. Docs and skills governance cleanup

- Update all Sir Convert-a-Lot runbooks/skills to allow only:
  - Tunnel lane (`http://127.0.0.1:28085`)
  - Internet lane (`https://convert.hule.education`)
- Remove or mark superseded guidance for local/legacy client lanes (for example `18085`).

## Deliverables

- [x] `compose.yaml` updated for public domain routing + proxy network persistence.
- [x] Hemma env mirror root created and permission-hardened (`700` root dirs, `600` files).
- [x] Symlinked `.env` files established for all four repos.
- [x] Sir API key synchronized across repo prod env bundles.
- [x] Runbooks/skills updated to tunnel-or-internet-only client guidance.
- [x] Validation evidence captured (domain readyz + authenticated API probe).

## Acceptance Criteria

- [x] `dig +short convert.hule.education` resolves to Hemma public IP.
- [x] `https://convert.hule.education/readyz` returns ready payload.
- [x] Authenticated `GET /v1/convert/jobs/{job_id}` returns contract-valid response.
- [x] `~/apps/*/.env` for Sir/HuleEdu/Skriptoteket/Projektveckor are symlinks into
  `~/infrastructure/env/prod/`.
- [x] Each canonical env file contains full project payload + synchronized Sir key fields.
- [x] No active runbook/skill in Sir repo suggests superseded local client lanes.

## Validation Evidence (2026-02-28)

- `dig +short convert.hule.education A @1.1.1.1` returned `83.252.61.217`.
- `curl --resolve convert.hule.education:443:83.252.61.217 https://convert.hule.education/readyz`
  returned `200` with `{"status":"ready","ready":true,...}` payload.
- Auth probe via ingress returned contract-valid not-found:
  `curl --resolve convert.hule.education:443:83.252.61.217 -H "X-API-Key: $key" https://convert.hule.education/v1/convert/jobs/00000000-0000-0000-0000-000000000000`
  returned `404` with `error.code="job_not_found"`.
- Symlink checks on Hemma confirmed:
  - `~/apps/sir-convert-a-lot/.env -> ~/infrastructure/env/prod/sir-convert-a-lot.env`
  - `~/apps/huleedu/.env -> ~/infrastructure/env/prod/huleedu.env`
  - `~/apps/skriptoteket/.env -> ~/infrastructure/env/prod/skriptoteket.env`
  - `~/apps/projektveckor-portal/.env -> ~/infrastructure/env/prod/projektveckor-portal.env`
- Canonical env file permissions verified as `600` and required key presence checks passed:
  - `SIR_CONVERT_A_LOT_API_KEY` present in Sir/HuleEdu/Skriptoteket env files.
  - `PVP_SIR_CONVERT_A_LOT_API_KEY` present in Projektveckor env file.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
