## Current

- [TASK-SIRCON-REP-0029](docs/backlog/tasks/task-sircon-rep-0029-repair-exam-net-qti-export-to-the-confirmed-import-contract.md)
  is `done` and live-proven: integrated head `20797ab5` emits an
  `assessmentTest` with manifest dependency wiring, confirmed item lanes
  (`map_response`, exact-sum positive mappings, per-gap score split,
  single-criterion free text, stems inside interaction prompts,
  item-relative images), and fail-closed preflight validators with
  probe-derived fixtures. A teacher-overlay migration bundle imported live
  into Exam.net as seven flat questions with keys and points intact; the
  user confirmed closure on 2026-08-29. The empirical contract is governed
  as `REF-SIRCON-GENERAL-exam-net-qti-import-contract-empirical-observations`
  (stems-in-prompt rule included), superseding the vendor-reported strategy
  reference. Four narrow empirical unknowns stay open in that reference.
- [TASK-SIRCON-08-01-07](docs/backlog/tasks/task-sircon-08-01-07-adopt-remote-answer-key-model-profiles-with-a-daily-token-lease-budget.md)
  is `done`: published revision `a1319739` runs GPT-5.6 Luna as the exam-lane
  low-effort default with GLM-5.3-flash (OpenRouter) as a failover-only backup
  under one 5,000,000 token/day non-refundable UTC lease. Credentialed Hemma
  proofs covered Luna success, one-shot GLM failover with two leases, and
  fail-closed exhaustion with zero provider calls while deterministic artifacts
  continued; canonical API and worker runtime was restored healthy afterward.
- Skriptoteket `EPIC-SKRIPT-39` (active, with accepted `ADR-SKRIPT-0090`) is
  porting the exam-conversion domain into Skriptoteket by incremental
  strangler. Its walking skeleton `TASK-SKRIPT-39-01-01` is `done`
  (2026-08-29): the exam domain chain ported from this repo at `41be61a6`
  produces a byte-identical QTI package (sha256 `f36a4ae3…`) behind a lane
  switch defaulting to the Sir Convert path, proven through the authenticated
  HuleEdu ceremony. This repo stays the default lane until the cutover story;
  Sir Convert then retains heavy OCR/STT behind a generic extraction contract
  and the exam-specific cross-repo schema surface retires with that cutover.
- [TASK-SIRCON-REP-0025](docs/backlog/tasks/task-sircon-rep-0025-complete-operations-handoff-and-parity-gated-governance-retirement.md)
  completed the shared-governance cutover. Product, Hemma, GPU, conversion,
  deployment, and Qwen behavior remain unchanged.
- `TASK-SIRCON-01-05-04` has published its bounded API/GPU-worker startup
  implementation. Its separately authorized Hemma current/stale-image proof
  has not run, so the task remains `in_progress`.
- `TASK-SIRCON-01-05-05` now pins `repository-governance` `0.11.25` at
  `1548765abc4f81e54cbe13f6112163da96fa8842` and contains the static
  Sir workload registry, adapters, inventory, CLI, focused tests, and operator
  contract. The repository-declared `operations` scope and coverage gate pass.
  No Hemma switching or production mutation ran; the task remains
  `in_progress` pending separately authorized live acceptance.
- Root quality has seven Git-derived scopes: `service`, `conversion`, `exam`,
  `speech`, `operations`, `research`, and `repository`. Select the owning scope;
  do not use the broad root aggregate as a routine commit gate.
- Active product authority remains in the current backlog, ADRs, references,
  and runbooks reached through the generated documentation doorway.

## Recent

- TASK-SIRCON-REP-0024 adopted the seven derived quality scopes while keeping
  Qwen as a separate PDM project.
- TASK-SIRCON-REP-0021 organized the root tests by behavior ownership and
  preserved the 1,444-test collection without running it as a cutover gate.
- The current governed corpus uses the shared Docs-as-Code contract; terminal
  records live under the canonical archive and remain historical.

## Facts

- Local commands use `pdm run run-local-pdm ...` when the repository wrapper is
  required.
- Hemma commands use the product-owned `pdm run run-hemma -- ...` transport.
- Qwen owns its separate project, Python constraint, dependencies, lock, and
  product commands.
- Production, deployment, conversion, GPU, training, and remote mutation require
  explicit task authority.

## Roots

- [Documentation](docs/index.md)
- [Backlog](docs/backlog/INDEX.md)
- [References](docs/reference/INDEX.md)
- [Runbooks](docs/runbooks/INDEX.md)
- [Durable session history](.codex/long-term-memory/index.md)
