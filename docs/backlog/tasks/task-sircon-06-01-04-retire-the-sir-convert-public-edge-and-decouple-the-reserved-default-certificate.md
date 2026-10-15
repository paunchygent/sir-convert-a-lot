---
type: task
id: TASK-SIRCON-06-01-04
title: Retire the Sir Convert public edge and decouple the reserved default certificate
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Sir Compose and operator verification no longer publish or require the retired public hostname.
  - The shared reserved default host uses no product certificate before the Sir public container and certificate are removed.
  - Live mutation remains approval-gated with exact ordered commands and cross-repo references reported.
story: ST-SIRCON-06-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Retire `convert.hule.education`, confirmed unused and retired by the user on
2026-10-15. Remove the Sir reserved-public service, its nginx configuration,
public-domain defaults, verification artifacts and checks, CLI advice, workload
declaration and current operating guidance. Preserve dated historical evidence.

First separate the shared `hemma-reserved-default-host` TLS identity from all
product certificates. Discover `/home/paunchygent/infrastructure` ownership
read-only and make its durable change in the owning Git source. Use the
nginx-proxy 1.6 default self-signed certificate or reject unknown-SNI TLS
handshakes. The reserved HTTP route continues to fail closed. Remove the old
Sir helper's ability to rewrite shared infrastructure directly.

Prepare exact ordered host commands: install and prove the independent default,
remove only the retired Sir public container/vhost, then remove only the retired
certificate and renewal material after verifying no remaining references.
The parent obtains user approval before any live mutation. CNAME deletion is
user-owned and follows successful vhost removal and fail-closed unknown-SNI proof.
Skriptoteket and HuleEduOS references are inventoried without modification.

The parent owns boot recovery, hostwide gates, alerts and other repositories.
This task does not start Sir, touch GPUs, mutate the canonical Hemma checkout,
reboot Hemma, or perform live deployment. The deploy helper consumes previously
published source and must not automatically push an arbitrary branch.

## Contract Inputs

- User assignment and verified incident report of 2026-10-15, including the
  explicit retirement, ordered certificate transition and live approval gate.
- ADR-SIRCON-0008's direct-public fail-closed boundary; permanent retirement
  replaces its former reservation requirement for this unused hostname.
- ADR-SIRCON-0014 records the user-accepted permanent retirement and ordered
  shared-default certificate transition.
- nginx-proxy 1.6 documentation and tagged template; ownership discovery retained
  in session `01a13f74-3532-7fbb-b559-a759ebf03e89`.
- Existing Sir Compose, deploy verifier, workload registry, CLI and operations
  command surfaces; preserve all private/tunnel behavior.

## Core Vertical And Performance

The integrated boundary is shared nginx-proxy default selection followed by
retirement of the Sir public vhost. Two bounded execution units remove the
deploy-verification dependency and the Compose/CLI/workload declaration; the
lead integrates shared-owner routing and current documentation. There is no
request-path performance change. Live walking proof remains pending approval;
local tests establish source behavior only.

## Validation

- Focused operations tests for deploy orchestration, Compose topology, bounded
  startup, workload declarations/inventory and detached command surfaces.
- Focused CLI route-submission tests and CLI help inspection.
- Inspect `pdm run check --plan operations` and run the owning named checks.
- Docs, skills, handoff validation and `git diff --check`.
- Before approved live removal, prove the default presents no product
  certificate; after removal prove no convert vhost or renewal remains and
  current product vhosts still select their own certificates. This proof is
  not claimed by local tests.

## Stop Conditions

- Any live Hemma mutation without separate parent/user approval.
- Missing infrastructure source ownership or a dirty checkout owned by another
  session; report the owning path rather than changing it.
- Default-host proof still depends on a product certificate, product vhosts
  would be recreated broadly, or certificate cleanup would affect shared certs.
- Any command would start Sir/GPU services, reboot the host, or modify sibling
  repository references assigned to the parent.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ |
| D01 | The user confirmed Sir production and the convert public hostname are retired and unused.                                            |
| D02 | Retire the Sir reserved service and all active dependencies on the public hostname.                                                  |
| D03 | Unknown SNI must fail closed using no product certificate; use the default self-signed pair or reject TLS.                           |
| D04 | Prove the replacement default before removing the convert vhost/container, then clean only its certificate material.                 |
| D05 | Discover shared infrastructure ownership read-only; change its owning Git source and never hand-patch Hemma.                         |
| D06 | All live mutation waits for parent-obtained user approval; never reboot or start GPU services.                                       |
| D07 | List Skriptoteket and HuleEduOS references without editing them; Namecheap CNAME deletion follows vhost retirement proof.            |
| D08 | Commits stay on the assigned branch; the parent owns main integration/publication and deploy helpers do not push arbitrary branches. |

## Implementation Evidence

- Two fresh juniors removed the deploy verifier and the Compose/CLI/workload
  surface. The lead removed the cross-repo direct-edit helper and integrated
  current guidance. No branch publication or live mutation ran.
- Read-only ownership discovery found no Git repository under or above
  `/home/paunchygent/infrastructure`. The parent routed a tracked shared compose
  override and apply/proof surface to the Skill Repository implementation lead.
- nginx-proxy is `nginxproxy/nginx-proxy:1.6`; acme-companion is `2.4`.
  Context7 documentation was checked against the tagged nginx-proxy 1.6.0
  README/template because Context7 returned the unversioned source.
- On 2026-10-15 the existing `default.crt` had subject and issuer
  `CN=letsencrypt-nginx-proxy-companion`, distinct from every product. Its SHA256
  fingerprint was `0C:3C:0A:73:24:16:7F:35:6C:46:14:5F:84:CB:A9:80:26:9B:B2:62:91:76:E1:BA:36:D1:18:5D:A1:10:5F:8C`.
  This proves available certificate material, not application of the override.

The parent explicitly deferred edits to the following two current references
until the shared docs hook's retired-identity allowance is repaired. Their
existing `CONV-*` identifiers are preserved. PreToolUse rejects body edits while
`pdm run docs-validate` passes; no alternate writer or hook bypass was used.
ADR-SIRCON-0014 governs retirement over their stale public-lane guidance:

- `docs/reference/ref-sircon-general-sir-convert-a-lot-cli-and-service-usage-sir-convert-a-lot-cli-and-service-usage.md`
- `docs/reference/ref-sircon-general-audio-transcription-service-api-artifact-contract-audio-transcription-service-api-artifact-contract.md`

The older cutover and public-host recovery backlog records retain their
historical contracts. Editing those records would require contract-profile and
retired-identity migration; this task does not migrate those planning records.

The ordered live procedure is the
[public-edge retirement runbook](../../runbooks/run-sircon-retire-the-sir-convert-public-edge-after-default-host-certificate-separation-retire-the-sir-convert-public-edge-after-default-host-certificate-separation.md).
All host mutation remains pending approval. Two final read-only SAN/alias
probes returned SSH connection refused at 12:41 UTC on 2026-10-15; those
certificate-sharing checks remain required before approved cleanup.

## Validation Evidence

- `pdm run check operations`: all phases passed, including 162 focused tests,
  40-source-file typecheck, Ruff, YAML/Markdown checks, docs, skills, handoff and
  diff validation. Retained capture: `0008-pdm-run-check-operations` in session
  `01a13f74-3532-7fbb-b559-a759ebf03e89`.
- `pdm run check service`: all phases passed, including four selected CLI test
  files (30 tests) and a 42-source-file typecheck. Retained capture:
  `0009-pdm-run-check-service` in the same session. Initial operations/service
  attempts failed only Markdown formatting;
  formatting was repaired before final validation.
- Direct `convert-a-lot convert --help` inspection shows local development and
  canonical Hemma tunnel advice without a direct public lane.
- Tracked-source audit found no remaining `VIRTUAL_HOST`, `LETSENCRYPT_HOST`,
  `CERT_NAME` or `SIR_CONVERT_A_LOT_PUBLIC_HOST` in runtime source outside tests
  and historical documentation. No live or GPU proof is claimed.
