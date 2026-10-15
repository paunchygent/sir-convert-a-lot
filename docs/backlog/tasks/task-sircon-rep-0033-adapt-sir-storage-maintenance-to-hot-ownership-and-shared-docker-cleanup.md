---
type: task
id: TASK-SIRCON-REP-0033
title: Adapt Sir storage maintenance to Hot ownership and shared Docker cleanup
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-10-15'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer and skill-prose-reviewer
  decided_at: '2026-10-15T10:31:38Z'
  approval_protocol: agent-implementation:approved-review-closeout
  approval_evidence: Independent code R1-R3 rereview and prose R1-R3 rereview approved the exact source bytes; parent retained root 01a13b6a-e17a-7255-8b11-da4f26bf7427 holds both reports and manifests.
task_kind: repository
acceptance_criteria:
  - Sir refuses legacy Docker cleanup requests before any mutation and delegates cleanup ownership to shared weekly hemma-docker-cleanup.
  - Nonvisual build, proof and legacy archive defaults use Hot owner job storage while preserving logical paths and existing producer protections.
  - Focused source checks pass and the unactivated runtime boundary is explicit.
backlog_document_profile: contract-derived
---

## Implementation Contract

Adapt Sir storage and scratch-maintenance source to the accepted shared Hemma
storage contract. Remove overlapping container, image, volume and builder prune
fallbacks. Refuse legacy cleanup flags at CLI and runtime/template boundaries
before mutation. Keep report compatibility where useful.

Place nonvisual generated build/proof and legacy evacuation archives under the
Hot-backed home owner workspace, preserving repository and Docker-visible logical
paths. The backup SSD is backup only. Preserve age, newest-count, free-space,
pin and active-work protections; add no retention horizon or model classification.
This assignment changes source only. Installation, moves, host rewrites, timer
activation, GPU work and production acceptance remain outside this task's execution.

Declare the existing isolated Qwen test/typecheck ownership in root quality
metadata so shared storage changes can reach their named operations check.
Use a target-only pytest entrypoint in the existing Qwen project; preserve its
separate dependency boundary and existing default test command.

## Contract Inputs

- Accepted cross-repository authority: skill-repository TASK-SKILL-REP-0316,
  decisions D05, D09 and D11, accepted 2026-10-15.
- Parent retained root: `01a13b6a-e17a-7255-8b11-da4f26bf7427` in the canonical
  skill repository; source assignment `sir-storage-cleanup-adapter`.
- Existing producer source and TASK-SIRCON-05-05-02/03 are historical behavior
  inputs; this contract supersedes their scratch/bulk placement and Docker fallback.

## Core Vertical And Performance

Legacy command or timer configuration reaches the refusal before output, archive,
migration or host mutation; ordinary owner maintenance keeps its selected-path
policy. Fresh execution units cover Docker cleanup refusal and Hot placement;
the implementation lead integrates and proves the source boundary. No benchmark
or workload execution is required.

## Validation

- Focused operations tests for scratch policy/maintenance, storage remediation
  and affected Docker-bind contracts; Qwen common-storage tests when changed.
- Adversarial assertions that obsolete flags cannot invoke pruning or mutate
  files, including direct runtime and timer rendering/install calls.
- Named `operations` check plan and affected checks through `run-local-pdm`;
  scoped docs validation, handoff validation and `git diff --check`.

## Stop Conditions

- Return material owner/path or active-work conflicts to the assigning parent.
- Preserve other writers and protected `.orchestration`; no Git lifecycle actions.
- Do not deploy, restart, prune, move or delete host state. Live acceptance needs
  the parent's later writer-safe cutover and producer activation authority.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Closed: shared weekly hemma-docker-cleanup is the sole Docker cleanup owner; refuse Sir legacy cleanup requests (0316 D05).                   |
| D02 | Closed: nonvisual build/proof/archive uses Hot owner jobs at preserved logical paths; scratch holds visual churn only (0316 D09).             |
| D03 | Closed: backup SSD stores backups, never Sir primary archive; no new model classification or retention rule (0316 D11 and accepted plan).     |
| D04 | Closed: source-only execution, existing producer protections preserved; parent owns publication and activation (explicit assignment).         |
| D05 | Closed: repair missing Qwen quality ownership exposed by the required operations plan, using existing isolated producers and focused targets. |

## Source Closeout

Independent code reviewer `01a13ef8-4ae3-77a1-9d02-84dfb5ddf197` approved the
repaired source on 2026-10-15; report
`evidence/reviews/sir-storage-cleanup-adapter/rereview.md` in the parent root
above. Downstream Hot paths, resolved archive aliases and conflicting-payload
preservation findings are cleared. The exact reviewed manifest is
`df1d2da0d727312655befe916b68e4cd012f1ebd42f1f7076b41d58c702ad49b`.

Independent prose reviewer `01a13f0f-761e-74c3-9e4c-66766206f5ee` approved both
repaired runbooks at 10:27:11 UTC; report
`evidence/reviews/sir-storage-prose-review/rereview-1.md` records their exact
hashes. The shared migration runbook must be published through its canonical
alias before consumers use that route.

The named operations check passed with 52 operations tests and focused types,
format, lint and documentation checks; the isolated Qwen targets passed 28 tests
and focused typechecking. These source checks establish no observed Hot backing,
Docker bind, migration, timer or GPU behavior. Physical activation remains
TASK-SKILL-REP-0316-owned; preserve its held writer boundary and disabled hourly
timer until that procedure admits activation. Parent owns merge-only local
integration and main-only publication.
