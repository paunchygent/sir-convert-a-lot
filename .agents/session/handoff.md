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

## Next Session Goals

- Prepare the next large Colab-owned slice on Hemma with:
  - one fresh bounded `rixvox train` source-selection universe capped at
    `36,000` rows
  - `slice_count=2`
  - Colab assigned `slice_index=1`
- Commit and push the `task129-scale-slice-1-of-2-20260311a` bundle from the
  Hemma repo clone so the notebook can stay press-run simple.
- Launch the next Colab run with the persistent Google Drive `RUN_ROOT` and
  `row_worker_count=10`, `gpu_asr_worker_count=2`.
- Refresh or relaunch the detached Task 116 Hemma resource monitor so resumed
  `task116-rowproc-5x2-20260309c` telemetry covers the post-`17:40Z` segment.
