# Session Handoff

## Current Session Summary (2026-03-10)

- Completed the local `T124` throughput-hardening slice for portable Colab
  Qwen preprocessing:
  - `scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py`
    now exposes `localize-slice`
  - the localization stage resolves portable selected-source rows against
    staged raw files, extracts only required archive members into
    `localized_audio/`, and persists:
    - `localized_selected_source_records.jsonl`
    - `localized_slice_summary.json`
  - the localized manifest rewrites archive-backed locators to plain local
    audio-file locators so reruns avoid repeated archive-member resolution

- Kept the notebook thin and repo-owned:
  - `colab_ml_training/qwen_portable_slice_row_processing.ipynb` now stages
    required files, runs `localize-slice`, and then invokes canonical Task 103
    row-processing against the localized manifest
  - the Colab worker mix is now:
    - `row_worker_count=8`
    - `gpu_asr_worker_count=2`

- Updated docs-as-code surfaces for the new localized Colab lane:
  - `docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md`
    is terminalized with deliverables/checklists complete
  - `docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md`
    records the localization rationale and the `8:2` probe
  - `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
    now treats localization as the next allowed Colab throughput optimization
  - `docs/backlog/current.md` archives the session outcome and updates next
    actions

- Completed `T125` as a workflow guardrail for future iterations:
  - added `.agents/skills/sir-convert-a-lot-colab-hemma/SKILL.md`
  - registered the skill in `.agents/skills/README.md` and the local global
    skill registry under `~/.codex/skills/sir-convert-a-lot-colab-hemma`
  - cross-linked the rule from the Qwen skill and Qwen Hemma/Colab runbook
  - codified the rule that Hemma-backed execution lanes should be edited,
    committed, and pushed from Hemma

- Completed `T126` after the first Colab rerun exposed a stale notebook clone
  URL:
  - `colab_ml_training/qwen_portable_slice_row_processing.ipynb` now defaults
    to `https://github.com/paunchygent/sir-convert-a-lot.git`
  - the notebook bootstrap now also accepts `SIR_CONVERT_A_LOT_REPO_URL` for
    intentional overrides

- Completed `T127` and `T128` as live Colab operator guardrails:
  - `scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py` now
    prints progress for each required archive, localization start/end per
    archive, extracted/reused file counts, and elapsed time for staging and
    localization
  - `colab_ml_training/qwen_portable_slice_row_processing.ipynb` now checks
    `nvidia-smi` plus `torch.cuda.is_available()` before launching Task 103 and
    fails immediately with a clear GPU-runtime error if CUDA is unavailable

- Completed `T129` as the next Colab scaling-prep slice:
  - `colab_ml_training/qwen_portable_slice_row_processing.ipynb` now defaults
    to the large `task129-scale-slice-1-of-2-20260311a` identifiers
  - the notebook now uses a stable `RUN_ID` plus a persistent Google Drive
    root under `/content/drive/MyDrive/sir-convert-a-lot` so sessions `2` and
    `3` can resume the same Colab-owned slice safely after runtime resets
  - the next Colab worker mix is now preconfigured to:
    - `row_worker_count=10`
    - `gpu_asr_worker_count=2`
  - the Hemma-preparation cell now documents the exact bounded
    `36,000 -> 18,000` source-selection and slice-bundling plan for the next
    multi-session Colab run

- The localized live Colab proof completed successfully:
  - `task121-colab-proof-rowproc-20260310a`
  - `processed_row_count=256`
  - `total_row_count=256`
  - `spool_rows=256`
  - `audio_24k_files=256`
  - observed wall-clock throughput was about `11.2` rows/minute end to end,
    with steady-state intervals around `12-13` rows/minute

- The concurrently running Hemma detached row-processing lane remained healthy
  during the same window:
  - detached launch `task116-rowproc-5x2-resume-20260310b` was still
    `running` at `2026-03-10T19:27:05Z`
  - Task 103 status showed `processed_row_count=4637` of `10024`
  - on-disk counts were `4635` spool rows and `4636` `audio_24k` files
  - the earlier detached Task 116 resource-monitor summary remained healthy,
    though it stopped before the resumed `2026-03-10 17:40Z` segment and should
    be relaunched or refreshed for fresh historical telemetry

- Completed the large-slice Hemma preparation and bundle commit:
  - fresh source-selection launch
    `task129-colab-scale-selection-launch-20260311a` completed at
    `2026-03-10T19:48:59Z`
  - bounded source-selection summary reported `total_selected_rows=36024`
  - the Colab-owned bundle summary reported:
    - `selected_row_count=18000`
    - `required_files_count=6`
    - `datasets=[\"rixvox\"]`
    - `source_splits=[\"train\"]`
  - committed portable bundle:
    `colab_ml_training/proof_inputs/task129-scale-slice-1-of-2-20260311a-bundle.tar.gz`
  - pushed from Hemma as `bc2addd` (`chore: add task129 colab scale slice bundle`)

- Completed `T130` after the first task129 notebook launch exposed one stale
  checkout failure mode:
  - `colab_ml_training/qwen_portable_slice_row_processing.ipynb` now refreshes
    any existing `/content/sir-convert-a-lot` checkout with `fetch`,
    `checkout main`, and `pull --ff-only` before looking for the committed
  portable bundle
  - this fixes the false `FileNotFoundError` path where the bundle existed on
    `main` but the already-open Colab repo clone predated the bundle commit

- Completed `T131` as the next persistent-Colab resume hardening slice:
  - Task 103 row-processing now maintains
    `spool/completed_row_keys.jsonl` inside the run root as a sequential
    completed-row resume index
  - resume now prefers the index fast path, rebuilds it from canonical spool
    JSON when the index is missing or invalid, and logs whether the fast path
    or rebuild path was used
  - stale crash tails self-heal: if a row is missing from the index but its
    canonical spool JSON already exists, resume skips the expensive row work
    and appends that key back into the index
  - added the committed helper surface
    `scripts/sir_convert_a_lot/devops/task103_qwen_resume_index.py`
    with `rebuild` and `validate` commands for historical run roots

- Completed `T132` as the next preprocessing-quality hardening slice:
  - the oversized
    `tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py` monolith was
    removed
  - shared deterministic builders now live in
    `tests/sir_convert_a_lot/task103_test_support.py`
  - the Task 103 test surface is now decomposed into:
    - `tests/sir_convert_a_lot/test_task103_runner.py`
    - `tests/sir_convert_a_lot/test_task103_processing.py`
    - `tests/sir_convert_a_lot/test_task103_sources.py`
    - `tests/sir_convert_a_lot/test_task103_asr.py`
  - this keeps runner/orchestration, preprocessing/resume/finalization,
    source-adapter parsing, and ASR runtime behavior in separate reviewable
    modules before the next Task 103 production refactors

- Completed `T133` as the first Task 103 production refactor after `T132`:
  - added
    `scripts/sir_convert_a_lot/devops/task103_qwen_runner_status.py`
  - extracted Task 103 run-status lifecycle and heartbeat persistence out of
    the public runner into one dedicated helper surface
  - `run_task103_qwen_swedish_preprocessing.py` now delegates allocation,
    running, source-selection, row-processing heartbeat, finalization
    heartbeat, failure, and completion/promotion status writes to the helper
  - added direct tests in
    `tests/sir_convert_a_lot/test_task103_runner_status.py`
    so this seam is independently testable rather than only covered through
    the public runner

- Optimized the decomposed Task 103 processing test surface:
  - `tests/sir_convert_a_lot/task103_test_support.py` now exposes a shared
    helper that stubs both `WhisperStrictScorer.ensure_loaded()` and
    `transcribe()`
  - `tests/sir_convert_a_lot/test_task103_processing.py` now uses that helper
    in the row-processing/resume/finalization cases so focused local test runs
    keep their behavior coverage without triggering unnecessary CPU-side ASR
    pipeline initialization

- Completed `T134` to contain the live Hemma/Colab overlap incident:
  - added
    `scripts/sir_convert_a_lot/devops/task121_qwen_slice_allocation.py`
    so Task 121 can load canonical row keys from completed Task 103 run roots
    and selected-source manifests
  - `task121_qwen_colab_slice_bundle.py` now exposes:
    - `plan-remaining-unique`
    - `dedupe-selected-source-records`
  - the guarded allocation path now subtracts already completed or already
    reserved rows before modulo partitioning future slices
  - the live recovery path can now emit one deduplicated remaining
    selected-source JSONL for the in-flight Colab lane without notebook-only
    overlap logic
  - `ref-qwen3-tts-colab-portable-slice-preprocessing.md` and
    `runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md` now treat guarded
    allocation as canonical after any prior run root or issued slice exists
  - the current live-state ownership comparison now shows:
    - `task129` slice rows: `18000`
    - Hemma processed rows seen in the slice: `4851`
    - Colab completed rows: `7970`
    - union already owned inside the slice: `10653`
    - still-unique remaining rows in the current slice: `7347`

- Completed `T137` to turn overlap containment into a durable canonical model:
  - added `scripts/sir_convert_a_lot/devops/task103_qwen_canonical_processed_root.py`
    so ordered Task 103 run roots can be deduped into one immutable canonical
    processed root with duplicates/conflicts reports
  - split Task 121 portable slice behavior by bounded context into:
    - `task121_qwen_portable_slice_planning.py`
    - `task121_qwen_portable_slice_localization.py`
    - `task121_qwen_shard_registry.py`
    - `task121_qwen_assignment_ledger.py`
  - rewrote `task121_qwen_colab_slice_bundle.py` into a thin canonical CLI
    with no notebook-owned logic and no alias surfaces
  - future work allocation is now intended to be shard-first:
    - build canonical processed root
    - build immutable `~5000`-row shard registry
    - issue processing units from shard ids only

- Completed `T138` to restore order to the live pilot and current Colab lane:
  - materialized canonical pilot root:
    - `/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/task138-qwen-pilot-owned-20260311b`
  - exact current ownership math:
    - Hemma completed rows: `10024`
    - Colab completed rows: `7970`
    - duplicate completed Colab rows: `2158`
    - novel completed Colab rows: `5812`
    - retained canonical unique pilot rows: `15748`
    - quarantined conflicts: `88`
  - created and pushed the repo-owned Colab recovery bundle:
    - `colab_ml_training/proof_inputs/task138-task129-remaining-unique-20260311a-bundle.tar.gz`
    - `sha256=6b260245a5daf208310489c4b4ba59eab4284c45ef4e4fb401519948a1e70d6b`
    - remaining unique rows in the original `task129` slice: `7187`
  - Colab should now resume from the same persistent `task129` run root but
    against the `task138` recovery bundle instead of the original `18000`-row
    bundle
  - important nuance: the canonical root quarantines `88` same-row conflicts,
    so future allocation should eventually exclude those conflicts explicitly
    rather than assuming the retained root alone is a sufficient exclusion set

- Completed `T141` to define the pilot-training bridge:
  - `Task 101`, `Story 25`, the Qwen runbook, and the finetuning guide now
    state the same rule that the first bounded Hemma fine-tune must consume a
    deterministic Task 101 pilot bundle projected from the frozen pilot root
    instead of the generic promoted preprocessing root
  - the relevant operator skills now carry the same rule so the docs and skill
    surfaces do not diverge during future planning or launch work

- Opened `T142` as the next implementation slice for the training lane:
  - materialize one deterministic Task 101 pilot bundle from the frozen pilot
    root through `pdm run task-101-pilot-bundle build`
  - emit:
    - `manifests/swedish_pilot_train.prepared.jsonl`
    - `manifests/swedish_checkpoint_dev.prepared.jsonl`
    - stable per-speaker `refs/`
    - `reports/task101_pilot_bundle_report.json`
  - retarget the detached Task 101 runner away from the generic promoted Task
    103 preprocessing root and onto `pilot_bundle_root`

## Validation Evidence

- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py -q`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `pdm run python -c "import json, pathlib; json.loads(pathlib.Path('colab_ml_training/qwen_portable_slice_row_processing.ipynb').read_text(encoding='utf-8')); print('notebook-json-ok')"`
- `pdm run python /Users/olofs_mba/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/sir-convert-a-lot-colab-hemma`
- `rg -n "paunchygent/sir-convert-a-lot|SIR_CONVERT_A_LOT_REPO_URL" colab_ml_training/qwen_portable_slice_row_processing.ipynb`
- `pdm run run-hemma -- pdm run task-114-isolated-stages status --launch-root build/verification/task-114-qwen-isolated-stages/task116-rowproc-5x2-resume-20260310b`
- `pdm run run-hemma --shell 'find /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task116-rowproc-5x2-20260309c/spool/rows -type f | wc -l'`
- `pdm run run-hemma --shell 'find /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task116-rowproc-5x2-20260309c/audio_24k -type f | wc -l'`
- `pdm run run-hemma -- pdm run task-103-preprocess-public-corpus launch --task103-stage source-selection --launch-id task129-colab-scale-selection-launch-20260311a --task103-run-id task129-colab-scale-selection-20260311a --rixvox-split train --rixvox-max-rows-per-split 36000 --skip-build`
- `pdm run run-hemma -- sudo -n cat /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task129-colab-scale-selection-20260311a/status.json`
- `pdm run run-hemma -- sudo -n /home/paunchygent/.local/bin/pdm run task-121-colab-slice-bundle plan --source-run-root /srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/task129-colab-scale-selection-20260311a --output-root /srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-colab-slices/task129-scale-slice-1-of-2-20260311a --slice-count 2 --slice-index 1`
- `sha256sum colab_ml_training/proof_inputs/task129-scale-slice-1-of-2-20260311a-bundle.tar.gz`
- `pdm run python -c "import json, pathlib; json.loads(pathlib.Path('colab_ml_training/qwen_portable_slice_row_processing.ipynb').read_text(encoding='utf-8')); print('notebook-json-ok')"`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root \"$(pwd)/docs/backlog\" --out \"/tmp/sir_tasks_index.md\" --fail-on-missing`
- `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_storage.py scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_row_stage.py scripts/sir_convert_a_lot/devops/task103_qwen_resume_index.py tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py -q`
- `pdm run python -m py_compile scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_storage.py scripts/sir_convert_a_lot/devops/task103_qwen_preprocessing_row_stage.py scripts/sir_convert_a_lot/devops/task103_qwen_resume_index.py`
- `pdm run python -m ruff check tests/sir_convert_a_lot/task103_test_support.py tests/sir_convert_a_lot/test_task103_runner.py tests/sir_convert_a_lot/test_task103_processing.py tests/sir_convert_a_lot/test_task103_sources.py tests/sir_convert_a_lot/test_task103_asr.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task103_runner.py tests/sir_convert_a_lot/test_task103_processing.py tests/sir_convert_a_lot/test_task103_sources.py tests/sir_convert_a_lot/test_task103_asr.py -q`
- `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task103_qwen_runner_status.py scripts/sir_convert_a_lot/devops/run_task103_qwen_swedish_preprocessing.py tests/sir_convert_a_lot/test_task103_runner_status.py tests/sir_convert_a_lot/test_task103_runner.py`
- `pdm run python -m mypy scripts/sir_convert_a_lot/devops/task103_qwen_runner_status.py scripts/sir_convert_a_lot/devops/run_task103_qwen_swedish_preprocessing.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task103_runner_status.py tests/sir_convert_a_lot/test_task103_runner.py tests/sir_convert_a_lot/test_task103_processing.py -q`
- `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task121_qwen_slice_allocation.py scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py`
- `pdm run python -m mypy scripts/sir_convert_a_lot/devops/task121_qwen_slice_allocation.py scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py -q`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `pdm run python -m ruff check scripts/sir_convert_a_lot/devops/task103_qwen_canonical_processed_root.py scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py scripts/sir_convert_a_lot/devops/task121_qwen_shard_registry.py scripts/sir_convert_a_lot/devops/task121_qwen_assignment_ledger.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_planning.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_localization.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_models.py tests/sir_convert_a_lot/test_task103_qwen_canonical_processed_root.py tests/sir_convert_a_lot/test_task121_qwen_shard_registry.py tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py`
- `pdm run python -m mypy scripts/sir_convert_a_lot/devops/task103_qwen_canonical_processed_root.py scripts/sir_convert_a_lot/devops/task121_qwen_colab_slice_bundle.py scripts/sir_convert_a_lot/devops/task121_qwen_shard_registry.py scripts/sir_convert_a_lot/devops/task121_qwen_assignment_ledger.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_planning.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_localization.py scripts/sir_convert_a_lot/devops/task121_qwen_portable_slice_models.py`
- `pdm run pytest-root tests/sir_convert_a_lot/test_task103_qwen_canonical_processed_root.py tests/sir_convert_a_lot/test_task121_qwen_shard_registry.py tests/sir_convert_a_lot/test_task121_qwen_colab_slice_bundle.py -q`

## Next Session Goals

- Build the first canonical processed root from the chosen completed Task 103
  run roots, then use that canonical root as the only durable ownership base
  for future allocation.
- Cut the remaining universe into immutable `~5000`-row shards and issue the
  next processing units from shard ids only.
- Keep `plan-remaining-unique` and `dedupe-selected-source-records` as
  recovery-only surfaces for already-issued manifests, not the long-term
  allocation path.
- Refresh or relaunch the detached Task 116 Hemma resource monitor so resumed
  `task116-rowproc-5x2-20260309c` telemetry covers the post-`17:40Z` segment.
- Use the decomposed `T132` Task 103 test surface as the guardrail for the
  next production refactor pass, starting with runner/orchestration
  responsibility review instead of adding more behavior into the old monolith.
- Continue the Task 103 production refactor sequence after `T133` by reviewing
  source-resolution and run-metadata orchestration as the next extraction
  candidate now that status lifecycle ownership has moved out of the public
  runner.
- Execute `T142` so the next canonical Hemma Task 101 pilot launches from the
  deterministic pilot bundle rooted in the frozen pilot ownership set.
