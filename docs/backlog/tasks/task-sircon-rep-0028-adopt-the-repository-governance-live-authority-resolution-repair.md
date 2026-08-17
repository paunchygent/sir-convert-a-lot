---
type: task
id: TASK-SIRCON-REP-0028
title: Adopt the repository-governance live authority resolution repair
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
  - Sir Convert-a-Lot pins and locks repository-governance 0.11.6 and its installed package reports that version
  - Worktree creation requires a live authority while setup still resolves an archived one
backlog_document_profile: contract-derived
---

## Implementation Contract

`TASK-SIRCON-REP-0027` adopted repository-governance `0.11.4`, which made
authority resolution read the archive lane as a union with the live lane while
still requiring exactly one match, and shared one resolver with worktree
creation. An identifier that exists live and archived therefore failed closed,
and `new-worktree` began admitting completed, archived authorities — verified
here, where `TASK-SIRCON-REP-0001` is archived and `status: done`.

`0.11.6` resolves the live lane first and reads the archive only when the live
lane holds no match, restores worktree creation to live authorities only,
records a binding durably through its directory entry, and states its refusals
in terms of the groups actually installed.

The reserved binding block is unchanged between `0.11.4` and `0.11.6`, so this
adoption advances the pin and lock only. The installed package must be refreshed
in this checkout, because a pin alone does not change the executing code.

### Decision And Assumption Ledger

| ID    | Type       | Status | Decision                                                                                           | Rejected alternative                                                                         | Source              |
| ----- | ---------- | ------ | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------- |
| AL-01 | dependency | closed | Adopt repository-governance `0.11.6` at revision `f2242e25bf469170b2865f49207c6710ab343189`.       | Stay on `0.11.4`, where `new-worktree` admits archived completed authorities.                | TASK-SKILL-REP-0120 |
| AL-02 | bindings   | closed | Advance the pin and lock only; the reserved binding block is byte-identical across these versions. | Run `repository-governance-bindings sync`, which would rewrite a block that needs no change. | `bindings check`    |
| AL-03 | install    | closed | Refresh the installed package in this checkout and verify the reported version.                    | Commit the pin alone, which leaves the superseded package executing.                         | Third review        |

### Scope Boundary

This task changes the repository-governance pin, `pdm.lock`, and this contract.
It changes no dependency group contents, conversion behavior, lane routing, or
runtime configuration.

## Contract Inputs

- The published repository-governance `0.11.6` release at revision
  `f2242e25bf469170b2865f49207c6710ab343189`.
- The archived `TASK-SIRCON-REP-0001`, which `0.11.4` wrongly admitted into
  worktree creation.

## Core Vertical And Performance

The core vertical is one `pdm run setup` that resolves its governing authority
through the live lane first. No other command changes.

## Validation

- `pdm run check`
- `pdm run docs-validate docs/backlog/tasks/task-sircon-rep-0028-adopt-the-repository-governance-live-authority-resolution-repair.md`
- `git diff --check`

## Stop Conditions

- The reserved binding block would need regeneration.
- The installed package still reports a superseded version after refresh.

## Decided Contract Terms

| ID    | Decided contract term                                                                   |
| ----- | --------------------------------------------------------------------------------------- |
| DC-01 | Consume the published shared release; copy no resolution logic into this repository.    |
| DC-02 | Advance the pin and lock together and refresh the installed package in the same change. |
| DC-03 | Leave the reserved binding block untouched while it validates.                          |
| DC-04 | Keep conversion behavior and lane routing outside this task.                            |
