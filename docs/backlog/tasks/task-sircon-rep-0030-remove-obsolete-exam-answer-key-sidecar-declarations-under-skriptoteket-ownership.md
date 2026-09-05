---
type: task
id: TASK-SIRCON-REP-0030
title: Remove obsolete exam answer-key sidecar declarations under Skriptoteket ownership
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-09-06'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Remove only unused exam answer-key sidecar declarations and dedicated build/config/documentation surfaces under TASK-SKRIPT-39-03-04; preserve generic Qwen tooling, CJ resources, and the active GPU hold; record runtime proof separately without claiming deployment or task completion.
backlog_document_profile: contract-derived
---

## Implementation Contract

Remove the obsolete `sir_convert_qwen_answer_key` sidecar declarations and their
exclusively answer-key build/config/docs/test surfaces under
`TASK-SKRIPT-39-03-04` ownership. The downstream Sir exam API is already gone;
no Skript caller remains; Hemma runs zero qwen containers and holds no
answer-key image. Preserve the generic `qwen/` TTS/finetune project, CJ
experiment resources, shared caches/volumes, STT/OCR, and all active GPU-hold
controls. No runtime operations, no secret reads, no GPU work. Task stays
nonterminal: full runtime proof remains blocked by the CJ hold, and code-state
proof is not runtime image attestation.

## Contract Inputs

- Scaffold commit `5f16fe25` (this PROPOSED shell).
- Prior read-only proof (parent): zero Hemma qwen containers, no answer-key
  image (only the unrelated qwen-finetune image), declaration survives in
  `compose.yaml`, no Skript callers, Sir downstream exam API removed.
- Worktree inspection: no Python source references the answer-key provider;
  all first-party `qwen/` code is free of `llama.cpp-qwen35`/provider-build use.
- Ownership boundary: `ST-SIRCON-07-04` S5 and `TASK-SIRCON-07-04-01` T5 keep
  Qwen sidecar retirement with Skriptoteket Task 04; this task is declaration
  cleanup serving Skript 03-04, not broad product work.
- `TASK-SIRCON-01-05-06` hold governs how the operational hold was applied;
  this task executes no hold change and relaxes nothing.

## Core Vertical And Performance

One declaration vertical, removed end to end: `compose.yaml` service block →
`Dockerfile.qwen-provider` → `qwen-llama-provider-build.sh` plus its two PDM
entries → workload-registry Qwen branches in `hemma_workload.py` → the
`bounded_production_startup.py` exclusion entry → contract-test coverage →
current operational doc rows (service-ops runbook, GPU-runbook probe
language, code-map Dockerfile listings). Shared files lose only their
answer-key branches; production/STT/reserved-edge declarations, conflict
controls, and generic startup behavior are unchanged. No performance work;
removal only shrinks declaration parsing.

## Validation

- Rendered compose structure and workload-registry behavior tests proving
  service absence (no prose/file-existence pinning).
- Named affected `operations` checks only, plus `docs-sync`, `docs-validate`,
  `skills-validate`, `handoff-validate`, and `git diff --check`. No full-repo
  suite, no Hemma calls, no GPU work.
- Evidence pack returned for final Sol review; closeout stays nonterminal.

## Stop Conditions

- A candidate file is shared with generic Qwen/CJ/STT/OCR/hold behavior beyond
  its answer-key branch: preserve the shared parts and flag it.
- The provider build script shows a genuine remaining consumer: stop that
  deletion and report it.
- Any step needs Hemma runtime action, secrets, or GPU work: stop and record.
- `TASK-SIRCON-01-05-05` and other historical task records are not rewritten;
  the current registry correction lives in operational docs and here. Its
  evidence paragraph describing the adopted three-target registry is superseded
  for the Qwen row only: the live registry declares production, STT sidecar,
  and the passive reserved edge.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 | Cleanup first: this declaration cleanup runs before Skript DOCX work under TASK-SKRIPT-39-03-04.                                                           |
| D02 | Declaration-only scope: remove the `sir_convert_qwen_answer_key` compose service plus exclusively answer-key Dockerfile/build/settings/docs/test surfaces. |
| D03 | Preservation set: generic `qwen/` project, Qwen CJ experiment, finetune image, shared caches/volumes, STT/OCR, and all active GPU-hold controls survive.   |
| D04 | Boundary: ST-SIRCON-07-04 S5 and TASK-SIRCON-07-04-01 T5 exclude Qwen; this task serves Skript 03-04 and is not broad product work.                        |
| D05 | No runtime operations: no restart/removal/provider calls, no secret reads, no GPU workloads; code-state proof is not runtime image attestation.            |
| D06 | The provider build script and its two PDM entries are removed on confirmed exclusive answer-key use; any genuine shared consumer stops that deletion.      |
| D07 | Closed historical task records are not rewritten; the current registry correction lives in operational docs and this task.                                 |
| D08 | User authority (later explicit cleanup decision) covers these declaration-only edits; the 01-05-06 hold is neither executed nor relaxed.                   |
| D09 | Review path: no Sol planning review; Sol only final. No staging, commits, branches, merges, or pushes from this worktree.                                  |
