# Task 255 Service Dependency Image Cache Report

Status: passed.

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

Detached Hemma proof ran from the canonical remote repo after `main` was
updated to commit `7173c03f8b414caa7fa1e9c84a0c6b33b5b357b8`.

Detached commands:

```bash
pdm run run-local-pdm hemma-command-start task255-prod-deps-rocm-build-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-deps-rocm-build
pdm run run-local-pdm hemma-command-start task255-prod-app-only-build-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-build
pdm run run-local-pdm hemma-command-start task255-prod-recreate-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-recreate sir_convert_a_lot_prod
```

Remote logs captured locally:

- `prod-deps-rocm-build.log`
- `prod-app-only-build.log`
- `prod-recreate.log`
- `prod-compose-ps.json`
- `buildkit-cache-summary-hemma-after.txt`

Results:

- Dependency image build used BuildKit pip cache mounts for normal
  requirements and ROCm torch wheel downloads.
- ROCm torch, torchvision, torchaudio, and triton-rocm installed only in the
  dependency image lane.
- EasyOCR detection and recognition models preloaded only in the dependency
  image lane.
- Dependency image tag:
  `sir-convert-a-lot-deps-rocm:958c03d4fceb446ba95eec0681c7d51c07de8d9c02595e962e282a7cdd22b690`.
- App-only production build consumed the dependency image directly and copied
  app/runtime source without rerunning pip, ROCm torch, or EasyOCR preload.
- Production recreate reused cached runtime layers and started
  `sir_convert_a_lot_prod` healthy on `127.0.0.1:28085->8085/tcp`.

`prod-deps-rocm-build-clean` was not run as part of this normal proof because
the Task 255 proof was intentionally non-destructive; the clean rebuild command
surface is reserved for explicit cold dependency rebuild testing.
