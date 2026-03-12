---
id: task-151-repair-task101-container-output-root-bind-fallback-for-hemma
title: repair task101 container output-root bind fallback for hemma
type: task
status: in_progress
priority: high
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-149-containerize-task101-pilot-bundle-batch-finalization-runtime.md
  - docs/backlog/tasks/task-150-accelerate-task101-pilot-bundle-finalization-with-gpu-backed-audio-code-encoding.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - pilot
  - training-bundle
  - container-runtime
  - bind-mount
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Repair the Task 101 containerized batch runtime so Hemma can resume the
stopped pilot-bundle root under the new GPU-backed tokenizer posture even when
snap-Docker rejects direct bind mounts from the canonical `/srv/...` bundle
output root.

## PR Scope

- Keep the public Task 101 `build` and direct `finalize-batch` surfaces
  unchanged for operators.
- Reuse the shared Task 100/109 bind-root helper pattern instead of inventing
  a new Task 101-only mounting model.
- Preserve the canonical host-visible bundle output-root path inside the
  container.
- Add focused regression coverage for output-root mount resolution and the
  generated Docker command.
- Update the Qwen runbook/session log so the Hemma retry path matches the
  repaired runtime contract.

## Non-Goals

- Do not redesign the Task 101 bundle plan, shard, or report contracts.
- Do not change the GPU-backed tokenizer posture introduced by `T150`.
- Do not narrow `--output-root` support back to one hardcoded filesystem.

## Why This Slice Exists

After `T150` was pulled and the stopped Hemma pilot-bundle root was retried,
the governed batch runtime still failed before container entrypoint start:

- Docker could build/reuse the governed Qwen image successfully
- the container launch then failed with:
  `mkdir /srv/scratch: read-only file system`
- the live stopped bundle root at
  `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
  therefore remained stuck at `swedish_pilot_train:batch-00013`

That exposed a real gap in `T149`: Task 101 reused the shared HF cache helper
but did not reuse the shared bind-root fallback for the selected bundle output
root.

## Required Implementation Shape

1. Add Task 101 output-root mount resolution that reuses
   `resolve_effective_bind_root`.
   - Preserve the selected canonical output-root path as the in-container
     mount target.
   - Use a deterministic home-backed fallback path when Docker cannot bind the
     canonical `/srv/...` root directly.
1. Keep output-root bind resolution separate from the HF cache contract.
   - The Task 101 bundle root is mutable job state, not shared model cache.
1. Emit enough launch metadata to debug which effective output-root mount was
   used on Hemma.
1. Add focused tests covering:
   - deterministic output-root home-mount mapping
   - shared helper reuse with `sync_home_into_canonical=False`
   - generated Docker command using the effective output-root mount rather than
     the canonical host path as the source
1. Retry the stopped Hemma bundle root only after the repaired runtime is
   committed, pushed, and pulled.

## Deliverables

- [x] Task 101 runtime helper updated to resolve the selected bundle output
  root through the shared bind-root helper.
- [x] Focused runtime tests covering deterministic output-root fallback and
  Docker command generation.
- [ ] Hemma retry evidence from the previously blocked
  `swedish_pilot_train:batch-00013` batch.

## Acceptance Criteria

- [x] Task 101 no longer mounts the canonical `/srv/...` bundle output root
  directly when Docker cannot bind it.
- [x] The container still sees the selected host-visible bundle output-root
  path unchanged.
- [x] Focused tests fail if Task 101 bypasses `resolve_effective_bind_root`
  for the output root again.
- [ ] Hemma can launch the resumed governed batch runtime past the previous
  mount error.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Implementation Notes

- Deterministic fallback base:
  `/home/paunchygent/.data/sir-convert-a-lot/task101-pilot-bundle-output-roots`
- The repaired runtime still mounts the effective host bind source back into
  Docker at the canonical bundle root path so in-container paths and host
  report paths stay aligned.

## Checklist

- [x] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
