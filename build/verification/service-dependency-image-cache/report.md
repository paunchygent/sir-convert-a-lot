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

## Recipe Freshness Proof

- Current recipe hash:
  `b73103f7eb1258eb7be902b74b10675cbd92c6c14db4e0c0c5c29d72ebc6f81f`
- Current ROCm deploy-facing dependency image hash:
  `b6265e4ee42c43c255e400bc1516cc04d8601ceaf6961008dc09ad7a60f6df89`
- Current CPU deploy-facing dependency image hash:
  `e012fe9dd168bd4c4f163026be4840e7b244956c9c8c0d891a08f226941790ff`

Result: the package-only dependency hash stays narrow, while the deploy-facing
dependency image identity also changes when `Dockerfile.deps`, the dependency
image helper, the dependency-input generator, `PYTHON_IMAGE`, system packages,
pip policy, BuildKit cache mounts, or EasyOCR preload command contract change.
Hemma image labels were verified in
`dependency-image-labels-after-recipe-fix.json`.

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
updated to commit `7173c03f8b414caa7fa1e9c84a0c6b33b5b357b8`, then the
Review 05 recipe-freshness follow-up ran from
`d23855375ec848a8c45ae40d43e23c4f8b23d319`.

Detached commands:

```bash
pdm run run-local-pdm hemma-command-start task255-prod-deps-rocm-build-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-deps-rocm-build
pdm run run-local-pdm hemma-command-start task255-prod-app-only-build-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-build
pdm run run-local-pdm hemma-command-start task255-prod-recreate-sudo-snap -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-recreate sir_convert_a_lot_prod
pdm run run-local-pdm hemma-command-start task255-review05-prod-build-warmup -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-build
pdm run run-local-pdm hemma-command-start task255-review05-app-only-build -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-build
pdm run run-local-pdm hemma-command-start task255-review05-prod-recreate -- sudo -n env PATH=/home/paunchygent/.local/bin:/snap/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /home/paunchygent/.local/bin/pdm run prod-recreate sir_convert_a_lot_prod
```

Remote logs captured locally:

- `prod-deps-rocm-build.log`
- `prod-app-only-build.log`
- `prod-recreate.log`
- `prod-build-recipe-warmup.log`
- `prod-app-only-build-recipe-labels.log`
- `prod-recreate-recipe-labels.log`
- `dependency-image-labels-after-recipe-fix.json`
- `prod-compose-ps-after-recipe-fix.txt`
- `prod-compose-ps.json`
- `buildkit-cache-summary-hemma-after.txt`
- `buildkit-cache-summary-recipe-fix-after.txt`

Results:

- Dependency image build used BuildKit pip cache mounts for normal
  requirements and ROCm torch wheel downloads.
- ROCm torch, torchvision, torchaudio, and triton-rocm installed only in the
  dependency image lane.
- EasyOCR detection and recognition models preloaded only in the dependency
  image lane.
- Dependency image tag:
  `sir-convert-a-lot-deps-rocm:b6265e4ee42c43c255e400bc1516cc04d8601ceaf6961008dc09ad7a60f6df89`.
- Dependency image labels matched dependency hash
  `958c03d4fceb446ba95eec0681c7d51c07de8d9c02595e962e282a7cdd22b690`,
  recipe hash
  `b73103f7eb1258eb7be902b74b10675cbd92c6c14db4e0c0c5c29d72ebc6f81f`,
  and combined dependency-image hash
  `b6265e4ee42c43c255e400bc1516cc04d8601ceaf6961008dc09ad7a60f6df89`.
- App-only production build consumed the dependency image directly and copied
  app/runtime source without rerunning pip, ROCm torch, or EasyOCR preload.
- Production recreate reused cached runtime layers and started
  `sir_convert_a_lot_prod` healthy on `127.0.0.1:28085->8085/tcp`.

`prod-deps-rocm-build-clean` was not run as part of this normal proof because
the Task 255 proof was intentionally non-destructive; the clean rebuild command
surface is reserved for explicit cold dependency rebuild testing.
