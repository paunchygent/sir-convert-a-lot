---
type: adr
id: ADR-SIRCON-0014
title: Retire the direct Sir Convert public hostname
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-15'
status: accepted
deciders:
  - user
links:
  governing: []
---

## Context

On 2026-10-15 the user confirmed that Sir production and
`convert.hule.education` are retired and unused. The shared nginx-proxy default
host still selects the convert product certificate. When other product vhosts
are absent, that default can present the wrong certificate to their clients.

TASK-SIRCON-06-01-04 owns the Sir retirement source. The shared Skill Repository
owns the infrastructure override and its apply/proof surface. Read-only
inspection established that `/home/paunchygent/infrastructure` is untracked and
its compose file contains secrets; the Sir remediation helper is not its owner.

## Decision

Remove the Sir public reserved service, public-domain defaults and verification
dependency. The direct hostname has no supported public conversion or reserved
status service. This replaces ADR-SIRCON-0008's former reservation posture only
for the retired direct hostname; private and Gateway authorization boundaries
remain governed by their existing contracts.

Before removing that vhost or certificate, apply and verify the shared tracked
override selecting the product-independent self-signed `default.crt` and
`default.key` through `CERT_NAME=default`. Unknown SNI must fail closed and must
never present a product certificate. A TLS handshake rejection is also permitted
by the user's contract if the shared owner changes that implementation.

After independent-default proof, remove only the retired Sir public container
and verify its generated vhost disappears. Then clean only the retired domain's
certificate and renewal state after proving no remaining consumer references
it. The user may delete the plain Namecheap CNAME after vhost retirement and
unknown-SNI proof succeed. All live mutations require separate approval through
the parent; source commits do not establish live retirement.

Acceptance uses `approval_protocol: agent-planning:user-closure-gate`.
Approval evidence is the user's 2026-10-15 implementation assignment confirming
retirement, order, ownership and the live approval gate; the retained plan for
TASK-SIRCON-06-01-04 records the closed decision source.

## Non-Decisions

Boot-time recovery, notification delivery and other product references remain
parent-owned incident work. This ADR grants no authority to restart Sir or GPU
workloads, reboot Hemma, or change unrelated certificate material.

## Consequences

- Sir deploy verification uses the selected private lane and no longer requires
  a retired public certificate, hostname or proxy vhost.
- Shared infrastructure is changed through its new tracked owner surface,
  preserving the untracked base and its secrets. The Sir direct-edit helper is
  removed.
- Historical references to public-edge operation remain dated history. Current
  guidance points to this retirement and does not advertise a public lane.
- Live application, certificate cleanup and DNS removal remain pending approval
  and actual host proof.
