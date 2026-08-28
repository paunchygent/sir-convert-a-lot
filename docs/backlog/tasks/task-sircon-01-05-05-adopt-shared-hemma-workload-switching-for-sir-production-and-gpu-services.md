---
type: task
id: TASK-SIRCON-01-05-05
title: Adopt shared Hemma workload switching for Sir production and GPU services
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-28'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Sir API, GPU worker, and required sidecars declare exact resource claims, conflicts, bounded commands, readiness, and terminal outcomes for the shared workload-switch package.
  - The shared transaction never starts excluded Qwen, training, benchmark, reserved-edge, or unrelated sidecar services and restores only recorded prior Sir services.
  - GPU readiness targets the GPU worker, preserves no-CPU-fallback behavior, and depends on the bounded startup command owned by TASK-SIRCON-01-05-04.
story: ST-SIRCON-01-05
dependencies:
  - TASK-SIRCON-01-05-04
  - Skill Repository TASK-SKILL-05-10-01
backlog_document_profile: contract-derived
---

## Implementation Contract

After `TASK-SIRCON-01-05-04` delivers bounded production startup and
`TASK-SKILL-05-10-01` releases the shared package, pin that exact provider
revision and declare Sir production API, GPU worker, and required sidecar
relationships. Declare exact GPU/resource claims, conflicts, bounded commands,
readiness, timeouts, terminal outcomes, and restart-policy expectations.

The adapter must use the bounded startup command, target GPU proof at
`sir_convert_a_lot_gpu_worker`, and preserve strict no-CPU-fallback behavior. It
must never cause Compose dependency expansion to start undeclared STT, Qwen,
training, benchmark, reserved-edge, or other services. Restore only Sir services
recorded in the transaction receipt.

## Contract Inputs

- `TASK-SIRCON-01-05-04` bounded startup command and exact revision/GPU
  readiness authority.
- Skill Repository `ST-SKILL-05-10` and released
  `TASK-SKILL-05-10-01` package identity.
- Current Sir API, GPU worker, sidecar, ROCm device, `/readyz`, and restart-policy
  contracts.
- Hule `TASK-HULE-09-02-26` integration coordinator.

## Core Vertical And Performance

Through the real shared adapter, inventory Sir service state, displace only a
declared GPU conflict, start and verify the selected Sir target through the
bounded command, stop it, and restore only recorded prior services. Prove that
all excluded service identities remain unchanged.

The transaction adds no conversion request to ordinary startup. GPU device and
runtime visibility are bounded readiness checks; live conversion remains a
separately authorized acceptance action. No dependency-image rebuild or broad
Compose recreate is permitted.

## Validation

- Focused adapter tests assert exact service membership, `--no-deps` behavior,
  resource claims, excluded-service identity, bounded outcomes, GPU-worker
  target, no CPU fallback, and exact restoration.
- Retain the focused bounded-startup, Compose-contract, deploy, and GPU-runtime
  tests owned by `TASK-SIRCON-01-05-04`.
- Run repository format, lint, typecheck, coverage, docs/skills/handoff gates,
  and `git diff --check` required by the current repository contract.
- Real Hemma switching and any live conversion proof require separate explicit
  runtime authority after all exact revisions are released.

## Stop Conditions

- The bounded startup task is not delivered or its exact command/outcome is
  unavailable.
- The exact shared-package release or immutable pin is unavailable.
- Compose would start an undeclared dependency or mutate an excluded service.
- GPU proof targets the CPU-only API, GPU visibility fails, or CPU fallback is
  possible.
- A Sir service is unknown, stale, or cannot be restored to its recorded state.
- Adoption would duplicate shared transaction storage or restoration logic.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------- |
| D01 | Sir owns exact API/GPU/sidecar declarations and commands; the shared package owns switching state and restore policy. |
| D02 | Adoption depends on the bounded startup command in `TASK-SIRCON-01-05-04` and one exact shared-package release.       |
| D03 | GPU readiness targets the GPU worker and retains strict no-CPU-fallback behavior.                                     |
| D04 | Undeclared STT, Qwen, training, benchmark, reserved-edge, and unrelated services remain untouched.                    |
| D05 | Restoration starts only the exact Sir services recorded before displacement.                                          |

## Implementation Evidence

- The consumer pins immutable `repository-governance` `0.11.25` at
  `1548765abc4f81e54cbe13f6112163da96fa8842`. The inadmissible `0.11.24`
  release is not present in the consumer pin or lock.
- `scripts/sir_convert_a_lot/devops/hemma_workload.py` declares the closed
  `sir-production`, `sir-stt-sidecar`, and `sir-qwen-answer-key` registry.
  Each target claims `gpu:amdgpu`; the three targets are pairwise conflicts.
  Inventory refuses partial production state, unknown Sir containers, malformed
  ROCm output, and nonzero-VRAM PIDs outside the exact declared containers.
- Production start delegates to the Task 04 `prod-start-bounded` command and
  its exact revision, `/readyz`, GPU-worker, and no-CPU-fallback checks.
  Production stop names only `sir_convert_a_lot_gpu_worker` and
  `sir_convert_a_lot_prod`. Sidecar adapters start and stop only their exact
  pre-existing containers and require bounded health readiness plus the
  declared restart policy.
- `scripts/sir_convert_a_lot/devops/hemma_workload_cli.py` exposes only shared
  start, stop, and restore commands after the Hemma Server guard. The provider
  owns the receipt, lock, transaction, and recovery policy under
  `/var/lib/hemma/workload-switch`; the consumer adds no duplicate switching
  state.
- The operations runbook records the exact owner command syntax, target
  identities, state ownership, exclusions, and separate runtime-authority gate.

## Validation Evidence

- Retained command
  `.orchestration/context/sessions/01a04756-9b0d-7fad-8b48-4aaa8b42d3b3/operational-output/commands/01a04754-bf8f-7372-8ec8-9c7db750865f/0006-pdm-run-check-operations`
  passed the repository-declared `operations` scope with no failed phases.
  The operations cohort reported 271 passing tests, including the Task 04
  bounded-startup, Compose, deploy, and GPU-runtime regressions.
- Retained command
  `.orchestration/context/sessions/01a04756-9b0d-7fad-8b48-4aaa8b42d3b3/operational-output/commands/01a04754-bf8f-7372-8ec8-9c7db750865f/0005-pdm-run-coverage-gate`
  passed with 1,521 tests passing, 6 skipped, and 95.57% coverage against the
  repository's established conversion-core coverage target. The preceding
  retained run `0004-pdm-run-coverage-gate` reached the same coverage but
  exposed one order-sensitive speech-test failure; that exact test and its
  immediate predecessor passed in isolation, no speech source was changed, and
  the full rerun passed.
- No Hemma switching, Docker daemon, production service, GPU, deployment, or
  live conversion action ran. Real Task 05 switching remains separately
  authorized acceptance work, so this task remains `in_progress`.
