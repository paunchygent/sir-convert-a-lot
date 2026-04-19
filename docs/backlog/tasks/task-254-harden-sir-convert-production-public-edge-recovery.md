---
id: task-254-harden-sir-convert-production-public-edge-recovery
title: Harden Sir Convert production public edge recovery
type: task
status: in_progress
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-43-publish-convert-domain-and-centralize-prod-env-mirroring-across-internal-repos.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - compose.yaml
  - pyproject.toml
  - scripts/devops/prod-compose.sh
  - scripts/devops/dev-compose.sh
  - scripts/devops/compose-actions.sh
  - scripts/sir_convert_a_lot/devops/hemma_deploy_and_verify.py
  - docs/backlog/reviews/review-04-ruthless-review-of-task-254-production-public-edge-recovery.md
  - ~/infrastructure/docker-compose.yml
  - /etc/nginx/conf.d/default.conf
labels:
  - hemma
  - devops
  - public-edge
  - recovery
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Permanently remediate the `convert.hule.education` public-edge drift found on
2026-04-19: DNS reaches Hemma and a valid `convert.hule.education` certificate
exists, but the stopped stale `sir_convert_a_lot_prod` container leaves
`nginx-proxy` without an active `VIRTUAL_HOST=convert.hule.education` vhost, so
the proxy falls back to the Skriptoteket default certificate.

The fix must make production recovery repeatable through committed Sir
Convert-a-Lot command surfaces, then prove both the internal host lane and the
public HTTPS lane.

The shared public edge must fail closed when a product/service vhost is absent.
The preferred permanent posture is a deliberately reserved placeholder default
host/container that returns a minimal non-product response for unknown hosts.
Do not use HuleEdu, Skriptoteket, Sir Convert-a-Lot, or any other product app as
the nginx-proxy default host unless a future ADR explicitly accepts that
unknown hosts may render that product.

## PR Scope

- Add or correct an explicit production compose command surface for Hemma:
  `pdm run prod-*` must use `scripts/devops/prod-compose.sh`, `compose.yaml`,
  and target `sir_convert_a_lot_prod`.
- Keep `pdm run dev-*` local-only: `scripts/devops/dev-compose.sh` must use
  `compose.local.yaml` and target `sir_convert_a_lot_dev` for laptop CPU debug.
- Update the Task 76 deploy-and-verify workflow so production recreate uses the
  production compose surface (`pdm run prod-recreate sir_convert_a_lot_prod`)
  rather than the local `compose.local.yaml` dev wrapper.
- Launch long-running Hemma production recreate commands through the detached
  command surface (`pdm run run-local-pdm hemma-command-start ...`) and monitor
  the remote log separately.
- Launch shared public-edge infrastructure reconciles through the same detached
  command surface; do not run `~/infrastructure` compose deploys attached.
- Recreate the Hemma production container through the corrected surface so the
  live Docker restart policy matches `compose.yaml` (`unless-stopped`).
- Extend verification to prove `https://convert.hule.education/readyz` with
  normal TLS hostname validation, in addition to the existing host lane.
- Own the shared nginx-proxy default-host hardening through the Hemma
  infrastructure surface:
  - remote root: `~/infrastructure`
  - compose/config owner: `~/infrastructure/docker-compose.yml`
  - proxy container: `nginx-proxy`
  - effective config proof:
    `sudo docker exec nginx-proxy sed -n '1,260p' /etc/nginx/conf.d/default.conf`
  - deployment command:
    `pdm run run-local-pdm hemma-command-start public-edge-default-host -- bash scripts/devops/hemma-public-edge-default-host-remediate.sh --deploy`
- Implement or link the preferred fail-closed default-host posture in that
  surface: a deliberately named `hemma-reserved-default-host` placeholder
  container on `hule-network`, with `DEFAULT_HOST` on `nginx-proxy` pointing to
  that reserved host and returning a minimal non-product 404/421-style
  response for unknown hosts.
- Keep product apps out of the default-host role. HuleEdu must not become the
  default host as a workaround unless a separate accepted ADR documents that
  tradeoff and rejects the reserved-placeholder approach.
- Update the Hemma runbook if the canonical production recovery command or
  public-edge proof changes.

Out of scope:

- changing Namecheap records for `convert.hule.education`;
- manually installing replacement certificates outside the nginx-proxy/acme
  companion flow;
- making HuleEdu the nginx-proxy default host as a fallback for unknown hosts;
- changing Sir Convert API behavior or conversion contracts.

## Deliverables

- [x] A committed production compose/recreate command surface exists and uses
  `compose.yaml` (`pdm run prod-recreate sir_convert_a_lot_prod`).
- [x] A committed detached Hemma command surface exists for long-running
  production deploy commands.
- [x] `hemma-deploy-and-verify` recreates `sir_convert_a_lot_prod` through the
  production command surface.
- [ ] The live Hemma `sir_convert_a_lot_prod` container runs with restart policy
  `unless-stopped`.
- [ ] The public nginx-proxy config registers `server_name convert.hule.education`
  while the service is running.
- [ ] The shared nginx-proxy default host is fail-closed through a reserved
  placeholder owned by `~/infrastructure/docker-compose.yml` rather than
  Skriptoteket, HuleEdu, Sir Convert-a-Lot, or another product app.
- [ ] Verification artifacts prove internal `/readyz`, public HTTPS `/readyz`,
  public TLS certificate validity, nginx-proxy public-host ownership,
  reserved default-host behavior, revision parity, and metrics safety.

## Acceptance Criteria

- [ ] `pdm run run-hemma -- pdm run prod-ps -a` reports
  `sir_convert_a_lot_prod` as running or healthy.
- [ ] `pdm run run-hemma -- sudo docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' sir_convert_a_lot_prod`
  returns `unless-stopped`.
- [ ] `curl -fsS https://convert.hule.education/readyz` succeeds without
  `--insecure` or `--resolve`.
- [ ] `curl -Iv https://convert.hule.education/readyz` shows a certificate
  subject/SAN valid for `convert.hule.education`, not the Skriptoteket
  fallback certificate.
- [ ] An unknown or deliberately unowned host reaching Hemma returns the
  reserved placeholder response instead of routing to Skriptoteket, HuleEdu,
  or Sir Convert-a-Lot.
- [ ] `pdm run run-hemma -- sudo docker exec nginx-proxy sed -n '1,260p' /etc/nginx/conf.d/default.conf`
  shows `server_name convert.hule.education` for Sir Convert and shows the
  `DEFAULT_HOST`/default upstream targeting `hemma-reserved-default-host`,
  not a product app.
- [ ] The canonical deploy-and-verify report passes for the pushed revision.

Unknown-host probe policy:

- Use strict TLS only for `convert.hule.education`.
- For default-host route-selection proof, use an explicit deliberately unowned
  host with `--resolve` to Hemma and allow `--insecure` only because that host
  is not expected to have a valid certificate. The proof must record status,
  response body, and the nginx-proxy upstream/default-host config that explains
  the route.

## Validation Commands

- `pdm run docs-validate`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/test_public_edge_verification.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_compose_contract.py -q`
- `pdm run run-local-pdm hemma-command-start sir-prod-recreate -- sudo -n /home/paunchygent/.local/bin/pdm run prod-recreate sir_convert_a_lot_prod`
- `pdm run run-local-pdm hemma-command-monitor -- <remote-log-path>`
- `pdm run run-local-pdm hemma-command-start public-edge-default-host -- bash scripts/devops/hemma-public-edge-default-host-remediate.sh --deploy`
- `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`
- `curl -fsS https://convert.hule.education/readyz`
- `curl -Iv https://convert.hule.education/readyz`
- `curl --resolve sir-convert-unowned-edge-proof.hule.education:443:<hemma-public-ip> --insecure -isS https://sir-convert-unowned-edge-proof.hule.education/`
- `pdm run run-hemma -- sudo docker exec nginx-proxy sed -n '1,260p' /etc/nginx/conf.d/default.conf`
- `git diff --check`

Canonical deploy-and-verify evidence files:

- `report.json` / `report.md`: overall gate status and public-edge check flags.
- `readyz.json`: canonical host-lane `/readyz` payload.
- `metrics.prom`: canonical metrics safety scan input.
- `remote_head.txt`: deployed Hemma repo revision.
- `public_edge.json`: structured public-edge proof summary.
- `public_readyz.json`: strict-TLS `https://convert.hule.education/readyz`
  payload.
- `public_tls.json`: validated `convert.hule.education` certificate summary.
- `nginx_proxy_default.conf`: rendered nginx-proxy config containing
  `server_name convert.hule.education`.
- `nginx_proxy_env.txt`: nginx-proxy environment containing
  `DEFAULT_HOST=hemma-reserved-default-host`.
- `unknown_host_response.txt`: unowned-host reserved placeholder response.

## Review Acceptance

The ruthless review for the Task 254 implementation slice was accepted on
2026-04-19 in
`docs/backlog/reviews/review-04-ruthless-review-of-task-254-production-public-edge-recovery.md`.
The acceptance covers the docs/code contract for the production compose split,
public-edge durable evidence, default-host ownership, and unknown-host probe
policy. Live Hemma acceptance criteria remain unchecked until the recorded
remote/public verification artifacts are captured.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
