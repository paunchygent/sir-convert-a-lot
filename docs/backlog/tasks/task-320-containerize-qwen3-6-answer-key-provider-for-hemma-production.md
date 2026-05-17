---
id: task-320-containerize-qwen3-6-answer-key-provider-for-hemma-production
title: Containerize Qwen3.6 answer-key provider for Hemma production
type: task
status: proposed
priority: high
created: '2026-05-17'
last_updated: '2026-05-17'
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
answer-key completion, reachable from `sir_convert_a_lot_prod` through Docker
service DNS instead of container-local loopback.

The production failure this task fixes is namespace-specific: Task 319 proved
the guarded Qwen3.6 `llama.cpp` provider on host `127.0.0.1:8082`, while the
production Sir Convert container tried to use that same loopback address from
inside its own namespace. The result was `provider_request_failed` for eligible
machine-marked MCQ rows even though the host-local provider was healthy.

## PR Scope

- Add a production `sir_convert_qwen_answer_key` service on the shared
  `hule-network`, with no public port exposure.
- Run the provider through the Task 309/319 Qwen3.6 MTP settings:
  `qwen36-llama-cpp-mtp`, alias/model `qwen3.6-27b-q6k-mtp`, GGUF repo
  `unsloth/Qwen3.6-27B-MTP-GGUF`, file
  `Qwen3.6-27B-UD-Q6_K_XL.gguf`, `llama.cpp` JSON Schema, context `32768`,
  max output `4096`, temperature `0.15`, `--reasoning off`,
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
- Keep Qwen3.6 guarded advisory only; this task does not promote automatic
  answer-key application.

## Deliverables

- [ ] Governed production Qwen provider service in Compose.
- [ ] Runbook-aligned `llama.cpp` build helper that enforces `nice -n 10` and
  `-j8` maximum build concurrency.
- [ ] Structured-provider environment renderer/validator for local and Hemma
  production lanes.
- [ ] Deploy verifier provider reachability and microprobe checks.
- [ ] Live authenticated path proof showing MCQ candidates in
  `answer_key_completion_report`.

## Acceptance Criteria

- [ ] Hemma production structured-provider config cannot use `127.0.0.1`,
  `localhost`, or `host.docker.internal`.
- [ ] `sir_convert_a_lot_prod` reaches Qwen through
  `http://sir_convert_qwen_answer_key:8082`.
- [ ] The production provider service uses Docker `expose`, not host `ports`.
- [ ] The production provider defaults use the MTP profile and alias
  `qwen3.6-27b-q6k-mtp`; non-MTP Qwen is not the Hemma production default.
- [ ] Provider build guidance and command surfaces preserve the runbook
  `nice -n 10` / `-j8` compile contract.
- [ ] Active model cache, build, and vision media paths stay on Scratch-backed
  Docker-visible roots, not container-local storage or `/`.
- [ ] Provider containers do not depend on host `/opt/rocm*` or `/opt/amdgpu`
  bind mounts; ROCm runtime libraries come from the pinned provider image.
- [ ] GPU device group access uses Hemma host numeric GIDs rendered into prod
  env, not image-local `video` / `render` group names.
- [ ] Advisory `.dxe` MCQ rows produce valid candidates instead of
  `provider_request_failed`.
- [ ] Local host-dev can still use `http://127.0.0.1:8082`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
