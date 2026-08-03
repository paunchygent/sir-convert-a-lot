---
type: task
id: TASK-SIRCON-REP-0024
title: Derive service and domain quality checks from behavior-owned tests
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
  approval_evidence: User directed reuse of HuleEdu's Git-derived service/domain design, prohibited a broad root test gate, and authorized this task to proceed without added ceremony on 2026-08-03.
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directed this bounded derived-configuration task to keep moving without needless review ceremony; exact command-boundary proof passed on 2026-08-03.
task_kind: repository
acceptance_criteria:
  - Repository quality projects are derived from the seven behavior-owned root test directories without a selector manifest
  - Named service and domain checks run only their owned scopes while Qwen remains a separate PDM project
  - Focused configuration and command-boundary proof passes without running the broad root aggregate
---

## Context

TASK-SIRCON-REP-0021 organized the root tests into seven behavior-owned
directories, but the shared quality facts are still empty. The existing
`test`/`check` bindings therefore cannot select a service or domain and a broad
root invocation would collect 1,444 tests.

The installed 0.9.17 package already supports the HuleEdu-derived design and
component-boundary test targets. Sir Convert-a-Lot needs consumer facts, not a
new package feature or a selector manifest.

## Impact And Escalation

The write set is `pyproject.toml`, this task, and generated documentation
indexes. Product code, tests, Qwen configuration, shared-package code, public
command names, and broad-suite policy are unchanged.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID     | Type      | Status | Question/Assumption                        | Recommendation/Decision                                                                                                                             | Source                                                      |
| ------ | --------- | ------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| DQ-001 | topology  | closed | How are scopes declared?                   | Declare one `component-root` cohort at `tests/sir_convert_a_lot`; Git-tracked immediate children derive the seven scopes. Add no selector manifest. | User direction; HuleEdu design; retained Explorer discovery |
| DQ-002 | execution | closed | How are tests targeted?                    | Set `test-target = "component"` and dispatch through the existing root `pytest-root` producer. Each named scope receives only its directory.        | Package 0.9.17 contract; TASK-SKILL-REP-0062                |
| DQ-003 | typing    | closed | How is the matching type check selected?   | Dispatch the selected directory through the existing `typecheck-all` producer.                                                                      | Existing Sir command; retained Explorer discovery           |
| DQ-004 | isolation | closed | Does Qwen join the routine root aggregate? | No. Qwen remains a separate setup project and receives no quality project, cohort, producer, or aggregate in this task.                             | User direction; current repository topology                 |
| DQ-005 | proof     | closed | Is the broad root suite required?          | No. Prove the generated plan and one representative named scope at the command boundary, plus configuration/docs checks.                            | User direction                                              |

## Plan

Add one root quality project, two producers, and one Git-derived cohort. Let the
shared package derive `service`, `conversion`, `exam`, `speech`, `operations`,
`research`, and `repository` from the tracked directories.

## Implementation Steps

1. Replace the empty quality project list with the root project and its existing
   typecheck/test producers.
2. Add the single component-root cohort with component test targeting.
3. Inspect the generated plan and run one representative named scope.
4. Synchronize and validate this task and generated indexes.

## Proof

- Configuration/command-boundary proof applies; no product behavior changes.
- Before the change, `pdm run check --plan service` must fail because the quality
  model is empty.
- After the change, `pdm run check --plan service` must select only
  `tests/sir_convert_a_lot/service` for typecheck and test.
- `pdm run check service` must execute that representative named scope without
  collecting the broad root suite.

## Validation

- `pdm run check --plan service`
- `pdm run check service`
- `pdm run docs-sync`
- `pdm run docs-validate docs/backlog/tasks/task-sircon-rep-0024-derive-service-and-domain-quality-checks-from-behavior-owned-tests.md`
- `git diff --check`

## Stop Conditions

- Any need for a selector manifest, seven duplicated scope rows, a shared-package
  change, Qwen inclusion, product/test edits, or a broad root test run.

## Lessons Learned

- A stable directory topology is itself the workload manifest; repeating it in
  configuration creates drift without adding control.

## Notes

Discovery is retained under session
`019fc4ff-75d4-764a-aa7f-3d0dbb71fe5b`. No package version is frozen by this
task; the current immutable consumer pin already provides the required schema.

## Readiness

DQ-001 through DQ-005 are closed by direct user decisions and verified current
repository/package facts. The user explicitly authorized proceeding without
additional review ceremony. Implementation may begin.

## Closeout

Implemented the root quality project, existing-command producers, one
Git-derived behavior cohort, and the normal docs validator. The plan derives
exactly `conversion`, `exam`, `operations`, `repository`, `research`, `service`,
and `speech`. The representative `service` plan targets only
`tests/sir_convert_a_lot/service` for both mypy and pytest; Qwen is absent.

Proof:

- Pre-change `pdm run check --plan service` failed with no valid named scopes.
- Post-change `pdm run check --plan service` returned the seven derived
  components and the focused service command vectors.
- `pdm run check service` passed after formatting the new task record. It ran the
  focused typecheck/test selections, docs validation, and diff check without the
  broad root suite.
- No product code, tests, Qwen facts, shared-package code, coverage command, or
  selector manifest changed.

Independent closeout review is waived under the user's explicit instruction to
reuse the accepted HuleEdu/package pattern and avoid additional ceremony for
this bounded consumer-facts change. Residual risk is limited to the other six
derived scopes not being executed in this task; their exact command vectors are
visible in the successful plan and will run when selected by their owners.
