---
type: task
id: TASK-SIRCON-REP-0035
title: Load local PDM dotenv configuration without shell execution
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-15T19:19:13Z'
  approval_protocol: agent-implementation:approved-review-closeout
  approval_evidence: Independent exact three-file rereview approved with no outstanding findings; shared retained root 01a1407e-c16a-70f5-9c1d-dc6019adb9fb evidence/review/sir0035-wrapper-rereview.md.
task_kind: repository
acceptance_criteria:
  - "Valid dotenv data reaches the requested existing PDM command without shell execution or exit127."
  - "The wrapper preserves explicit override precedence, missing-file behavior, literal argv and child exit status."
  - "Focused adversarial proof and actual corrected Mac/Hemma commands pass with original configuration/private work preserved and Sir production/STT remaining offline."
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the existing `run-local-pdm` wrapper so valid dotenv data reaches the
requested PDM command without shell execution. Let the existing PDM per-script
`env_file.override` owner load `.env`; keep the shell wrapper's checkout root,
usage check, literal argv forwarding, `exec` and child status. Preserve missing
env-file behavior and existing explicit override precedence.

Scope only `scripts/devops/run-local-pdm.sh`, its declaration in `pyproject.toml`
and a focused operations test. No new parser, dependency, global PDM behavior,
secret rewrite or configuration migration. Preserve existing private work and
all `.env` bytes. Sir production and STT remain offline by the user's standing
decision; this wrapper repair does not provision or start those workloads.

## Contract Inputs

- Accepted derived plan: Mac Sir retained session `01a140e5-f446-7105-b54c-68cba9b03a7a`, `evidence/planning/TASK-SIRCON-REP-0035/plan.md`, command-written with closed D01-D03.

- [Local retained plan](../../../.orchestration/context/sessions/01a140e5-f446-7105-b54c-68cba9b03a7a/evidence/planning/TASK-SIRCON-REP-0035/plan.md).

- Accepted shared TASK-SKILL-REP-0316 storage decisions and TASK-SKILL-REP-0318
  autonomous repair/ordinary command acceptance; parent-admitted wrapper fault.

- Parent's actual exit127 observation and current wrapper lines14–19, which
  execute `source .env` on valid dotenv data.

- Retained session `01a1407e-c16a-70f5-9c1d-dc6019adb9fb`: official current PDM
  docs, PDM2.29.2 private adversarial fixture and exact source scope proposal.

- Sir's standing production/STT offline decision, preserved unchanged.

## Core Vertical And Performance

Keep the public command `pdm run run-local-pdm <script> [args]`. Move only its
dotenv loading to PDM's existing per-script owner and remove shell sourcing.
The owned fixture already reproduces legacy exit127 and passes the proposed
PDM owner with literal argv, dotenv override, no command execution and an absent
file. That fixture is not acceptance of the actual repaired wrapper.

After source review/publication, run the ordinary corrected command on both Mac
and Hemma with the preserved real configuration, observing the requested child
and its result without printing secrets. This is a short command repair; no
service restart, model download, paid job or runtime build is required.

## Validation

- Focused adversarial test at
  `tests/sir_convert_a_lot/operations/test_run_local_pdm_wrapper.py`: valid
  dotenv that is invalid shell, literal command substitution, quoted values,
  override precedence, absent file, special-character argv and child status.
- Affected shell/TOML/Python lint and the repository's focused tests/checks;
  task/docs validation through existing commands, no full suite.
- Actual Mac and Hemma `run-local-pdm` child execution with existing env bytes
  unchanged and no secret output; record installed/effective revision separately.
- Independent review before parent Git integration and ordinary publication.

## Stop Conditions

- Preserve `.env`, private orchestration roots, unrelated source and active
  work. A command failure returns exact safe diagnostics without sourcing data
  again or rewriting configuration.
- No service activation, STT provisioning, model change/download, new parser,
  framework or dependency is authorized.
- Parent owns readiness, worktree/Git lifecycle and installed rollout; failed
  focused proof or independent review blocks that transition.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                   |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Use the existing PDM dotenv owner for the existing wrapper, preserving explicit override, missing-file behavior, literal argv and child status without shell execution. |
| D02 | Preserve all configuration/private work; run focused adversarial checks and actual corrected Mac/Hemma commands through normal parent-owned review/publication.         |
| D03 | Sir production/STT remains offline; no provisioning, model download, dependency, parser or framework is part of this wrapper repair.                                    |

## Delivery And Acceptance

Published reviewed source through merge `894f3ff5839b940aeddd0965a76b1913f8e16afe` on 2026-10-15. The ordinary primary-checkout `pdm run run-local-pdm handoff-validate` completed with exit 0 on both Mac and Hemma. Before/after SHA-256 checks confirm both original `.env` files are unchanged. Sir production/STT remains offline. Three focused adversarial tests, focused mypy, Ruff and shell/TOML checks passed; no full-suite claim. Exact source review, native check receipts and actual command acceptance are retained under the shared session above.
