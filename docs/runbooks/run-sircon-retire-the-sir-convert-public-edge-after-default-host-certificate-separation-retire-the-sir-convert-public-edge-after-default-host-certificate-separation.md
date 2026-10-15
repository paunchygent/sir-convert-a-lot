---
type: runbook
id: RUN-SIRCON-retire-the-sir-convert-public-edge-after-default-host-certificate-separation
title: Retire the Sir Convert public edge after default-host certificate separation
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-15'
status: active
system: hemma.hule.education
summary: Approval-gated ordered removal of the retired Sir public container, vhost and certificate after shared default-host proof.
---

## Trigger

The parent and user approve live execution of TASK-SIRCON-06-01-04 and
ADR-SIRCON-0014. Source delivery alone does not authorize these commands. The
user confirmed on 2026-10-15 that Sir production and the direct public hostname
are retired and unused.

## Preconditions

- The parent has integrated and published the reviewed source on each owning
  repository's `main`; branches are never pushed. Another session must release
  the canonical Hemma checkout before the parent updates it.
- Hemma access works. At 12:41 UTC on 2026-10-15 two read-only SSH probes
  returned connection refused; those failures do not establish the later host
  state. Recheck access before executing this procedure.
- The Skill Repository owns the tracked override and default-host apply/proof
  surface. `/home/paunchygent/infrastructure` is untracked; preserve its
  secret-bearing compose file and reserved backend config. Do not revive the
  removed Sir direct-edit helper.
- No command may start Sir, GPU or unrelated services. Do not use broad Compose
  reconciliation, `down`, `--remove-orphans` or a reboot for this retirement.

## Steps

1. Apply the shared owner's tracked override and retain its successful proof
   before running the removal commands below. It must set the reserved host's
   `CERT_NAME=default`, keep unknown requests fail-closed, prove unknown SNI
   presents the independent self-signed default (or rejects TLS), and prove
   active product vhosts retain their own certificates. The parent supplies the
   exact shared apply/proof command from that implementation's reviewed head.
   This is a hard prerequisite, not permission to hand-edit the live base.

   The nginx-proxy 1.6
   [certificate selection documentation](https://github.com/nginx-proxy/nginx-proxy/blob/1.6.0/docs/README.md#sni)
   and [template](https://github.com/nginx-proxy/nginx-proxy/blob/1.6.0/nginx.tmpl)
   were checked after the Context7 lookup. Explicit `CERT_NAME=default` uses
   the independent pair as a usable certificate; an implicit missing-cert
   fallback would return 500 instead of the reserved backend's 404.

2. After shared-default proof, remove exactly the retired container. Run from
   this repository's root through its transport; this does not recreate any
   remaining Sir service:

   ```bash
   pdm run run-hemma -- sudo -n docker rm -f sir_convert_a_lot_public_reserved
   pdm run run-hemma -- sudo -n docker exec nginx-proxy nginx -t
   pdm run run-hemma -- sudo -n docker exec nginx-proxy grep -nF convert.hule.education /etc/nginx/conf.d/default.conf
   pdm run run-hemma -- sudo -n docker exec acme-companion grep -nF convert.hule.education /app/letsencrypt_service_data
   ```

   Wait for both proxy and companion Docker event regeneration and observe both
   searches produce no output with exit 1; exit 0 means references remain, and
   exit 2 is an error.
   Rerun the shared proof against the regenerated configuration. Retain strict
   TLS proof for active product hosts and unknown-SNI proof. Do not proceed
   while any generated configuration still refers to the retired hostname or
   certificate.

3. Inspect the certificate's SANs and aliases before cleanup. The following two
   checks were not completed during implementation because SSH refused the
   connection. Require SANs only for the retired hostname and exactly its three
   top-level aliases; stop if another domain shares its material:

   ```bash
   pdm run run-hemma -- sudo -n docker exec nginx-proxy openssl x509 -in /etc/nginx/certs/convert.hule.education.crt -noout -subject -ext subjectAltName
   pdm run run-hemma -- sudo -n docker exec nginx-proxy find /etc/nginx/certs -maxdepth 1 -type l -lname '*convert.hule.education*' -print
   ```

4. Remove the domain from renewal, then delete only its deployed certificate
   directory, its three top-level links and its account-scoped domain state.
   Preserve `default.crt`, `default.key`, account configuration and all other
   domains. Context7 and the installed acme.sh 3.0.7 source confirm that
   [`--remove`](https://github.com/acmesh-official/acme.sh#14-how-to-stop-cert-renewal)
   stops renewal but leaves files on disk:

   ```bash
   pdm run run-hemma -- sudo -n docker exec acme-companion /app/acme.sh --home /app --config-home /etc/acme.sh/admin@hule.education --remove -d convert.hule.education
   pdm run run-hemma -- sudo -n docker exec acme-companion rm -rf -- /etc/nginx/certs/convert.hule.education /etc/nginx/certs/convert.hule.education.crt /etc/nginx/certs/convert.hule.education.key /etc/nginx/certs/convert.hule.education.chain.pem /etc/acme.sh/admin@hule.education/convert.hule.education
   pdm run run-hemma -- sudo -n docker exec nginx-proxy nginx -t
   pdm run run-hemma -- sudo -n docker exec nginx-proxy nginx -s reload
   pdm run run-hemma -- sudo -n docker exec nginx-proxy find /etc/nginx/certs -maxdepth 1 -name '*convert.hule.education*' -print
   pdm run run-hemma -- sudo -n docker exec acme-companion find /etc/acme.sh -maxdepth 3 -iname '*convert.hule.education*' -print
   ```

   Both final searches must be empty. Inspect fresh rendered config and rerun
   the shared proof after reload. Stop if any product loses strict TLS or the
   default begins presenting a product certificate. No revocation, forced
   renewal or unrelated ACME account change is part of this procedure.

5. After successful vhost-removal and unknown-SNI proof, the user may delete
   the plain `convert` CNAME at Namecheap. The sequence above completes the
   certificate cleanup before the final DNS handback. DNS deletion is manual
   and user-owned; the record is not managed by ddclient.

## Expected Results

- No retired Sir public container, generated convert vhost, deployed certificate
  or per-domain renewal state remains. Sir production and GPU services remain
  stopped.
- Unknown SNI presents no product certificate and unknown requests fail closed;
  active product vhosts retain strict TLS. Retain actual post-change proof,
  not a local test or source-only assertion.

## Stop Conditions

- Missing user approval, unavailable shared apply/proof source, or a failed
  independent-default proof.
- Unreleased/dirty owner checkout, unavailable SSH, stale rendered config,
  shared certificate SAN/alias, or any command requiring broad service changes.
- Unexpected ACME layout or renewal removal result; preserve domain/account
  state and return the observed failure to the parent.

## Rollback

If a check fails before container removal, leave the convert container and
certificate in place and return the failure to the shared owner. After removal,
keep the product-independent default and repair through the owning source;
do not restore the old product-certificate default. Certificate cleanup deletes
the retired domain's material, so restoring that domain would require separate
user authority and preserved owner backups or fresh issuance. It is not an
automatic rollback. This procedure never reboots Hemma or starts Sir.
