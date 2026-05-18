---
id: task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production
title: Containerize Qwen3.6 answer-key provider for Hemma production
type: task
status: done
priority: high
created: '2026-05-17'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-47-structured-llm-provider-harness-for-answer-key-completion.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes.md
  - docs/backlog/tasks/task-311-run-service-backed-auth-public-edge-mirror-validation-for-answer-key-completion.md
  - docs/backlog/tasks/task-319-enable-qwen3-6-vision-capable-advisory-answer-key-completion-in-the-main-pipeline.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - docs/runbooks/runbook-answer-key-local-model-operator-guide.md
labels:
  - answer-key-completion
  - qwen
  - llama-cpp
  - hemma
  - production
  - docker
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make Qwen3.6 a first-class Hemma production provider service for advisory
answer-key completion, reachable through Docker service DNS instead of
container-local loopback. At the same time, split production job execution so
`sir_convert_a_lot_prod` remains the HTTP admission container while the explicit
`sir_convert_a_lot_gpu_worker` owns current PDF/OCR GPU execution.

The production failure this task fixes is namespace-specific: Task 319 proved
the guarded Qwen3.6 `llama.cpp` provider on host `127.0.0.1:8082`, while the
production Sir Convert container tried to use that same loopback address from
inside its own namespace. The result was `provider_request_failed` for eligible
machine-marked MCQ rows even though the host-local provider was healthy.

## 2026-05-18 Production Reachability Status

Fresh Hemma production proof now shows that the namespace-specific loopback
failure is fixed for provider reachability. The running service path uses
Docker DNS from `sir_convert_a_lot_prod` to `sir_convert_qwen_answer_key`
instead of container-local loopback.

Evidence:

- Hemma repo revision: `2a1dc4d0b0dfe670ce64ba25e125dd59e5d102af`.
- `sir_convert_a_lot_prod`, `sir_convert_a_lot_gpu_worker`, and
  `sir_convert_qwen_answer_key` were all running for two hours; prod and worker
  were healthy.
- `pdm run answer-key-provider-env --lane hemma-prod-compose --profile qwen36-llama-cpp-mtp` rendered provider base URL
  `http://sir_convert_qwen_answer_key:8082`, runtime lane
  `hemma-prod-compose`, model `qwen3.6-27b-q6k-mtp`, context `16384`, max output
  `4096`, JSON Schema output mode, multimodal vision enabled, and remote
  providers disabled.
- Inside `sir_convert_a_lot_prod`, the active provider environment uses
  `http://sir_convert_qwen_answer_key:8082` and not `127.0.0.1`, `localhost`, or
  `host.docker.internal`.
- From inside `sir_convert_a_lot_prod`, `GET http://sir_convert_qwen_answer_key:8082/v1/models` returned
  `qwen3.6-27b-q6k-mtp` with `n_ctx=16384` and `owned_by=llamacpp`.
- From inside `sir_convert_a_lot_prod`, a JSON Schema chat-completions
  microprobe returned `{"decision_state":"answered", "correct_alternative_ids":[1]}` for a synthetic MCQ prompt.
- `sir_convert_a_lot_prod` has `HostConfig.Devices=null`,
  `SIR_CONVERT_A_LOT_ENABLE_SUPERVISOR=0`, and
  `SIR_CONVERT_A_LOT_RUN_JOBS_ON_SUBMIT=0`.
- `sir_convert_qwen_answer_key` has no host port bindings, exposes `8082`, and
  is attached to `hule-network` with alias `sir_convert_qwen_answer_key`.
- The running provider process is `llama-server` with
  `--alias qwen3.6-27b-q6k-mtp`, `--ctx-size 16384`, `--parallel 1`,
  `--n-gpu-layers all`, `--fit off`, `--flash-attn on`, `--jinja`,
  `--reasoning off`, `--temp 0.15`, `--offline`, `--spec-type draft-mtp`,
  `--spec-draft-n-max 2`, and the Task 320 vision media path.
- The provider mounts only Docker-visible home-backed build/cache roots into
  `/srv/scratch/sir-convert-a-lot/...`, has GPU device mounts for `/dev/kfd`
  and `/dev/dri`, and uses numeric group IDs `44` and `993`.
- `sir_convert_a_lot_gpu_worker` has no host port bindings, is attached to
  `hule-network`, has supervisor enabled for background execution, and owns
  `/dev/kfd` plus `/dev/dri` GPU device mounts.

Remaining scope: this proof clears the production provider-reachability gate for
local Qwen routing.

Additional completion evidence:

- Build-helper contract proof passed locally with
  `pdm run pytest-root tests/sir_convert_a_lot/test_qwen_provider_build_contract.py`.
  The test locks the `nice -n 10` / `-j8` runbook build limits, confirms the
  provider image does not hide a `llama.cpp` build, and confirms prod env mirror
  creates the Qwen vision media host path.
- Runtime-lane config proof passed locally with
  `pdm run pytest-root tests/sir_convert_a_lot/test_answer_key_provider_runtime_config.py`.
  The local-host lane still renders `http://127.0.0.1:8082`, while the
  `hemma-prod-compose` lane rejects `127.0.0.1`, `localhost`, and
  `host.docker.internal`.
- A direct service submission with only `X-API-Key` failed with
  `auth_invalid_internal_identity`, proving the DigiExam service route is not a
  plain Sir API-key path and still requires HuleEdu-signed identity context.
- A controlled Hemma proof used the configured HuleEdu Gateway internal-identity
  signing key (`gateway-identity-rs256-v1`) to mint a short-lived
  `InternalIdentityContextV1` for the Sir service verifier, then submitted
  `1786767978-23c-biologi-ak-9-slutprov.dxe` through the deployed service at
  `http://127.0.0.1:28085`.
- The authenticated service job `jobv2_6843fafd02f0402285763eb6e7` succeeded.
  Its `answer_key_completion_report_v1` artifact was available, contained 19
  report rows, produced 8 `suggested` rows, 0 `manual_follow_up_required` rows,
  and 0 `provider_request_failed` rows. Retained artifacts live outside git at
  `/srv/scratch/sir-convert-a-lot/build/verification/task-320-qwen-provider/service-advisory-proof/`.

The remaining full auth/public-edge mirror, including product-edge behavior and
alpha readiness, is broader than this production provider containerization task
and remains governed by Task 311.

## PR Scope

- Add a production `sir_convert_qwen_answer_key` service on the shared
  `hule-network`, with no public port exposure.
- Add a private `sir_convert_a_lot_gpu_worker` service on the shared
  `hule-network` for current PDF/OCR job execution. The public/internal API
  service must not mount GPU devices, must not start the job supervisor, and
  must not execute jobs synchronously on submit in production.
- Run the provider through the Task 309/320 Qwen3.6 MTP Q6_K settings:
  `qwen36-llama-cpp-mtp`, alias/model `qwen3.6-27b-q6k-mtp`, GGUF repo
  `unsloth/Qwen3.6-27B-MTP-GGUF`, file
  `Qwen3.6-27B-Q6_K.gguf`, `llama.cpp` JSON Schema, context `16384`,
  one server slot via `--parallel 1`, max output `4096`, temperature `0.15`,
  `--reasoning off`,
  `--n-gpu-layers all`, `--fit off`, `--flash-attn on`, `--jinja`,
  `--spec-type draft-mtp`, and `--spec-draft-n-max 2`.
- Preserve the runbook build contract for the HIP `llama-server` artifact:
  builds are serialized, use the Scratch source tree, and compile with
  `nice -n 10` plus `-j8` unless a stricter lower-concurrency value is chosen.
- Use Task 242 Docker-visible home-backed bind roots for build/cache mounts
  while preserving `/srv/scratch/...` as the canonical in-container path.
- Do not bind host `/opt/rocm*` or `/opt/amdgpu` paths into the provider
  container. Hemma snap Docker cannot reliably bind those host paths; the
  provider image must supply its pinned ROCm runtime libraries while Compose
  maps only GPU device nodes plus Docker-visible build/cache/media roots.
- Use numeric Hemma GPU group IDs in Compose instead of container-local group
  names. AMD ROCm images may not define `render`, and images that do define it
  may use a GID that does not match the host device group.
- Render and validate the production structured-provider environment so prod
  rejects `127.0.0.1`, `localhost`, and `host.docker.internal` provider URLs.
- Extend deploy verification to prove provider reachability and a small
  structured MCQ microprobe separately from OCR-heavy conversion smoke.
- Keep GPU access explicit in Compose: Qwen is the LLM GPU provider, the worker
  is the PDF/OCR GPU executor, and the API container is CPU/no-device admission
  only.
- Keep Qwen3.6 guarded advisory only; this task does not promote automatic
  answer-key application.

## Deliverables

- [x] Governed production Qwen provider service in Compose.
- [x] Governed private GPU worker service for current PDF/OCR execution, with
  API admission separated from GPU execution.
- [x] Runbook-aligned `llama.cpp` build helper that enforces `nice -n 10` and
  `-j8` maximum build concurrency.
- [x] Structured-provider environment renderer/validator for local and Hemma
  production lanes.
- [x] Deploy verifier provider reachability and microprobe checks.
- [x] Live authenticated path proof showing MCQ candidates in
  `answer_key_completion_report`.

## Acceptance Criteria

- [x] Hemma production structured-provider config cannot use `127.0.0.1`,
  `localhost`, or `host.docker.internal`.
- [x] `sir_convert_a_lot_prod` reaches Qwen through
  `http://sir_convert_qwen_answer_key:8082`.
- [x] `sir_convert_a_lot_prod` has no GPU device mounts, has supervisor
  disabled, and does not execute jobs on submit in Hemma production.
- [x] `sir_convert_a_lot_gpu_worker` is private to Docker networking and owns
  current PDF/OCR GPU execution against the shared production job store.
- [x] The production provider service uses Docker `expose`, not host `ports`.
- [x] The production provider defaults use the smaller MTP Q6_K profile and
  alias `qwen3.6-27b-q6k-mtp`; the XL MTP quant is not the Hemma production
  default.
- [x] The production provider is capped to one `llama-server` slot
  (`--parallel 1`) so Qwen residency does not silently multiply the 16k KV
  cache while current OCR GPU work remains part of the stack.
- [x] Provider build guidance and command surfaces preserve the runbook
  `nice -n 10` / `-j8` compile contract.
- [x] Active model cache, build, and vision media paths stay on Scratch-backed
  Docker-visible roots, not container-local storage or `/`.
- [x] Provider containers do not depend on host `/opt/rocm*` or `/opt/amdgpu`
  bind mounts; ROCm runtime libraries come from the pinned provider image.
- [x] GPU device group access uses Hemma host numeric GIDs rendered into prod
  env, not image-local `video` / `render` group names.
- [x] Advisory `.dxe` MCQ rows produce valid candidates instead of
  `provider_request_failed`.
- [x] Local host-dev can still use `http://127.0.0.1:8082`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
