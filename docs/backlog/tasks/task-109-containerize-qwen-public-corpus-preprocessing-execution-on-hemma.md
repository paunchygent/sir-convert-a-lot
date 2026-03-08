---
id: 'task-109-containerize-qwen-public-corpus-preprocessing-execution-on-hemma'
title: 'Containerize Qwen public-corpus preprocessing execution on Hemma'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-08'
last_updated: '2026-03-08'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-100-create-the-containerized-qwen3-tts-1-7b-swedish-full-finetune-runtime-on-hemma.md
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-107-run-the-staged-public-corpus-qwen-swedish-preprocessing-bundle-on-hemma.md
  - docs/backlog/tasks/task-108-materialize-rixvox-audio-and-train-family-mapping-for-qwen-preprocessing.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - preprocessing
  - container
  - hemma
  - remediation
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Correct the runtime-model drift introduced during `T103` / `T107` so the
public-corpus Qwen preprocessing lane runs inside the selected containerized
Qwen runtime on Hemma instead of the Hemma host virtualenv.

## PR Scope

- Document the drift explicitly:
  - `T100` established the Qwen container as the canonical execution unit
  - `T103` started as a fast repo/PDM preprocessing runner to prove manifest
    logic
  - `T107` extended that runner into real public-corpus execution without
    moving it into the container runtime
  - that split execution truth between the container and the host venv, which
    is not the planned architecture
- Explain why the drift is unacceptable:
  - host-installed binaries and Python packages can diverge from the canonical
    processing unit
  - runtime warnings and behavior can differ between preprocessing and training
  - docs and operational truth drift apart
- Implement the preferred correction:
  - container is the canonical execution unit for public-corpus preprocessing
  - Hemma host is orchestration only
  - wrapper-driven repo commands remain the entrypoint
  - the same persistent DATA and Hugging Face cache roots are mounted into the
    containerized preprocessing run
- Record the preferred solution as policy so future Qwen preprocessing work
  does not regress into host execution.

## Deliverables

- [x] One explicit remediation record for the host-versus-container drift.
- [x] One containerized command surface for public-corpus preprocessing on
      Hemma.
- [x] One updated runbook/task state describing the container-first policy for
      preprocessing and training alike.
- [x] One live Hemma validation proving the public-corpus preprocessing lane no
      longer depends on host-installed `sox`, `flash_attn`, or other drift-prone
      host runtime state.

## Acceptance Criteria

- [x] The task explains the drift in concrete terms and references the affected
      tasks (`T100`, `T103`, `T107`).
- [x] The preferred solution is documented explicitly:
      containerized preprocessing is canonical, host execution is not.
- [x] The public-corpus preprocessing command runs through the Qwen
      container/runtime rather than the Hemma host venv.
- [x] The containerized run mounts the canonical DATA-backed corpus root and
      Hugging Face cache root.
- [x] The remediation leaves no ambiguity in backlog/runbook docs about the
      selected processing unit.

## Drift Record

The current drift happened because `T103` was initially implemented as a
fast repo-level preprocessing runner to prove the manifest contract, and `T107`
extended that same runner into real public-corpus execution before the command
surface was migrated into the Task 100-style container runtime.

That sequencing produced an unplanned split:

- training/runtime truth:
  - Task 100 container
- preprocessing truth:
  - Hemma host `qwen-preprocessing` virtualenv

This is not the intended architecture for the Qwen lane.

## Preferred Solution

Preferred long-term repo position:

- container is the canonical execution unit for:
  - Qwen preprocessing
  - Qwen tokenizer/audio-code generation
  - Qwen fine-tuning
- Hemma host is used only for:
  - wrapper-driven orchestration
  - bind mounts
  - cache and DATA-root exposure
  - report collection

The public-corpus preprocessing lane should therefore be moved onto the
Task 100-style Qwen runtime rather than hardened further on the host.

## Completed Evidence

The remediation now exists as a committed command surface:

- canonical repo command:
  - `pdm run task-103-preprocess-public-corpus`
- canonical Hemma wrapper command:
  - `pdm run run-hemma -- pdm run task-103-preprocess-public-corpus`
- committed runtime surfaces:
  - `scripts/sir_convert_a_lot/devops/run_task109_hemma_qwen_containerized_preprocessing.py`
  - `scripts/sir_convert_a_lot/devops/task109_qwen_containerized_preprocessing_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task100_qwen_finetune_runtime.py`
  - `pyproject.toml`

Live Hemma validation completed on `2026-03-08` and wrote deterministic
evidence to:

- `build/verification/task-109-qwen-containerized-preprocessing/report.json`
- `build/verification/task-109-qwen-containerized-preprocessing/report.md`

Key runtime facts from the live report:

- image:
  - `sir-convert-a-lot-qwen-finetune-hemma:task100`
- image id:
  - `sha256:e09ab71bc210812f554a3068d0d0f262d2e287e0bc078c86707cb874b42512c2`
- canonical HF cache mounted into the container:
  - `/srv/scratch/sir-convert-a-lot/cache/huggingface`
- canonical DATA root mounted into the container:
  - `/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus`
- effective home-backed compatibility mounts used by Docker:
  - `/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface`
  - `/home/paunchygent/.data/sir-convert-a-lot/data/qwen3-tts-swedish-corpus`
- clean GPU baseline recorded before launch:
  - `No KFD PIDs currently running`
  - `VRAM Total Used Memory (B): 59936768`
- inner public-corpus preprocessing result:
  - `inventory_rows=16841`
  - `curated_rows=24`
  - `admitted_rows=23`
  - `prepared_rows=23`

This closes the runtime-model remediation. Public-corpus preprocessing now runs
inside the selected Qwen container runtime, and the remaining blocker before
`T101` is `T108`: real `rixvox` audio materialization plus train-family
mapping.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
