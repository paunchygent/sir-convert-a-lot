## Current

- [TASK-SIRCON-REP-0029](docs/backlog/tasks/task-sircon-rep-0029-repair-exam-net-qti-export-to-the-confirmed-import-contract.md)
  is `in_progress` with the writer repair implemented: packages now emit an
  `assessmentTest` (`imsqti_test_xmlv2p1`) with manifest dependency wiring;
  choice/matching items emit `correctResponse` plus positive exact-sum
  mappings and `map_response` (no `match_correct`, no `shuffle`); gap items
  split the item score per gap; keyed free text emits one full-score
  criterion mapping; five content validators and the probe-derived
  `test_examnet_qti_contract_rules.py` fixtures enforce the contract.
  `pdm run check exam` passes with no failed phases; sample packages are
  regenerated. The empirical contract is governed as
  `REF-SIRCON-GENERAL-exam-net-qti-import-contract-empirical-observations`,
  superseding the vendor-reported strategy reference. Remaining acceptance
  gate: live Exam.net import proof of a regenerated package. Planning
  session `01a048d5-69f7-7394-93dd-8ff91af608cd` absorbed diagnostic session
  `01a0474c-158e-7bf1-85ae-6adb4198c143` and its validated boundary ledger.
- [TASK-SIRCON-08-01-07](docs/backlog/tasks/task-sircon-08-01-07-adopt-remote-answer-key-model-profiles-with-a-daily-token-lease-budget.md)
  is `ready`: exam-lane answer-key completion moves to a GPT-5.6 Luna
  low-effort default with GLM-5.3-flash (OpenRouter) failover-only backup and
  a 5,000,000 token/day non-refundable lease (UTC-midnight reset, fail-closed
  exhaustion).
- Skriptoteket `EPIC-SKRIPT-39` (proposed, with `ADR-SKRIPT-0090`) will port
  the exam-conversion domain into Skriptoteket by incremental strangler after
  the two tasks above land; Sir Convert then retains heavy OCR/STT behind a
  generic extraction contract and the exam-specific cross-repo schema surface
  retires with that cutover.
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
