---
type: task
id: TASK-SIRCON-01-05-04
title: Bound Hemma production startup to API revision and GPU readiness
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
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
- '`--no-deps` prevents the GPU worker''s Compose dependency edge from starting STT,
  and before/after identity evidence proves every excluded service stayed untouched.'
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
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

Product-owned implementation leaf for the shared Hemma staged-start contract.

### Objective

Provide one bounded Sir Convert production-start command that starts the API and
GPU worker without rebuilding dependency images, proves API revision/readiness
and worker GPU availability, repairs only a stale API application image, and
leaves both selected services at `restart=no`.

### Decision And Assumption Ledger

| ID | Status | Decision | Accepted outcome | Source |
| --- | --- | --- | --- | --- |
| T384-01 | closed | Which parent owns the change? | Keep the task under the active Dockerized service-hardening story. | Current backlog discovery; user-approved owner-local split, 2026-07-29. |
| T384-02 | closed | Which services join the bounded startup? | Start `sir_convert_a_lot_prod` and `sir_convert_a_lot_gpu_worker`; do not start STT, Qwen, training, benchmark, or reserved-edge services. | ST-SKILL-05-01 accepted baseline and manual-heavy exclusion. |
| T384-03 | closed | How is a stale API repaired? | Build only the API application image against the already-present ROCm dependency image, then force-recreate only the API with `--no-build`; never call dependency-image ensure or broad recreate. | Task 255 cache contract; live TASK-0105 evidence; user-approved bounded rebuild decision. |
| T384-04 | closed | What proves readiness? | Require `/readyz` HTTP 200 with `ready=true`, `service_revision == expected_revision == repo HEAD`, production profile/data-root readiness, then run GPU proof against the GPU worker rather than the intentionally CPU-only API. | Current health/GPU contracts and retained discovery `0001-bounded-production-startup`. |
| T384-05 | closed | What restart policy survives startup? | Source and live truth for the selected API and GPU worker are `restart=no`; fail verification on mismatch. | Shared operator-started baseline and user-approved compose restart-policy truth. |
| T384-06 | closed | How is application revision provenance established before startup? | Compute repo `HEAD`; compute the expected ROCm dependency identity with `service_dependency_inputs` without calling `service-deps-image.sh`; require the exact hash-addressed dependency image and all three identity labels; then require or build `sir-convert-a-lot-runtime:<HEAD>` with OCI revision and dependency-image-hash labels. Compose receives that immutable application tag only after its labels match. | Plan-review finding 1; Task 255 hash-addressed dependency contract; accepted exact-revision boundary. |
| T384-07 | closed | How are selected services started while excluded dependencies stay stopped? | Snapshot all service IDs/states first. Start an absent/stopped API or worker separately with `up -d --no-deps --no-build`. When only the API is stale, run `up -d --no-deps --no-build --force-recreate sir_convert_a_lot_prod`; require an already-running worker to have current image provenance and preserve its ID. A stale running worker is a stop condition, not an API-repair side effect. | Plan-review findings 1-2; T384-02/T384-03 bounded service contract. |
| T384-08 | closed | What terminal contract does the coordinator consume? | Bound readiness to 120 seconds. Print one final accepted `outcome=<value>` line and exit zero only for `succeeded`; use non-zero for `timed_out`, `dependency_unhealthy`, or `failed`, retaining the failed boundary diagnostics. Do not add a status store or polling framework. | ST-SKILL-05-01 OQ-005 product-owned timeout and accepted outcome contract; plan-review finding 3. |

### PR Scope

- Add one stable on-Hemma command for bounded production startup.
- Reuse Compose, `/readyz`, and the existing GPU verifier.
- Add the smallest API-only application build/recreate path that computes and
  validates the expected hash-addressed dependency image without invoking
  `service-deps-image.sh`.
- Bake and inspect immutable application-image revision and dependency identity
  labels before Compose can inject runtime revision environment values.
- Set and verify `restart=no` for the selected API and GPU worker.
- Add focused command-contract tests for clean start, stale API repair,
  readiness failure, GPU target selection, and restart-policy mismatch.

### Deliverables

- [ ] `pdm run prod-start-bounded`
- [ ] Focused startup/revision/GPU/restart-policy tests.
- [ ] Updated Sir Convert Hemma operations runbook.

### Implementation Plan

1. Add the bounded command and expose it through PDM.
1. Compute repo `HEAD` and the expected ROCm dependency hash with
   `python -m scripts.sir_convert_a_lot.devops.service_dependency_inputs`;
   inspect the exact `sir-convert-a-lot-deps-rocm:<dependency_image_hash>` image
   and its dependency, recipe, and dependency-image-hash labels. Stop without
   building when any identity is absent or mismatched.
1. Inspect `sir-convert-a-lot-runtime:<HEAD>` for
   `org.opencontainers.image.revision=<HEAD>` and the expected
   `sir-convert-a-lot.dependency-image-hash` label. When absent or stale, build
   only `Dockerfile` with the exact hash-addressed dependency image, bake both
   labels, and tag the result with `<HEAD>`. Never retag an unverified
   application image as current.
1. Snapshot the IDs, running states, and image provenance of the API, worker,
   STT, Qwen, training, benchmark, and reserved-edge containers. Select the
   verified `<HEAD>` application tag and set both runtime revision values to
   `<HEAD>`. Start an absent/stopped API with
   `docker compose up -d --no-deps --no-build sir_convert_a_lot_prod`.
   When an existing API is stale, replace it with
   `docker compose up -d --no-deps --no-build --force-recreate
   sir_convert_a_lot_prod`. Start an absent/stopped worker separately with
   `docker compose up -d --no-deps --no-build
   sir_convert_a_lot_gpu_worker`. If a running worker is stale, stop; never
   recreate it through the API stale-repair branch.
1. Poll the API readiness payload for at most 120 seconds and compare both
   revision fields to repo `HEAD`. Timeout and terminal failure retain the last
   payload/diagnostic, print the accepted non-success outcome, and exit
   non-zero.
1. Prove the GPU worker through the existing verifier with its container target
   explicit.
1. Apply and strictly verify `restart=no` for both selected services.
1. Update the product runbook and retain the focused real-Hemma packet.

### Acceptance Criteria

- [ ] A current API starts without any dependency-image helper invocation and
  passes exact `/readyz` revision/profile/data-root parity.
- [ ] A stale API builds and recreates only `sir_convert_a_lot_prod`; GPU
  worker, STT, Qwen, dependency-image, and persistent-data identities remain
  unchanged.
- [ ] No stale application image can report current solely because Compose
  injected current revision environment values; the selected image labels,
  tag, and ID prove its source revision and dependency identity before start.
- [ ] `--no-deps` prevents the GPU worker's Compose dependency edge from
  starting STT, and before/after identity evidence proves every excluded
  service stayed untouched.
- [ ] GPU proof targets `sir_convert_a_lot_gpu_worker` and proves ROCm torch,
  `/dev/kfd`, `/dev/dri`, and `rocm-smi` visibility.
- [ ] API and GPU worker finish with source and live `restart=no`; mismatch is a
  failing result.
- [ ] Failure retains the failed boundary and never falls back to CPU, broad
  recreate, dependency rebuild, or unrelated service startup.
- [ ] The command terminates within 120 seconds, prints exactly one final
  accepted outcome, and returns zero only for `succeeded`.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

### Proof

- Mode: behavioral red/green plus real-Hemma boundary proof.
- Red: `pdm run pytest-root
  tests/sir_convert_a_lot/test_bounded_production_startup.py -q` fails against
  the missing bounded command for immutable app/dependency provenance,
  `--no-deps`, timeout/outcome, excluded-service identity, worker GPU target,
  and strict restart-policy assertions.
- Green: the same exact command passes without weakening assertions.
- Live: one exact revision exercises the current path and one genuinely older
  application image whose OCI revision label and image ID differ from `HEAD`.
  If no such prior image exists, stop rather than fabricate provenance. Retain
  the old/current labels and IDs, exact dependency label packet, readiness
  JSON, GPU report, restart policies, timeout/outcome record, and before/after
  identities for every excluded service.

### Validation

- `pdm run pytest-root tests/sir_convert_a_lot/test_bounded_production_startup.py -q`
- `pdm run pytest-root tests/sir_convert_a_lot/test_compose_contract.py tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime.py -q`
- `pdm run coverage-gate`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

### Stop Conditions

- The required remote revision or existing ROCm dependency image is absent.
- The expected hash-addressed dependency image or any of its three identity
  labels is absent or mismatched.
- The selected application tag lacks exact revision/dependency labels, or a
  real older application image is unavailable for the controlled stale proof.
- `/readyz` cannot prove exact revision/profile/data-root parity.
- GPU proof targets the CPU-only API or requires starting unrelated workloads.
- The proposed path invokes dependency-image ensure, rebuilds ROCm
  dependencies, mutates volumes/data, or recreates services outside the API.
- Any excluded service is created, started, stopped, or recreated.
- A running GPU worker has stale application provenance; API-only repair must
  not recreate or silently relabel it.
- Restart-policy truth cannot be made and verified `no` for the selected
  operator-started services.

### Plan Document Review

- Recorded: `2026-07-29T18:25:48+02:00`.
- Reviewer: `plan-document-reviewer`
  `/root/review_sir_task384`.
- `readiness_review`: `changes_requested`.
- Decision: `changes_requested`.
- Reviewed scope: this task; parent
  `story-05-dockerized-service-hardening-with-robust-persistence`; Tasks 255
  and 283; `EPIC-SKILL-05` CAP-05-A, ready `ST-SKILL-05-01`, and approved
  `TASK-SKILL-05-01-01`; retained discovery
  `0001-bounded-production-startup`; current Compose, dependency-image,
  readiness, deploy, and GPU-verifier contracts; the current task template,
  docs contract, proof-selection rules, and repo validation rules.
- Governing authority: closed T384-01 through T384-05, the accepted shared
  owner split and Sir Convert product-leaf contract, and the parent story's
  deterministic startup, narrow dependency-image, readiness, GPU-first, and
  script-backed operations contract.
- Findings:
  1. Critical: the stale-image path does not define trustworthy revision
     provenance or an exact dependency-image selection. The current Compose
     wrapper resolves both revision environment values to repository `HEAD`,
     while the production Dockerfile does not bake a revision. An initial
     `up -d --no-build` can therefore recreate a stale tagged image with
     current revision environment values and make `/readyz` report parity
     before the required application build. The plan also says only
     "existing ROCm dependency image", so implementation could consume a stale
     `:local` dependency tag while avoiding `service-deps-image.sh`. Derive
     and record one exact start/detect/build/recreate sequence that cannot
     relabel stale application code as current, validates or selects the
     already-present dependency image without ensuring or rebuilding it, and
     stops when that identity is unavailable.
  2. High: the selected-service command is incomplete against T384-02.
     `sir_convert_a_lot_gpu_worker` has a Compose `depends_on` edge to
     `sir_convert_a_lot_stt_sidecar`, so the planned
     `up -d --no-build` starts the excluded STT sidecar unless dependency
     startup is explicitly suppressed. Record the exact API/worker argv and
     proof that STT, Qwen, training, benchmark, and reserved-edge services are
     neither started nor recreated.
  3. High: the product-owned terminal boundary is under-specified. The plan
     says to poll readiness but selects no bounded timeout, terminal exit
     behavior, or retained failure result for the HuleEdu coordinator to
     consume. Close that task-level decision from the accepted shared
     `succeeded`/non-success and product-owned-timeout contract, without
     creating a second status framework.
  4. Medium: the proof and validation plan is not execution-ready. The red
     description observes existing generic recreate behavior rather than
     naming one new-command boundary that fails before implementation and
     passes afterward, and a controlled revision-environment mismatch would
     not prove replacement of a stale application image. Name the focused
     test paths or node IDs, make the same bounded command proof red then
     green, require live stale-image provenance rather than environment-only
     drift, and add the repo-required `pdm run coverage-gate` or record the
     accepted basis for non-applicability.
- Permitted next step: keep the task `proposed`; repair only the four derived
  readiness gaps, run the declared planning/docs validation, and return the
  changed task to this reviewer. Implementation is not permitted by this
  decision.
- Status transition: none.
- Residual risk: no code, container, service, dependency image, volume, data,
  restart policy, or Hemma host state was changed or verified by this review.
  Behavioral red/green, real-Hemma current/stale proof, unchanged HuleEdu
  walking-skeleton integration, implementation review, and CAP-05-A
  end-to-end verification remain later gates.

### Re-review

- Recorded: `2026-07-29T18:40:54+02:00`.
- Reviewer: `plan-document-reviewer`
  `/root/review_sir_task384`.
- `readiness_review`: `changes_requested`.
- Decision: `changes_requested`.
- Changed scope: only the repairs for the four findings recorded above.
- Findings:
  1. Critical: T384-06 now establishes trustworthy application and dependency
     provenance, but the execution sequence no longer contains the accepted
     API-only stale repair. Steps 3 and 4 build or select
     `sir-convert-a-lot-runtime:<HEAD>` before one joint API/GPU-worker
     `up`; both Compose services consume the same application image tag. The
     plan therefore does not show how a genuinely older API is replaced without
     also recreating the GPU worker, and it names no API-only
     `--force-recreate --no-build` action after stale detection. This conflicts
     with T384-03 and the unchanged-worker criterion at lines 96-98. Record the
     exact service/image selection and command sequence that starts the selected
     pair but force-recreates only `sir_convert_a_lot_prod` for the controlled
     older-image branch, with the GPU-worker ID unchanged.
  2. Medium: finding 4 is nearly resolved, but the focused commands use
     `pdm run pytest` instead of the repository's required
     `pdm run pytest-root`, and validation retains the noncanonical
     `lint-fix --unsafe-fixes` form. Change only those command forms to
     `pdm run pytest-root <exact paths> -q` and `pdm run lint-fix`; keep the
     selected exact test paths and `coverage-gate`.
- Cleared findings: exact hash-addressed dependency-image and label validation,
  immutable OCI application provenance, `--no-deps` selected-service startup
  and excluded-service identity proof, the 120-second terminal outcome, and
  genuine older-image live-proof stop condition are adequate.
- Permitted next step: keep the task `proposed`; repair only the two remaining
  contradictions and return the changed task for re-review. Implementation is
  not permitted by this decision.
- Status transition: none.
- Residual risk: no runtime or Hemma mutation was performed. Behavioral
  red/green, real-Hemma proof, implementation review, and CAP-05-A end-to-end
  verification remain later gates.

### Approved Final Re-review

- Recorded: `2026-07-29T18:45:05+02:00`.
- Reviewer: `plan-document-reviewer`
  `/root/review_sir_task384`.
- `readiness_review`: `approved`.
- Decision: `approved`.
- Changed scope: only the API-only stale-repair sequence and canonical
  validation-command repairs requested in the preceding re-review.
- Findings: none. The task now starts absent or stopped API and worker
  separately, uses the exact API-only
  `up -d --no-deps --no-build --force-recreate sir_convert_a_lot_prod`
  stale-repair action, requires a running worker to have current provenance,
  preserves its container ID, and stops on stale worker provenance. The focused
  and regression suites now use `pytest-root`, and lint validation uses the
  canonical `lint-fix` command.
- Validation supplied: docs validation, task validation, and
  `git diff --check` passed.
- Permitted next step: the parent may transition this task from `proposed` to
  `in_progress` and implement Task 384 directly under its closed ledger and
  stop conditions.
- Status transition: `proposed -> in_progress` when implementation starts.
- Residual risk: approval establishes plan readiness only. Behavioral
  red/green, the genuinely older-image real-Hemma packet, unchanged
  HuleEdu-owned walking-skeleton integration, implementation review, and final
  CAP-05-A end-to-end verification remain later gates. This review performed
  no code, container, service, image, volume, data, restart-policy, or Hemma
  mutation.
