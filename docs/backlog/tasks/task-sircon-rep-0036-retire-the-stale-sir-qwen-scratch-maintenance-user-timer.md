---
type: task
id: TASK-SIRCON-REP-0036
title: Retire the stale Sir Qwen scratch maintenance user timer
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-22'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer and skill-prose-reviewer
  decided_at: '2026-10-22T11:17:00Z'
  approval_protocol: agent-implementation:approved-review-closeout
  approval_evidence: Code rereview 604209c5 approved 04b942c after F01-F03 repairs; prose rereview 850b2845 approved the repaired runbooks; Sir retained root 01a16345-8ce2-7602-8bc0-7900e7a9513f holds both records under evidence/reviews.
task_kind: repository
acceptance_criteria:
  - The Sir user-scope Qwen scratch maintenance timer and service are disabled, stopped and removed from the Hemma user unit directory through the repository's uninstall-timer command.
  - The repository can no longer install that timer; status-timer, audit, maintain and remediate keep their reviewed behaviour.
  - The Qwen fine-tuning and GPU runtime runbooks describe the retired timer and the current Scratch roots.
backlog_document_profile: contract-derived
---

## Implementation Contract

Retire the held user-scope units `sir-convert-a-lot-qwen-scratch-maintenance.service`
and `.timer` that skill-repository TASK-SKILL-REP-0371 D15 handed to Sir. Remove
the `qwen-scratch-policy install-timer` verb with its unit renderers and install
report. Add `uninstall-timer`: it disables and stops the named timer and service,
removes only those two files from the user unit directory when present, reloads
the user manager, clears failed state and reports what it removed. After `main`
is integrated, run it from the canonical checkout on Hemma. Repair the stale
timer paragraph in the Qwen fine-tuning runbook and the Scratch roots list in
the GPU runtime runbook.

Out of scope: `sir-convert-a-lot-qwen-docker-bind-roots.service` and its cutover
drop-in; deleting the remaining `/srv/scratch/sir-convert-a-lot` entries
(`task-347`, `tools`, `bin`, `data`); any Hot retention policy for
`~/.data/sir-convert-a-lot/build`.

## Contract Inputs

- Skill-repository TASK-SKILL-REP-0371 D15 (closed 2026-10-22) and the teacher's
  instruction relayed that day to decide without questions.
- TASK-SIRCON-REP-0033: Docker cleanup refusal, Hot placement and D03 (no new
  retention horizon).
- Host state 2026-10-22: both units disabled and inactive; the user journal has
  no successful run since its first entry on 2026-07-29 and shows hourly
  failures until 2026-10-14; the candidate roots under
  `/srv/scratch/sir-convert-a-lot/build` and the `/srv/storage` archive root do
  not exist. Retained plan: Sir context `01a16345-8ce2-7602-8bc0-7900e7a9513f`.

## Core Vertical And Performance

`pdm run qwen-scratch-policy uninstall-timer` on Hemma removes the real units,
and `systemctl --user` then reports neither unit. No performance concern.

## Validation

- Focused tests in `tests/sir_convert_a_lot/operations/test_hemma_scratch_maintenance.py`
  and `test_hemma_storage_ownership.py`, including an adversarial case where
  `uninstall-timer` must leave other files in the unit directory untouched and
  must succeed when the units are already absent.
- Focused typecheck and lint of the changed modules; `docs-validate` on the
  changed docs; `handoff-validate`; `git diff --check`.
- Host: `systemctl --user list-unit-files 'sir-convert-a-lot-qwen-scratch*'`
  lists none, and no Sir container or the bind-roots unit changes state.

## Stop Conditions

- Stop if a Sir Qwen container is running or a Sir job uses the units.
- Never use sudo or edit host unit files by hand.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Retire the units; do not retarget them. A Hot retention horizon is a separate Sir planning decision.                                                                      |
| D02 | Remove `install-timer`, its renderers and install report; add `uninstall-timer` touching only the two named unit files; keep audit, maintain, remediate and status-timer. |
| D03 | Change the host only by running `uninstall-timer` from the canonical checkout after integration; no hand edits, no sudo.                                                  |
| D04 | Leave `sir-convert-a-lot-qwen-docker-bind-roots.service` and its drop-in unchanged.                                                                                       |
| D05 | Do not delete the `/srv/scratch/sir-convert-a-lot` leftovers; record sizes, dates and consumers and report them.                                                          |
| D06 | Repair the stale timer and Scratch-root guidance in the two runbooks in the same change.                                                                                  |

## Closeout

Integrated as `main` merge `52dcd46`. Code review `e479ae6` requested changes:
F01 arbitrary unit names, F02 unchecked `systemctl` failures, F03 unchecked
service enablement. Rereview approved repair `04b942c`. Prose review requested a
correction of an unverified Hugging Face cache claim and a named storage-tier
owner; its rereview approved after a full search of Hot, Cache and
`/home/paunchygent` found no Granite FP8 cache. `pdm run check operations`
passed with 52 tests.

On 2026-10-22 at 11:18:22Z, `pdm run qwen-scratch-policy uninstall-timer` from the
canonical checkout removed both unit files. Both units then reported
`LoadState=not-found`, an empty `UnitFileState` and `ActiveState=inactive`.
`list-unit-files` lists none, and `status-timer` reports the timer disabled and
inactive. The bind-roots service stayed `active`/`exited`, and no Sir or Qwen
container ran. The July backup file
`sir-convert-a-lot-qwen-scratch-maintenance.timer.task205-onactive.bak` remains
in the user unit directory; systemd does not load it. Evidence:
`evidence/operations/host-retirement/` and `evidence/reviews/` in the Sir
retained root above.
