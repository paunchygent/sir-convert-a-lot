---
type: task
id: TASK-SIRCON-REP-0026
title: Publish the Sir Convert-a-Lot platform discovery overview
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-03'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-08-03T10:00:00+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directive of 2026-08-03 ordered the three remaining ST-SKILL-08-09 conformance slices; every decided term derives from that accepted parent story (CON-003, CON-004, CON-005) and its note on the deferred markdown gate. No independent plan-document-reviewer ran in that session.
closeout_review:
  record: REV-SIRCON-TASK-REP-0026-CLOSEOUT
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: REV-SIRCON-TASK-REP-0026-CLOSEOUT
task_kind: repository
contract_version: 2
acceptance_criteria:
  - The .codex/skills/ lane carries a codemap-style skill whose references publish the platform discovery overview covering the v2 service layers, conversion routes, sidecars, containers, and docs topology
  - The overview is reachable from AGENTS.md routing without duplicating route tables
  - The repository docs, skills, handoff, Markdown, and diff validators have truthful current results; the implementation-time markdown failure remains historical evidence and is not repaired by this task
---

## Implementation Contract

Publish one Sir Convert-a-Lot platform discovery overview in the repo-local
`.codex/skills/repo-code-map/` lane and route it from one `AGENTS.md` table row.
The overview covers the application layers, conversion routes and job model,
sidecars and containers, execution lanes, ownership boundaries, and docs
topology from repository state.

This repository-governance slice changes no product behavior, service,
container, deployment, or shared governance reference. The implementation-time
missing-`gfm` markdown defect was deferred under the accepted parent story; this
task performs no repair and records the current package-backed gate result.

## Contract Inputs

- ST-SKILL-08-09 CON-003 through CON-005 and its Sir Convert-a-Lot markdown
  gate note.
- The shared Discovery Docs And Codemap Placement policy.
- The accepted v1 planning, alternatives, readiness evidence, and initial
  implementation record preserved at commit
  `f6c958cd6ed5e90ec8fecf2d68805f333db90084`.
- Retained review discovery and reconciliation plan in session
  `019fd7fc-7a82-7ba2-919a-9685e613c1f7`.
- Reviewer-owned closeout record
  `REV-SIRCON-TASK-REP-0026-CLOSEOUT`, approved on 2026-08-06.

## Proof

- Implementation commit `f6c958cd6ed5e90ec8fecf2d68805f333db90084`
  created the two-file repo-code-map lane and the one-row `AGENTS.md` route.
- Initial implementation evidence recorded successful docs sync, docs
  validation, and diff hygiene, plus the same missing-`gfm` failure before and
  after the slice.
- Closeout repair evidence on 2026-08-06: `pdm run format-md` and
  `pdm run check-md` completed on the two changed authored Markdown files;
  `pdm run docs-sync`, affected `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check` exited 0.
- The implementation-time missing-`gfm` result remains historical evidence.
  The current package-backed Markdown commands pass on the changed authored
  files, so that earlier defect is no longer a residual risk for this repair.

## Validation

- `pdm run format-md <changed authored Markdown>` before docs sync
- `pdm run docs-sync`
- `pdm run docs-validate <changed governed task and generated docs paths>`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `pdm run check-md <changed authored Markdown>`
- `git diff --check`

No product test, CI, Python quality, runtime, or remote proof belongs to this
docs/governance-only contract.

## Stop Conditions

- Missing authority, an open material decision, or scope beyond the factual and
  evidence repair returns to the task owner.
- The reviewer-owned verdict and review record remain unchanged during repair.
- Any validator failure blocks re-review.
- Task terminal transition remains parent-owned after reviewer approval. Story
  verification and story closeout remain separate later gates.

## Decided Contract Terms

| ID      | Decided contract term                                                                                                                                                          |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SCO-001 | The overview lives in `.codex/skills/repo-code-map/` as a minimal `SKILL.md` router plus `references/platform-discovery-overview.md`.                                          |
| SCO-002 | The lane carries one discovery overview, not a full codemap family.                                                                                                            |
| SCO-003 | The overview describes the named application, conversion, container, execution, ownership, and docs surfaces from repository state.                                            |
| SCO-004 | One `AGENTS.md` route row reaches the overview without duplicating its content.                                                                                                |
| SCO-005 | This task does not repair the implementation-time missing-`gfm` failure; its original deferred result remains historical evidence and current results are recorded truthfully. |
| SCO-006 | Slice proof uses the repository's docs, skills, handoff, Markdown, and diff gates.                                                                                             |

## Plan Document Review

User closure on 2026-08-03 approved the task-local terms derived from the
accepted ST-SKILL-08-09 contract. No independent plan-document-reviewer ran in
that session. The v2 migration preserves those terms and cites the original
planning record instead of carrying its alternatives and implementation plan.

## Implementation Review

`REV-SIRCON-TASK-REP-0026-CLOSEOUT` records the independent
`ruthless-code-review` decision `approved` at
`2026-08-06T19:56:45+02:00`. Changed-files-only re-review closed the false
validator-absence finding after the factual repair, omitted validator proof,
and v2 migration were inspected. The parent may now apply the task's terminal
lifecycle transition without changing reviewer-owned facts.
