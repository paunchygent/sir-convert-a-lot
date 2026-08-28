---
type: task
id: TASK-SIRCON-01-05-04
title: Bound Hemma production startup to API revision and GPU readiness
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: ready
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-01-05
task_kind: story
acceptance_criteria:
- A current API starts without any dependency-image helper invocation and passes exact
  `/readyz` revision/profile/data-root parity.
- A stale API builds and recreates only `sir_convert_a_lot_prod`; GPU worker, STT,
  Qwen, dependency-image, and persistent-data identities remain unchanged.
- No stale application image can report current solely because Compose injected current
  revision environment values; the selected image labels, tag, and ID prove its source
  revision and dependency identity before start.
- "`--no-deps` prevents the GPU worker's Compose dependency edge from starting STT, and before/after identity evidence proves every excluded service stayed untouched."
- GPU proof targets `sir_convert_a_lot_gpu_worker` and proves ROCm torch, `/dev/kfd`,
  `/dev/dri`, and `rocm-smi` visibility.
- API and GPU worker finish with source and live `restart=no`; mismatch is a failing
  result.
- Failure retains the failed boundary and never falls back to CPU, broad recreate,
  dependency rebuild, or unrelated service startup.
- The command terminates within 120 seconds, prints exactly one final accepted outcome,
  and returns zero only for `succeeded`.
retired_ids:
- task-384-bound-hemma-production-startup-to-api-revision-and-gpu-readiness
backlog_document_profile: contract-derived
---

## Implementation Contract

Deliver one on-Hemma `pdm run prod-start-bounded` command that admits an exact
repository revision and already-present hash-addressed ROCm dependency image,
starts only the production API and GPU worker, proves API readiness and worker
GPU visibility, and leaves both selected services at `restart=no`.

The command may build the exact application image and force-recreate only
`sir_convert_a_lot_prod` when the API is stale. It must not invoke the
dependency-image helper, rebuild dependencies, recreate a stale running GPU
worker, expand Compose dependencies, start excluded services, mutate persistent
data, run a live conversion, or fall back to CPU.

## Contract Inputs

- `ST-SIRCON-01-05` and its accepted product-owned bounded-startup slice.
- The closed Task 384 decisions and approved final plan rereview recorded at
  `2026-07-29T18:45:05+02:00`.
- Existing Compose service topology, `/readyz` contract, dependency-image
  identity computation, application Dockerfile, GPU verifier, and Hemma command
  wrappers.
- Existing operator-started restart-policy and shared staged-restart outcome
  vocabulary.

## Core Vertical And Performance

Compute repository `HEAD` and the expected ROCm dependency hash without
calling `service-deps-image.sh`. Require the exact hash-addressed dependency
image and its dependency, recipe, and hash labels. Require or build
`sir-convert-a-lot-runtime:<HEAD>` with immutable OCI revision and dependency
hash labels before Compose receives that tag.

Snapshot the API, worker, STT, Qwen, training, benchmark, and reserved-edge
container identities and states. Start an absent or stopped API and worker
separately with `up -d --no-deps --no-build`. For a stale API, force-recreate
only `sir_convert_a_lot_prod`; a stale running worker is a stop condition.
Within 120 seconds, require exact `/readyz` revision, production profile, and
data-root parity; then target the existing GPU verifier at
`sir_convert_a_lot_gpu_worker`, apply and verify `restart=no` for both
selected services, and prove every excluded identity stayed unchanged.

The command prints exactly one final `outcome=<value>` line. Only
`outcome=succeeded` exits zero. `timed_out`, `dependency_unhealthy`, and
`failed` retain the failed boundary diagnostics and exit non-zero. Startup
adds no live conversion workload and performs no broad rebuild or recreate.

## Validation

- `pdm run pytest-root tests/sir_convert_a_lot/operations/test_bounded_production_startup.py -q`
- `pdm run pytest-root tests/sir_convert_a_lot/operations/test_compose_contract.py tests/sir_convert_a_lot/operations/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/operations/test_verify_hemma_gpu_runtime.py -q`
- `pdm run coverage-gate`
- Inspect `pdm run check --plan operations`, then run `pdm run check operations`.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Retain one real-Hemma current-revision packet and one genuinely older
  application-image packet. Stop rather than fabricate older provenance.

## Stop Conditions

- The required remote revision, expected hash-addressed ROCm dependency image,
  or any required dependency identity label is absent or mismatched.
- The selected application tag lacks exact revision and dependency labels, or a
  genuine older application image is unavailable for the stale proof.
- `/readyz` cannot prove exact revision, production profile, and data-root
  parity within 120 seconds.
- GPU proof targets the CPU-only API, cannot prove ROCm torch, `/dev/kfd`,
  `/dev/dri`, and `rocm-smi`, or requires unrelated workload startup.
- A running GPU worker has stale application provenance.
- Any path would invoke dependency-image ensure, rebuild ROCm dependencies,
  mutate volumes or data, recreate a service other than the stale API, or
  create, start, stop, or recreate an excluded service.
- Source or live restart-policy truth cannot be made and verified `no` for
  both selected operator-started services.

## Decided Contract Terms

| ID | Decided contract term |
| --- | --------------------- |
| D01 | The bounded command owns only `sir_convert_a_lot_prod` and `sir_convert_a_lot_gpu_worker`; all other services remain excluded and identity-stable. |
| D02 | A stale API is repaired by building the exact application image and force-recreating only the API with `--no-deps --no-build`. |
| D03 | Dependency identity is computed without invoking the dependency-image helper, and the already-present hash-addressed ROCm image plus all identity labels must match. |
| D04 | The application image tag, ID, OCI revision label, and dependency-hash label must prove provenance before runtime revision values are injected. |
| D05 | Selected services start separately with `--no-deps`; a stale running worker stops the command instead of being recreated. |
| D06 | Readiness requires exact revision, production profile, and data-root parity within 120 seconds, followed by GPU proof at the worker boundary with no CPU fallback. |
| D07 | Source and live restart policies for the API and GPU worker must finish as `restart=no`. |
| D08 | Exactly one terminal outcome is printed; only `succeeded` exits zero, while failure preserves diagnostics and performs no broad recovery. |
