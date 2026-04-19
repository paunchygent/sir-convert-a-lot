---
type: agent_session_handoff
id: sir-convert-a-lot-handoff
status: active
created: '2026-04-16'
last_updated: '2026-04-19'
---

## Purpose

Keep only volatile Sir Convert-a-Lot agent state, blockers, validation evidence,
and next actions. Move durable session history to
`.codex/long-term-memory/entries/` and governed doctrine to docs, rules,
runbooks, or skills.

## Current State

- The current active implementation lane is now the Epic 03 / Story 05 DevOps
  lane for Hemma-hosted service operations.
- Task 254 remains the immediate production recovery authority for detached
  deploy verification, public HTTPS proof, and reserved default-host behavior.
- Task 255 is completed and pushed to `main`. Dependency image inputs live
  under `docker/service-deps/`, `Dockerfile.deps` owns ROCm/CPU dependency
  images, and production/local runtime Dockerfiles consume explicit
  `DEPS_IMAGE` app layers.
- Review 05 Task 255 follow-up is completed and pushed to `main`. Dependency
  image freshness now includes build-recipe truth through a separate recipe
  hash, a combined dependency-image hash, and Docker label verification before
  accepting existing dependency image tags.
- Epic 09 is proposed for the Sir Convert Gateway cutover. ADR-0009, Stories
  33-37, Tasks 256-264, and
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md` now
  govern the planning path. Task 256 must inventory all callers/access lanes
  before any public route is removed or repointed.
- ADR-0009 review feedback has been incorporated into the planning spine:
  Sir Convert consumes HuleEdu `InternalIdentityContextV1` with audience
  `sir-convert-a-lot` instead of minting a parallel identity contract, Task 259
  is a hard prerequisite for ADR acceptance, user-originated backend jobs must
  carry context-derived ownership, unknown public consumers require empirical
  public-edge evidence, and `convert.hule.education` defaults to a fail-closed
  reserved posture after cutover.
- Third-pass review approved the Epic 09 planning spine. Keep ADR-0009
  proposed until Task 259 locks the Sir-specific `InternalIdentityContextV1`
  authorization profile and proves non-browser service/operator extensions do
  not introduce a second signed issuer or browser-adjacent auth path.
- Task 265 is in progress for pre-cutover public-edge isolation:
  `sir_convert_a_lot_prod` should stay internal/tunnel reachable, while
  `sir_convert_a_lot_public_reserved` owns `convert.hule.education` and returns
  the reserved non-product public response until the Gateway cutover deliberately
  re-enables the intended public edge.
- `TASK-0046` compacted this handoff, moved durable March 2026 history into
  long-term memory, and added the real `pdm run handoff-validate` command
  surface.
- `TASK-0043` completed the direct governance cutover from `.agents/` paths to
  `.codex/` paths. Do not recreate compatibility shims.
- `TASK-0045` added the shared command grammar now available in this repo:
  `pdm run docs-validate` and `pdm run skills-validate`.
- Generated repomix packages belong under ignored `.codex/repomix_packages/`;
  do not track generated XML packages.

## Active Pointers

- Active planning log: `docs/backlog/current.md`.
- Active DevOps story: `docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md`.
- Active public-edge recovery task: `docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md`.
- Active dependency-image follow-up task: `docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md`.
- Active Gateway cutover planning epic:
  `docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md`.
- Gateway cutover inventory reference:
  `docs/reference/ref-sir-convert-gateway-cutover-caller-inventory.md`.
- Active Qwen Task 101 ledger:
  `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`.
- Qwen experiment governance:
  `.codex/rules/096-qwen-experiment-governance.md`.
- Hemma/Qwen runbook:
  `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`.
- Durable session-history index:
  `.codex/long-term-memory/index.md`.

## Durable Memory

- TASK-0043 governance cutover memory:
  `.codex/long-term-memory/entries/session-2026-04-16-task-0043.md`.
- March 2026 service, local runtime, service image, and Qwen operator
  history compacted from the former long handoff:
  `.codex/long-term-memory/entries/session-2026-03-25-service-and-qwen-operator-history.md`.

## Next Actions

1. Finish Task 254 by making `hemma-deploy-and-verify` deploy-detached-aware
   and by emitting durable public-edge/default-host artifacts in the canonical
   report.
1. Start Epic 09 with Task 256: inventory HuleEdu, Skriptoteket, internal
   service, public direct, and local operator Sir Convert callers in the
   gateway cutover inventory reference before implementation.
1. Before any future Hemma Qwen run, use:
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   and
   `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`.

## Validation

- 2026-04-19 Task 255 focused checks:
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_service_dependency_inputs.py tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_export_service_requirements.py tests/sir_convert_a_lot/test_service_image_build_contract.py -q`
  passed.
- 2026-04-19 Task 255 full local gates passed:
  `pdm run docs-validate`; `pdm run skills-validate`;
  `pdm run handoff-validate`; `pdm run format-all`; `pdm run lint-fix`;
  `pdm run typecheck-all`;
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`;
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "service_image or compose or dockerfile" -q`;
  `pdm run coverage-gate`;
  `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`;
  `git diff --check`.
- 2026-04-19 Task 255 detached Hemma proof passed from commit
  `7173c03f8b414caa7fa1e9c84a0c6b33b5b357b8`: ROCm dependency image
  `sir-convert-a-lot-deps-rocm:958c03d4fceb446ba95eec0681c7d51c07de8d9c02595e962e282a7cdd22b690`
  built with BuildKit pip cache mounts, app-only `prod-build` reused the
  dependency image without rerunning heavy dependency work, and
  `prod-recreate sir_convert_a_lot_prod` started healthy. Final artifacts are
  under `build/verification/task-255-service-deps-image-cache/`.
- 2026-04-19 Review 05 follow-up proof passed from commit
  `d23855375ec848a8c45ae40d43e23c4f8b23d319`: ROCm dependency image
  `sir-convert-a-lot-deps-rocm:b6265e4ee42c43c255e400bc1516cc04d8601ceaf6961008dc09ad7a60f6df89`
  carries matching dependency, recipe, and dependency-image labels. Detached
  app-only `prod-build` reused that image without rerunning ROCm torch or
  EasyOCR, and detached `prod-recreate sir_convert_a_lot_prod` started
  healthy on `127.0.0.1:28085->8085/tcp`.
- 2026-04-19 Epic 09 docs-governance slice:
  ADR-0009 review feedback incorporated and third-pass review approved the
  planning spine. Final closeout gates after the latest handoff/current update:
  `pdm run docs-validate`;
  `pdm run skills-validate`; `pdm run handoff-validate`;
  `pdm run index-tasks --root docs/backlog --out /tmp/sir_tasks_index_final_rereview.md --fail-on-missing`;
  `git diff --check`.
- `pdm run ruff format scripts/docs_as_code/validate_handoff.py`: passed
- `pdm run ruff check scripts/docs_as_code/validate_handoff.py`: passed
- `pdm run handoff-validate`: passed
- `pdm run docs-validate`: passed
- `pdm run skills-validate`: passed
- `git diff --check`: passed
- Skill-repository closeout also passed:
  `pdm run docs-sync`, `pdm run docs-validate`, and `git diff --check`.

## Stop Conditions

- Stop before deleting durable Qwen, service, or Hemma evidence that is not
  already preserved in governed docs or long-term memory.
- Stop before changing service runtime behavior, Hemma deployment semantics,
  generated artifact retention, or Qwen experiment interpretation.
