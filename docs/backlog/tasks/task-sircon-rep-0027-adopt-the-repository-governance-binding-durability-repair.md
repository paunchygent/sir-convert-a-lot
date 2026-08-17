---
type: task
id: TASK-SIRCON-REP-0027
title: Adopt the repository-governance binding durability repair
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-17'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Sir Convert-a-Lot pins and locks repository-governance 0.11.4 and regenerates the reserved binding block that version validates
  - A worktree whose governing authority is archived keeps resolving that authority and its declared setup groups
backlog_document_profile: contract-derived
---

## Implementation Contract

This repository pins repository-governance `0.11.1`. Since that release the
shared package gained a durable authority binding for worktrees the governed
creator did not create, and an independent review then found a defect that
predates the binding entirely: authority resolution searched only
`docs/backlog/<lane>/`, while `archive-documents` moves every completed epic,
story, and task to `.archive/`.

Any worktree whose governing authority is archived therefore stops resolving it
and fails every later `setup`. That exposure applies to ordinary
`codex/<authority-id>` worktrees in this repository, not only to bound ones, and
it grows with every completed backlog item.

`0.11.4` resolves an archived authority exactly like a current one, records a
binding only after its groups install, makes an explicit authority request the
single recovery path for any recorded declaration, and drops the inherited PDM
project selectors so the immutable runtime commands execute the runtime. This
task adopts that release and regenerates the reserved binding block it
validates.

### Decision And Assumption Ledger

| ID    | Type       | Status | Decision                                                                                                | Rejected alternative                                                                    | Source                       |
| ----- | ---------- | ------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------- |
| AD-01 | dependency | closed | Adopt repository-governance `0.11.4` at revision `de4faadfd70c7ff8268377640f5ad048f68039ed`.            | Stay on `0.11.1` and accept that archiving a completed authority breaks live worktrees. | TASK-SKILL-REP-0119          |
| AD-02 | bindings   | closed | Regenerate the reserved block with `repository-governance-bindings sync` in the same change as the pin. | Advance the pin alone and leave routine commands reporting binding drift.               | `validate_reserved_bindings` |
| AD-03 | boundary   | closed | Change only the pin, lock, reserved binding block, and this contract.                                   | Change dependency group contents or product behavior as part of the adoption.           | This task                    |

### Scope Boundary

This task changes the repository-governance pin, `pdm.lock`, the generated
reserved binding block, and this contract. It changes no dependency group
contents, conversion behavior, lane routing, or runtime configuration.

## Contract Inputs

- The published repository-governance `0.11.4` release at revision
  `de4faadfd70c7ff8268377640f5ad048f68039ed`.
- The package-owned `repository-governance-bindings sync` maintenance command.

## Core Vertical And Performance

The core vertical is one `pdm run setup` that keeps resolving its governing
authority after that authority is archived. Resolution scans one additional
directory that is usually absent; no other command changes.

## Validation

- `pdm run check`
- `pdm run docs-validate docs/backlog/tasks/task-sircon-rep-0027-adopt-the-repository-governance-binding-durability-repair.md`
- `git diff --check`

## Stop Conditions

- Routine commands report binding or producer drift after the pin advances.
- Regenerating the reserved block changes any binding other than `setup` and
  `new-worktree`.

## Decided Contract Terms

| ID    | Decided contract term                                                                                         |
| ----- | ------------------------------------------------------------------------------------------------------------- |
| DC-01 | Consume the published shared release; do not copy shared resolution or binding logic into this repository.    |
| DC-02 | Advance the pin, lock, and generated reserved binding block in one change so validation never observes drift. |
| DC-03 | Keep conversion behavior, lane routing, and runtime configuration outside this task.                          |
