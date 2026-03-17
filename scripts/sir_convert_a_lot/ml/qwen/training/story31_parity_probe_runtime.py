"""Runtime orchestration for the Story 31 deterministic parity probe.

Purpose:
    Prepare one bounded Qwen runtime per comparison path, resolve the exact
    `T225` microbatch family, and project the resulting execution artifacts
    into the stable `Story31ParityPathReport` contract used by the runner.

Relationships:
    - Imported by `story31_parity_probe_runner.py`.
    - Delegates execution to `story31_parity_probe_execution.py`.
    - Delegates artifact shaping to `story31_parity_probe_artifacts.py`.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import prepare_training_run
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_artifacts import (
    collated_batch_signature,
    dataset_item_signature,
    runtime_posture,
    selected_row_signature,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_contracts import (
    DEFAULT_EXECUTION_MODE_CURRENT,
    DEFAULT_EXECUTION_MODE_INTENDED,
    DEFAULT_PATH_LABEL_CURRENT,
    Story31ParityPathReport,
    Story31ParityProbeSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe_execution import (
    build_runtime_args,
    cleanup_prepared_run,
    require_training_dataset,
    run_current_train_step_window,
    run_reconstructed_shared_window,
    seed_everything,
    select_rows,
)


def run_parity_path(
    settings: Story31ParityProbeSettings,
    *,
    path_label: str,
) -> Story31ParityPathReport:
    """Execute one deterministic parity path and return comparable artifacts."""
    seed_everything(settings.deterministic_seed)
    output_model_path = settings.output_root / path_label / "model-output"
    prepared = prepare_training_run(
        build_runtime_args(settings, output_model_path=output_model_path)
    )
    prepared.model.train()
    try:
        dataset = require_training_dataset(prepared)
        selected_rows = select_rows(dataset, manifest_lines=settings.manifest_lines)
        selected_items = [dataset[selected.dataset_index] for selected in selected_rows]
        collated_batches = tuple(dataset.collate_fn([item]) for item in selected_items)
        execution = (
            run_current_train_step_window(prepared, collated_batches)
            if path_label == DEFAULT_PATH_LABEL_CURRENT
            else run_reconstructed_shared_window(prepared, collated_batches)
        )
        execution_mode = (
            DEFAULT_EXECUTION_MODE_CURRENT
            if path_label == DEFAULT_PATH_LABEL_CURRENT
            else DEFAULT_EXECUTION_MODE_INTENDED
        )
        return Story31ParityPathReport(
            path_label=path_label,
            execution_mode=execution_mode,
            output_model_path=output_model_path.as_posix(),
            runtime_posture=runtime_posture(prepared),
            selected_rows=tuple(
                selected_row_signature(
                    row=selected.row,
                    dataset_index=selected.dataset_index,
                )
                for selected in selected_rows
            ),
            per_item_dataset_output=tuple(
                dataset_item_signature(item=item) for item in selected_items
            ),
            collated_batch_tensors=tuple(
                collated_batch_signature(batch=batch) for batch in collated_batches
            ),
            forward_entry_surfaces=execution.forward_entry_surfaces,
            loss_decomposition=execution.loss_decomposition,
            backward_pre_clip=execution.backward_pre_clip,
            clip_boundary=execution.clip_boundary,
            optimizer_preconditions=execution.optimizer_preconditions,
            step_forensics=execution.step_forensics,
            execution_outcome=execution.execution_outcome,
        )
    finally:
        cleanup_prepared_run(prepared)
