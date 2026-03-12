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
- Docs-as-code surfaces updated:
  - `docs/backlog/tasks/task-149-containerize-task101-pilot-bundle-batch-finalization-runtime.md`
  - `docs/backlog/tasks/task-148-batch-task101-pilot-bundle-finalization-and-progress-logging-on-hemma.md`
  - `docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md`
  - `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
  - `docs/backlog/current.md`

## Validation Status

- `PASS` `pdm run format-all`
- `PASS` `pdm run lint-fix`
- `PASS` `pdm run typecheck-all`
- `PASS` `pdm run pytest-root tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py -q`
- `PASS` `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_cli.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_source.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_validation.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_contracts.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_progress.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_batch_execution.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_runtime.py scripts/sir_convert_a_lot/devops/task101_qwen_pilot_bundle_in_container.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle.py tests/sir_convert_a_lot/test_task101_qwen_pilot_bundle_runtime.py`
- `PASS` `pdm run validate-tasks`
- `PASS` `pdm run validate-docs`
- `PASS` `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Active Blocker

- The next live Hemma Task 101 bundle retry is still blocked by storage
  pressure on `/srv/scratch`.
- Verified live state from the earlier incident remains the operator truth to
  respect until rechecked:
  - `/srv/scratch` was `458G / 458G` used
  - the canonical retry failed with `OSError: [Errno 28] No space left on device`

## Immediate Next Step

- Reclaim `/srv/scratch` capacity safely or choose an alternate
  `--output-root`.
- After that prerequisite is satisfied, run the next bounded Hemma Task 101
  pilot-bundle retry through the governed containerized `build` surface and
  inspect:
  - `reports/task101_pilot_bundle_plan.json`
  - `reports/task101_pilot_bundle_events.jsonl`
  - `reports/task101_pilot_bundle_status.json`
  - `reports/task101_pilot_bundle_runtime.json`
