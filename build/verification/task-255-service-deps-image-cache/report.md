# Task 255 Service Dependency Image Cache Report

Status: partial local pass, Hemma proof pending.

## Dependency Hash Proof

- ROCm dependency hash before script-only change:
  `958c03d4fceb446ba95eec0681c7d51c07de8d9c02595e962e282a7cdd22b690`
- ROCm dependency hash after script-only change:
  `958c03d4fceb446ba95eec0681c7d51c07de8d9c02595e962e282a7cdd22b690`
- ROCm dependency hash after controlled runtime dependency delta:
  `cdbccff98310cf4a564d811307d8312da1f85ecd0ac913a317ff18ef6733cb42`

Result: script-only changes do not move the dependency hash; runtime dependency
truth changes do move it.

## Local Gates

- `pdm run docs-validate`: passed
- `pdm run skills-validate`: passed
- `pdm run handoff-validate`: passed
- `pdm run format-all`: passed
- `pdm run lint-fix`: passed
- `pdm run typecheck-all`: passed
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_local_compose_contract.py -q`:
  passed
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot -k "service_image or compose or dockerfile" -q`:
  passed
- `pdm run coverage-gate`: passed
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`:
  passed
- `git diff --check`: passed

## Hemma Proof

Pending. The implementation is currently local worktree state, so the detached
Hemma proof must run after these changes are available in the canonical remote
repo through Git.

Required detached commands:

```bash
pdm run run-local-pdm hemma-command-start task255-prod-deps-rocm-build -- pdm run prod-deps-rocm-build
pdm run run-local-pdm hemma-command-monitor -- <remote-deps-build-log-path>
pdm run run-local-pdm hemma-command-start task255-prod-app-only-build -- pdm run prod-build
pdm run run-local-pdm hemma-command-monitor -- <remote-app-build-log-path>
pdm run run-local-pdm hemma-command-start task255-prod-recreate -- pdm run prod-recreate sir_convert_a_lot_prod
pdm run run-local-pdm hemma-command-monitor -- <remote-recreate-log-path>
```
