---
type: task
id: TASK-SIRCON-REP-0020
title: Archive terminal and superseded governed records after cutover
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-08-02T19:05:51+0200'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: Inline Plan Document Review approved TASK-SIRCON-REP-0020 for readiness.
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-08-02T19:32:37+0200'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Exact candidate 34758ae8 approved with no blocking findings.
task_kind: repository
acceptance_criteria:
- Every terminal, canceled, deprecated, and superseded document is moved from live
  governance to .archive with relative provenance preserved, current indexes and relationships
  exclude archived records, and ordinary shared docs validation remains green.
---

## Context

Sir's governance cutover left 389 governed historical records in live paths:
387 terminal backlog records, one deprecated converter contract, and one
superseded decision. Eight retired-memory files are historical but are not
governed documents and remain outside this operation. Shared
`repository-governance` now owns the canonical archive behavior.

## Impact And Escalation

This task changes only Sir's immutable package pin/lock, generated command
binding, current structured relationships that block archival, generated live
indexes, and mechanical file locations. It changes no product behavior,
runtime, Docker surface, tests, converter semantics, or retained-memory files.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID | Status | Contract term, decision, or assumption | Recommendation or closed decision | Other highly plausible options | Motivation | Source |
| --- | --- | --- | --- | --- | --- | --- |
| SARC-001 | closed | Sir must consume the shared archive implementation rather than define local behavior. | At execution, advance the immutable dependency and lock to the latest verified release containing the shared archive command, then synchronize the generated `archive-documents` binding. Do not freeze a package version in backlog prose. | Implement a Sir-local command or archive layout; freeze a planning-time package version. | The user assigned archive behavior to the rolling shared package protocol and explicitly rejected backlog version pins. | User decisions on shared ownership and rolling package adoption. |
| SARC-002 | closed | The archive set must match the governed inventory. | Move exactly the 389 governed eligible records selected by the shared command to `.archive/<original path>`. Exclude the eight retired-memory files. | Move all 397 inventoried historical files. | Retained memory has no governed type/status under the accepted shared contract. | Retained Sir inventory; TASK-SKILL-REP-0075 ARC-004. |
| SARC-003 | closed | Live structured relationships cannot target archived identities. | Run the shared preflight, edit only its exact live incoming relationship blockers under this task, and rerun. Do not rewrite archived content or body-prose history. | Add archive-aware live relationships or silently remove links in the command. | Current relationships must remain truthful and consumer-owned; the package deliberately fails closed. | Shared archive contract and command behavior. |
| SARC-004 | closed | The governing task becomes terminal during closeout. | Archive the initial 389-record set while this task remains `in_progress`; after independent approval and `done`, rerun the same command once to archive this task itself and refresh live outputs. | Leave this terminal task live or archive it before review. | The move must be reviewed, while the final live corpus must contain no terminal exception. | User requirement that terminal docs move; review-gate ordering. |
| SARC-005 | closed | Proof must remain docs/governance scoped. | Use lock checks, generated binding check, archive command/preflight results, exact count/path/byte audits, ordinary docs sync/validation, skills/handoff validation, and `git diff --check`. Run no product, broad Python, Docker, browser, deployment, or Hemma suite. | Run Sir's full 1,700+ test corpus. | This is a package adoption and mechanical document move with no product behavior. | User cutover validation constraint. |

## Plan

Advance Sir to the current immutable shared release, synchronize the generated bindings, resolve
only exact live relationship blockers, and invoke the shared bulk archive
command. Preserve every file's bytes and original path under root `.archive`.
After review and closeout, invoke the same command once more for this task.

## Implementation Steps

1. Advance `pyproject.toml` and `pdm.lock` to the verified immutable release and
   run setup/binding synchronization.
2. Run `pdm run archive-documents` as a preflight; resolve only reported live
   structured relationship blockers.
3. Rerun the command and verify the exact 389 canonical moves, byte identity,
   and regenerated live outputs.
4. Run the bounded validation, freeze the candidate, and obtain independent
   implementation review.
5. Record approved closeout, transition this task to `done`, rerun
   `archive-documents` to move this task, and validate the final live corpus.
6. Integrate and publish Sir main, then retire the clean task worktree/branch.

## Proof

- Contract/validator proof applies because the consumer change is a pin,
  generated binding, governed relationship correction, and mechanical move.
- Pre-change: `pdm run archive-documents` is unavailable on the current consumer pin.
- Post-change: the installed shared command first reports exact relationship
  blockers without moving files, then moves the complete eligible set after
  those blockers are resolved.

## Validation

- `pdm lock --check`
- `pdm run setup`
- `pdm run archive-documents`
- exact source/destination count and byte audit
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.
- Any product/runtime change, local archive implementation, retained-memory
  move, archive content rewrite, or broad test requirement.

## Lessons Learned

Archive adoption is a consumer pin plus mechanical reconciliation. It does not
need another migration manifest, historical validator, or local archive schema.

## Notes

Retained inventory:
`.orchestration/context/sessions/019fc322-a15d-7187-bb54-ccb5cdbf1803/discovery/explorer/archive-inventory/0001-archive-inventory.md`.
The execution parent records the selected immutable package tuple in release
evidence and consumer lock state, not in this backlog contract.

## Readiness

SARC-001 through SARC-005 are closed by the user's archive decisions, retained
inventory, and immutable shared release. After independent plan approval, the
task may become `ready`; implementation admission remains separate. Residual
risk is limited to consumer-local relationship blockers reported by preflight.

## Plan Document Review

- Decision: `approved`.
- Reviewer: `plan-document-reviewer`.
- Recorded: `2026-08-02T19:05:51+0200`.
- Findings: none. SARC-001 through SARC-005 close the material decisions.
- Scope: shared-package adoption, exact governed inventory, consumer-owned live
  relationship reconciliation, mechanical canonical moves, and proportionate
  docs/governance proof.
- Permitted next step: apply `proposed -> ready`; admit implementation
  separately.
- Residual risk: exact consumer relationship blockers remain preflight-dependent
  and fail closed under the shared command contract.

## Closeout

Exact candidate `34758ae8` moved 389 governed records as canonical 100%
byte-identical renames, preserved all eight retained-memory files, and passed
the selected docs/governance proof. Independent ruthless review approved with
no findings. After the authorized `done` transition is committed, the shared
command archives this governing task itself.

## Implementation Review

- Decision: `approved`; findings: none.
- Reviewer: `ruthless-reviewer`; recorded `2026-08-02T19:32:37+0200`.
- Permitted next step: apply closeout, transition to `done`, commit that exact
  terminal state, then rerun `archive-documents` for the governing task.
