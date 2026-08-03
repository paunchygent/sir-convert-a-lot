---
type: task
id: TASK-SIRCON-REP-0025
title: Complete operations handoff and parity-gated governance retirement
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-03'
status: done
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved ST-SKILL-08-07's operations and parity-gated retirement slice and directed execution to proceed without needless ceremony on 2026-08-03.
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directed the final cutover to proceed without additional ceremony and approved rolling shared-package repairs on 2026-08-03.
task_kind: repository
acceptance_criteria:
  - Read-only operations, staleness, root-handoff, and active-route proof passes without deployment, restart, conversion, GPU, training, or remote mutation
  - Local shared-workflow overlaps retire only after exact public-entrypoint parity while product and Qwen commands remain repository-owned
  - Historical validation remains disabled and no broad root test aggregate becomes a cutover gate
---

## Context

The shared package already owns Sir's current Docs-as-Code entrypoints, but the
replaced local implementation, local contract/profile, legacy auxiliary
commands, and `.codex/handoff.md` route remain. The final cutover slice retires
only those overlaps and proves the shared root-handoff and current validation
routes.

## Impact And Escalation

The write set is the root handoff and live entrypoint references,
`pyproject.toml`, its tooling lock entry, obsolete local Docs-as-Code files and
their implementation test, this task, and generated indexes. Product code and
commands, Qwen, Docker, deployment, conversion, GPU, training, product
dependencies, and historical archive records are excluded.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID     | Type       | Status | Question/Assumption                              | Recommendation/Decision                                                                                                                                                                                                         | Source                                                                             |
| ------ | ---------- | ------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| FC-001 | handoff    | closed | Which handoff contract remains?                  | Replace `.codex/handoff.md` with the shared concise root `handoff.md` shape and update live routes.                                                                                                                             | ST-SKILL-08-07; HuleEdu/Skriptoteket precedent; retained discovery                 |
| FC-002 | retirement | closed | Which local governance implementation retires?   | Remove `scripts/docs_as_code`, its local contract and completed migration profile, legacy auxiliary PDM commands, and the sole local implementation test. Current public scaffolding/index/validation already uses the package. | Current binding blocks; successful corpus migration and repeated shared docs proof |
| FC-003 | validators | closed | How are skill and handoff checks exposed?        | Bind `skills-validate` and `handoff-validate` directly to their package entrypoints. Historical validation receives no local public route.                                                                                      | Package 0.9.17 entrypoints; user historical-validator-off decision                 |
| FC-004 | operations | closed | Does `run-hemma` retire?                         | No. Preserve the Sir product wrapper and all Hemma/product/Qwen commands because exact transport parity is absent.                                                                                                              | Retained Explorer comparison; ST-SKILL-08-07                                       |
| FC-005 | history    | closed | Are stale historical command mentions rewritten? | No. Preserve `.archive` and terminal historical evidence unchanged; audit only live routes.                                                                                                                                     | User archive/history decision                                                      |
| FC-006 | proof      | closed | What proof is sufficient?                        | Shared docs, skills, handoff, staleness, active-route grep, one read-only local-wrapper Hemma transport probe, and diff checks. No broad root suite.                                                                            | ST-SKILL-08-07 accepted proof boundary                                             |
| FC-007 | package    | closed | May the shared package advance during cutover?   | Yes. Roll the immutable governance pin and tooling lock whenever consumer proof discovers a required shared repair; do not freeze a package version in backlog prose.                                                           | Direct user decision                                                               |

## Plan

Install one concise root handoff, update live routes and two validator bindings,
then delete the now-unreachable local governance implementation and its local
contract artifacts. Preserve every product-owned surface.

## Implementation Steps

1. Create the shared root handoff and update live `AGENTS.md` pointers.
2. Switch the skill/handoff validators to package entrypoints and remove legacy
   local governance commands and the obsolete mypy target.
3. Delete local Docs-as-Code code, local contract/migration metadata, and its
   implementation test.
4. Synchronize indexes and run the bounded public-entrypoint proof.

## Proof

- Structural/public-command proof applies; no product behavior changes.
- Before the change, package `handoff-validate` fails because root `handoff.md`
  is absent, and active grep exposes the local implementation and old route.
- After the change, package docs, skill, handoff, staleness, and active-route
  checks pass with no live local validator/scaffolder/indexer route.
- A read-only `run-hemma -- hostname` probe proves the preserved product wrapper
  remains usable without mutating Hemma.

## Validation

- `pdm run check --plan repository`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- deterministic `pdm run staleness-audit` at the integration candidate
- active-route `git grep` excluding `.archive` and terminal historical evidence
- `pdm run run-hemma -- hostname`
- `git diff --check`

## Stop Conditions

- Any required product/Qwen change, remote mutation, broad test run, archive
  rewrite, compatibility shim, or evidence that a removed local command still
  has an active producer.

## Lessons Learned

- Binding parity is sufficient only for shared workflow commands; a similarly
  named product transport wrapper remains local when its behavior differs.

## Notes

Discovery is retained under session
`019fc50b-de14-7c4d-af42-0ddc5c10458a`. Backlog prose does not freeze a package
version or planning SHA.

## Readiness

FC-001 through FC-007 are closed by the accepted story, direct user decisions,
and current repository/package evidence. Implementation may begin.

## Closeout

The root handoff and every live route now use the shared contract. The obsolete
local contract, migration profile, implementation, commands, and implementation
test are removed; historical validation has no public route. Product-owned
`run-hemma` remains local and returned `paunchygent-server` through the real
read-only transport; its 12 focused tests pass.

The cutover exposed two shared current-only defects. TASK-SKILL-REP-0079 made
`run-hemma` ownership derive from declared Hemma facts. TASK-SKILL-REP-0080 made
current-only docs commands reuse committed retired identities and moved the
authored Markdown policy into the package. Sir consumes immutable 0.9.20 at
`ad642130e887f4a829e3579346f714c41e1e41cd`.

`docs-sync`, `docs-validate`, `skills-validate`, `handoff-validate`, binding
validation, deterministic staleness audit, active-route audit, and
`git diff --check` pass. The derived `repository` check plan selected only its
35 repository tests plus named validators; execution passed. No broad root,
Qwen, product-service, Docker, GPU, deployment, conversion, or training suite
ran.
