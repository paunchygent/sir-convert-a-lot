## Current

- [TASK-SIRCON-REP-0025](docs/backlog/tasks/task-sircon-rep-0025-complete-operations-handoff-and-parity-gated-governance-retirement.md)
  completed the shared-governance cutover. Product, Hemma, GPU, conversion,
  deployment, and Qwen behavior remain unchanged.
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
