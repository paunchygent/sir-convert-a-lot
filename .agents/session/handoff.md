# Session Handoff

## Session Summary (2026-03-12)

- `T148-T149` follow-up is closed in code and docs.
- Task 101 pilot-bundle batching remains split across:
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_cli.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_source.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_validation.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_contracts.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_execution.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_progress.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_runtime.py`
  - `scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_in_container.py`
- Review-driven fixes landed:
  - CLI manifest-family arguments now normalize through typed validation in the
    dedicated `task101_qwen_pilot_bundle_cli.py` module so `typecheck-all`
    passes again and the orchestration module stays CLI-free
  - source/materialization and manifest/report validation helpers now live in
    dedicated modules, leaving `task101_qwen_pilot_bundle.py` at `477` LoC and
    focused on orchestration
  - reusable batch-shard validation now compares ordered
    curated/raw/prepared row signatures instead of only counts plus first/last
    row keys
  - regression coverage now includes interrupted-batch recovery, subprocess
    launch/failure contract checks, and corrupted middle-row shard rejection
- `T149` containerized the remaining runtime-governance gap:
  - bounded Task 101 `finalize-batch` now reuses the governed Task 100/101
    Qwen image instead of the host PDM environment
  - the canonical in-container HF/cache convention is now explicit and aligned
    with the detached Task 101 training lane:
    `HF_HOME=/cache/huggingface`,
    `HUGGINGFACE_HUB_CACHE=/cache/huggingface/hub`,
    `TORCH_HOME=/cache/huggingface/torch`
  - the selected bundle output root is mounted back into Docker at the same
    host-visible path so `task101_pilot_bundle_status.json` and related
    artifacts stay host-rooted
  - bundle-level plus per-batch runtime fingerprints now fail closed on legacy
    host-generated shards and completed bundles that lack governed runtime
    provenance
- `T150` is complete and `T151` is now active:
  - the governed Task 101 batch runtime now initializes
    `Qwen3TTSTokenizer` on `cuda:0` with `bfloat16` plus
    `flash_attention_2` instead of silently staying on CPU
  - the in-container Task 101 entrypoint now writes
    `reports/task101_pilot_bundle_audio_codes_runtime.json` so operators can
    verify the observed tokenizer device/runtime posture
  - the live Hemma host-runtime bundle build at
    `/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-task101-pilot-bundle-20260312h`
    was intentionally stopped after completed batch `00012`; batch `00013`
    had started but not completed, so the next governed rerun should regenerate
    that incomplete batch under the GPU-backed runtime
  - the first post-`T150` Hemma retry exposed one remaining Task 101 runtime
    bug: snap-Docker rejected the direct `/srv/...` output-root mount with
    `read-only file system`
  - `T151` repairs that gap by resolving the selected bundle output root
    through the same shared home-backed bind fallback pattern already used for
    Task 100/109 cache and scratch mounts
- Docs-as-code surfaces updated:
  - `docs/backlog/tasks/task-149-containerize-task101-pilot-bundle-batch-finalization-runtime.md`
  - `docs/backlog/tasks/task-150-accelerate-task101-pilot-bundle-finalization-with-gpu-backed-audio-code-encoding.md`
  - `docs/backlog/tasks/task-151-repair-task101-container-output-root-bind-fallback-for-hemma.md`
  - `docs/backlog/tasks/task-148-batch-task101-pilot-bundle-finalization-and-progress-logging-on-hemma.md`
  - `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
  - `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
  - `docs/backlog/current.md`

## Validation Status

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_preprocessing_finalization.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py -q`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task103_processing.py tests/sir_convert_a_lot/test_task103_runner.py -q`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py -q`
- `PASS` `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_cli.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_source.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_validation.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_contracts.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_progress.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_execution.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_runtime.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_in_container.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Active Blocker

- The next live Hemma Task 101 bundle retry must not continue on the stopped
  host-runtime checkout.
- Pull the repaired GPU-backed governed runtime onto Hemma first, then rerun
  the resumable bundle root.

## Immediate Next Step

- Pull the updated checkout on Hemma now that the old host-runtime bundle
  process is stopped.
- Rebuild or reuse the governed Task 100/101 Qwen image with the GPU-backed
  tokenizer runtime and repaired output-root bind fallback.
- Rerun the stopped bounded Hemma Task 101 pilot-bundle root through the
  governed `build` surface and inspect:
  - `reports/task101_pilot_bundle_plan.json`
  - `reports/task101_pilot_bundle_events.jsonl`
  - `reports/task101_pilot_bundle_status.json`
  - `reports/task101_pilot_bundle_runtime.json`
  - `reports/task101_pilot_bundle_audio_codes_runtime.json`
