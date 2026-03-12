---
id: task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts
title: Harden qwen pilot training eval and bundle preflight contracts
type: task
status: completed
priority: high
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/stories/story-25-containerized-qwen3-tts-swedish-full-finetune-baseline-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-117-harden-the-qwen-hemma-training-runtime-for-graceful-stop-and-cold-start-safety.md
  - docs/backlog/tasks/task-142-materialize-frozen-qwen-pilot-training-bundle-for-task-101.md
  - docs/reference/ref-qwen3-tts-swedish-finetuning-guide.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels: []
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Harden the deterministic Task 101 pilot-bundle and launch contract so the
first bounded Hemma fine-tune behaves like a professional training, test, and
evaluation pilot: portable frozen inputs, fail-closed bundle preflight, and
explicit held-out eval-manifest metadata throughout the detached runtime.

## PR Scope

- Make the Task 101 pilot-bundle materializer resilient to relocated frozen
  roots by resolving freeze-ledger artifacts from the current source root
  rather than trusting stale absolute paths blindly.
- Harden Task 101 launch preflight so it validates the actual prepared-manifest
  payloads and bundle-local `audio` / `ref_audio` targets before the detached
  training container starts.
- Carry the held-out eval manifest path through the Task 101 runtime metadata,
  detached launch metadata, and in-container status/report surfaces so the
  pilot contract records both the training and held-out evaluation inputs even
  though upstream Qwen training remains train-only.
- Keep the runtime honest about that upstream limitation:
  - do not invent a fake eval loop inside `sft_12hz.py`
  - do not claim that the detached Task 101 pilot already performs automatic
    held-out scoring during training
  - do record which eval manifest is reserved for post-training assessment

## Why This Exists

`T142` established the deterministic pilot-bundle surface, but the initial
implementation still had three operational gaps:

- the held-out eval family was required in docs and preflight but was not
  carried through the runtime/report contract,
- launch preflight only checked for manifest/report file existence rather than
  validating the real bundle payload paths,
- bundle materialization depended on absolute ledger paths from the freeze
  report, making restored or relocated frozen roots brittle.

Those gaps are small enough for one PR-sized hardening slice and large enough
to matter before the first canonical Task 101 pilot launch.

## Non-Goals

- Do not redesign upstream Qwen training into a custom validation loop inside
  this task.
- Do not fold graceful stop, final checkpoint on stop, or cache-sync hardening
  into this task; those remain `T117`.
- Do not reopen the frozen pilot ownership decision from `T140`.
- Do not add aliases or fallback legacy flags.

## Ordered Execution

1. Tighten the docs/runtime contract for Task 101 around held-out eval inputs
   and bundle preflight.
1. Make the pilot-bundle materializer resolve freeze-ledger artifacts relative
   to the current frozen source root.
1. Add fail-closed prepared-manifest path validation before detached launch.
1. Carry `eval_jsonl` through the detached runtime metadata and probe report.
1. Add focused tests for relocation safety, eval metadata propagation, and
   launch preflight integrity.

## Deliverables

- [x] Relocation-safe Task 101 pilot-bundle materialization.
- [x] Fail-closed Task 101 launch preflight that validates bundle-local
  manifest paths, `audio`, and `ref_audio` artifacts.
- [x] Detached Task 101 runtime/probe metadata that records both train and
  held-out eval manifest inputs.
- [x] Focused tests covering the new contract.

## Acceptance Criteria

- [x] The Task 101 pilot-bundle builder works from a copied or restored frozen
  pilot root without depending on stale absolute ledger paths.
- [x] Task 101 launch fails before container start if any prepared-manifest row
  points at a missing bundle-local `audio` or `ref_audio` artifact.
- [x] Detached Task 101 launch metadata, status, and report artifacts all
  record the held-out eval manifest path used for the pilot contract.
- [x] The runtime is explicit that upstream Qwen training remains train-only;
  no fake in-training eval claim is introduced.

## Validation

- [x] `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py`
- [x] `pdm run python -m mypy scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_runtime.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_probe.py scripts/sir_convert_a_lot/devops/run_task101_hemma_qwen_pilot.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Notes

Upstream Qwen truth at task start:

- the current `sft_12hz.py` surface is train-only and accepts one training
  manifest, not an eval manifest
- therefore this task hardens our runtime/test contract around the held-out
  eval split without pretending the upstream trainer already performs internal
  validation on it

## Outcome

`T143` is now implemented.

The Task 101 pilot lane now:

- resolves frozen ownership ledgers from the active copied/restored frozen root
  instead of trusting stale absolute report paths
- fails before detached launch if prepared-manifest rows point at missing or
  bundle-escaping `audio` / `ref_audio` artifacts
- carries both the train and held-out eval manifest paths through detached
  launch metadata and in-container status/report artifacts
- states explicitly in runtime metadata that upstream `sft_12hz.py` remains
  train-only, so held-out evaluation is a post-training assessment contract,
  not an in-training loop claim

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
