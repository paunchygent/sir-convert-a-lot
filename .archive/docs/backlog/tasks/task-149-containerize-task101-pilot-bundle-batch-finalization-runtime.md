---
id: task-149-containerize-task101-pilot-bundle-batch-finalization-runtime
title: containerize task101 pilot bundle batch finalization runtime
type: task
status: completed
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma.md
  - docs/backlog/tasks/task-148-batch-task101-pilot-bundle-finalization-and-progress-logging-on-hemma.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - pilot
  - training-bundle
  - container-runtime
  - flash-attn
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Move Task 101 batch finalization off the host PDM environment and onto the
existing governed Qwen runtime image so `audio_codes` generation uses the same
dependency-governed ROCm / `flash-attn` posture as the current Qwen training
lane instead of falling back to the slower host-side manual PyTorch path.

Containerization in this task means:

- a new narrow Task 101 batch-runtime helper and, if needed, a narrow
  in-container entrypoint
- one fresh short-lived container/process per bounded batch
- reuse of the current Task 100 / Qwen image lineage and runtime
  helpers rather than a second ad hoc Qwen image

## PR Scope

- Keep Hemma as the canonical execution target for Task 101 bundle
  materialization.
- Keep the existing Task 101 batch-plan, progress-artifact, validation, and
  final report contracts unchanged.
- Replace the current host-side `finalize-batch` subprocess path with one
  committed runtime surface that runs bounded batch finalization inside the
  governed Qwen runtime image.
- Reuse the existing Task 100 / Qwen image/build and mount-resolution
  helpers as a requirement, not a preference.
- Preserve the current public `--output-root` contract.
  - Do not hardcode `/srv/scratch` as the only valid bundle root when the
    current builder can target another filesystem.
  - If the chosen output root needs special container path translation or bind
    mounting, that behavior must be implemented explicitly rather than narrowed
    by accident.
- Make the containerized batch runner mount only the minimum required inputs:
  - repo checkout
  - the selected bundle output root read-write
  - Hugging Face cache root
- Preserve fresh-process batch isolation and resumable reuse of validated
  batch shards.
- Preserve host-visible plan, event, status, and final report artifacts at the
  same on-disk paths operators use today.

## Non-Goals

- Do not redesign the Task 101 batch-plan or progress JSON contracts again.
- Do not redesign the established Qwen Hemma container model from Task 100 /
  Task 109 when an extension of the working runtime/helper pattern is
  sufficient.
- Do not build or introduce a second Qwen ROCm image lineage when the existing
  Task 100 / Task 101 training image already provides the required governed
  runtime.
- Do not move the copy or assemble/report stages into Docker unless that is
  required to keep the public surface coherent.
- Do not silently accept a CPU-only or disabled-`flash-attn` steady state for
  this lane.

## Why This Slice Exists

The live `2026-03-12` Hemma Task 101 batch build proved that the new batched
shape avoids the earlier immediate `ENOSPC` failure and can complete bounded
batches, but it also exposed one remaining runtime-governance gap:

- `qwen-pilot-bundle build` currently invokes `Qwen3TTSTokenizer` through
  the host PDM environment
- the host environment did not have `flash-attn` available
- the live run therefore emitted the upstream warning that it was falling back
  to the slower manual PyTorch path

That means the Task 101 bundle lane is still host-drift-prone in exactly the
way Task 109 and Task 100 were created to avoid for other Qwen surfaces.

The intended fix is therefore:

- reuse the existing governed Qwen runtime image
- keep the host as orchestration only
- launch one fresh containerized bounded finalization batch at a time
- preserve the current bundle/report contracts on the host-visible output root

## Required Implementation Shape

1. Add one committed Qwen pilot runtime helper/module for containerized batch
   finalization.
   - It should own Docker invocation, bind mounts, in-container command
     execution, and structured failure diagnostics.
   - It should be small and reuse the shared Task 100 / Qwen pilot runtime
     helper pattern rather than introducing a second Qwen image or a second
     runtime model.
   - Mandatory reuse surface:
     - `prepare_qwen_image`
     - `resolve_effective_hf_cache_dir`
     - `resolve_effective_bind_root`
     - ROCm Docker flags and env posture equivalent to the existing Qwen lane:
       `/dev/kfd`, `/dev/dri`, `--ipc=host`, `--cap-add=SYS_PTRACE`,
       `--security-opt seccomp=unconfined`, and canonical HF env vars
1. Keep the public `pdm run qwen-pilot-bundle build` surface unchanged.
   - Operators should not need a new top-level workflow just to get the
     governed runtime.
1. Keep the direct `finalize-batch` CLI stage coherent with the same runtime
   contract.
   - The direct stage may remain an internal/debug surface, but it must not
     bypass the governed runtime and silently reintroduce host drift.
1. Repoint the internal `build -> finalize-batch` subprocess handoff.
   - The host orchestrator may still launch a fresh subprocess or direct
     helper, but the tokenizer work itself must happen in the containerized
     runtime.
1. Add one committed in-container batch entrypoint if needed.
   - This can be a narrow script/module that finalizes exactly one batch from
     an existing plan/output root.
1. Reuse the existing Qwen image lineage instead of creating a new image.
   - Fresh container instances per batch are encouraged for isolation.
   - A new Docker image is not part of this task unless a documented blocker
     proves that reuse is impossible.
1. Preserve deterministic artifacts.
   - `reports/task101_pilot_bundle_plan.json`
   - `reports/task101_pilot_bundle_events.jsonl`
   - `reports/task101_pilot_bundle_status.json`
   - final assembled manifests and final report
   - host-visible artifact paths must remain stable even when the batch work
     executes in-container
1. Add runtime provenance that proves the governed runtime actually produced
   the batch shards.
   - Existing validated host-generated batch shards from pre-Task149 runs must
     not be silently mixed with container-generated shards.
   - The batch reuse path must validate a runtime fingerprint or equivalent
     provenance contract before skipping an existing shard.
1. Add validation that proves the runtime posture.
   - the containerized path must exercise the Qwen runtime image where
     `flash-attn` is governed
   - the host path should no longer be the place where tokenizer/runtime
     dependencies drift
   - focused tests must prove generated Docker command shape, effective bind
     roots, build-vs-reuse behavior, failure propagation, and host-visible
     progress artifact preservation

## Deliverables

- [x] Committed Task 101 containerized batch-finalization runtime helper.
- [x] Committed Task 101 batch-runtime provenance contract so validated shard
  reuse can distinguish governed container output from legacy host output.
- [x] Canonical `qwen-pilot-bundle build` surface updated to use that
  helper for bounded batch finalization.
- [x] Direct `qwen-pilot-bundle finalize-batch` stage updated so it does
  not bypass the governed runtime.
- [x] Tests covering the container-launch contract and failure propagation.
- [x] Tests covering runtime provenance, host-visible status/event/report path
  preservation, and non-hardcoded output-root handling.
- [x] Docs updates that state Task 101 finalization now depends on the governed
  Qwen runtime image rather than host-installed tokenizer dependencies.

## Acceptance Criteria

- [x] Task 101 batch finalization no longer depends on host-installed
  `flash-attn`, `sox`, or equivalent drift-prone tokenizer/runtime
  dependencies.
- [x] The live/operator path for Task 101 batch finalization uses the
  containerized runtime with the governed Qwen dependency set.
- [x] Task 101 batch finalization reuses the existing Task 100 / Qwen
  training image and canonical runtime helpers rather than building a second
  ad hoc Qwen image.
- [x] The public `qwen-pilot-bundle build` surface remains stable for
  operators.
- [x] The direct `finalize-batch` stage no longer bypasses the governed
  runtime.
- [x] The current `--output-root` contract remains valid and is not narrowed to
  one hardcoded scratch path by accident.
- [x] A failed containerized batch still leaves the same resumable progress
  evidence as `T148`.
- [x] Host-visible `task101_pilot_bundle_plan.json`,
  `task101_pilot_bundle_events.jsonl`, and
  `task101_pilot_bundle_status.json` remain stable and continue to reference
  the host-visible bundle root rather than leaking container-only paths.
- [x] Existing pre-Task149 host-generated batch shards are not silently reused
  as if they were governed container output.
- [x] The task doc and Qwen Hemma/Colab runbook describe the new runtime
  contract clearly.

## Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py -q`
- [x] focused Task 101 container-runtime validation for:
  - generated Docker command contract
  - effective mount-root resolution
  - build-vs-reuse image behavior
  - host-visible progress/status/report preservation
  - stale host-shard invalidation or rerun behavior
  - non-hardcoded `--output-root` handling
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Design Notes

- Preferred runtime source:
  reuse the existing `containers/qwen-finetune-hemma/Dockerfile` image family
  and Task 100 / Qwen pilot runtime helpers rather than creating a second Qwen
  ROCm image unless that proves impossible and is documented explicitly.
- Preferred architecture posture:
  extend the current working Task 100 / Task 109 container-runtime concept;
  only add the minimum new Task 101-specific helper/entrypoint surface needed
  to finalize one batch inside that already-proven model.
- Preferred mount model:
  - selected bundle output root mounted read-write
  - repo checkout mounted read-only or read-write depending on the chosen
    entrypoint
  - HF cache mounted through the same canonical resolution rules as Task 100
  - if the chosen bundle root is outside the default scratch root, the runtime
    helper must still mount and translate it correctly instead of rejecting it
    implicitly
- Preferred execution model:
  one bounded batch per fresh container/process so the runtime isolation gains
  from `T148` are preserved.
- Preferred ownership boundary:
  host orchestrator remains the canonical owner of copy-stage setup plus the
  final assemble/report flow unless a documented blocker requires moving more
  logic in-container.
- Preferred provenance posture:
  validated batch reuse must include runtime provenance so a mixed
  host-generated / container-generated bundle cannot pass as a governed Task
  149 output.
- Performance posture:
  `flash-attn` should be treated as the default Qwen ROCm path for this lane,
  not an optional nice-to-have.

## Outcome

`T149` is now implemented.

The canonical Task 101 bundle path now reuses the governed Task 100 / Task 101
Qwen image instead of the host PDM environment for bounded `finalize-batch`
execution. The committed implementation added:

- a narrow Task 101 batch-runtime helper that reuses `prepare_qwen_image`,
  `resolve_effective_hf_cache_dir`, the fixed in-container HF cache contract,
  and the canonical ROCm Docker flags
- a narrow in-container batch entrypoint that finalizes exactly one bundle
  batch with the governed tokenizer/runtime dependencies
- governed runtime provenance at both bundle and per-batch scope so legacy
  host-generated shards fail closed and rerun instead of being silently reused
- stable host-visible report/status paths by mounting the selected bundle root
  back into the container at the same host path

The fixed in-container HF/cache convention for Task 101 bundle finalization is
now explicitly aligned with the existing Task 100/101 training lane:

- `HF_HOME=/cache/huggingface`
- `HUGGINGFACE_HUB_CACHE=/cache/huggingface/hub`
- `TORCH_HOME=/cache/huggingface/torch`

Direct `qwen-pilot-bundle finalize-batch` now uses the same governed
runtime contract as `build`, and focused regression coverage now proves:

- generated Docker command shape and fixed in-container HF/cache paths
- build-vs-reuse runtime preparation behavior
- runtime-fingerprint-gated shard reuse
- completed legacy bundle rejection when governed runtime provenance is missing
- preservation of the existing host-visible bundle/report contract

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
