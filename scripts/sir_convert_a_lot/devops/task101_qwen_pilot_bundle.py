"""Task 101 pilot-bundle materialization for frozen Qwen pilot ownership.

Purpose:
    Project the frozen canonical Qwen pilot root into one deterministic Task
    101 training bundle so the bounded Hemma fine-tune consumes immutable
    prepared manifests, stable speaker references, and machine-readable bundle
    metadata instead of a generic promoted preprocessing root.

Relationships:
    - Consumes the frozen canonical processed root emitted by
      `task103_qwen_canonical_processed_root.py`.
    - Reuses Task 103 row/finalization contracts while replacing the old
      whole-family finalization pass with Task 101 batch-plan, progress, and
      batch-shard helpers from the `task101_qwen_pilot_bundle_batch_*`
      modules.
    - Supplies the canonical input root consumed by
      `run_task101_hemma_qwen_pilot.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from scripts.sir_convert_a_lot.devops import (
    task101_qwen_pilot_bundle_source as bundle_source,
)
from scripts.sir_convert_a_lot.devops import (
    task101_qwen_pilot_bundle_validation as bundle_validation,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    Task101PilotBundleBatchPlan,
    build_task101_pilot_bundle_batch_plan,
    load_task101_pilot_bundle_batch_plan,
    selected_manifest_families,
    task101_pilot_bundle_batch_plan_path,
    task101_pilot_bundle_progress_events_path,
    task101_pilot_bundle_progress_state_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    assemble_task101_pilot_bundle_from_batches,
    ensure_reference_audio_paths,
    task101_pilot_bundle_batch_is_complete,
    validate_task101_pilot_bundle_batch_outputs,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_progress import (
    record_task101_pilot_bundle_progress_event,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleRuntimeFingerprint,
    prepare_task101_pilot_bundle_batch_runtime,
    run_containerized_task101_pilot_bundle_batch,
    validate_runtime_fingerprint_matches,
    write_task101_pilot_bundle_runtime_fingerprint,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesEncoderProtocol,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_spool_rows,
    rebuild_completed_row_keys_index,
    write_json,
    write_spool_row,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import load_row_key_records
from scripts.sir_convert_a_lot.devops.task112_hemma_storage_runtime import (
    DEFAULT_SCRATCH_BUILD_ROOT,
)

DEFAULT_FROZEN_PILOT_ROOT = Path(
    "/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/"
    "task140-qwen-pilot-frozen-20260311a"
)
DEFAULT_PILOT_BUNDLE_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "reference/qwen3-tts-swedish-task101-pilot-bundle"
)
DEFAULT_TRAIN_MANIFEST_FAMILY: ManifestFamily = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY: ManifestFamily = "swedish_checkpoint_dev"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 64
DEFAULT_CONTAINER_BATCH_SPAN = 4


@dataclass(frozen=True)
class Task101PilotBundleSummary:
    """Machine-readable summary for one deterministic Task 101 pilot bundle."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    retained_row_count: int
    conflict_row_count: int
    manifest_row_counts: dict[ManifestFamily, int]
    speaker_counts: dict[ManifestFamily, int]
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str
    finalization_batch_row_count: int
    total_batch_count: int
    batch_plan_path: str
    events_path: str
    status_path: str


Task101PilotBundleBatchRunner = Callable[
    [
        Path,
        Task101PilotBundleBatchPlan,
        ManifestFamily,
        int,
        int,
        AudioCodesEncoderProtocol,
        Path,
    ],
    None,
]


def task101_pilot_bundle_report_path(output_root: Path) -> Path:
    """Return the machine-readable report path for one pilot bundle."""
    return output_root / "reports" / "task101_pilot_bundle_report.json"


def task101_pilot_bundle_manifest_path(
    output_root: Path,
    manifest_family: str,
) -> Path:
    """Return one prepared-manifest path inside the Task 101 pilot bundle."""
    return output_root / "manifests" / f"{manifest_family}.prepared.jsonl"


def build_task101_pilot_bundle(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
    audio_codes_chunk_size: int,
    container_batch_span: int,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    repo_root: Path,
    run_batch_fn: Task101PilotBundleBatchRunner | None = None,
    expected_runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None = None,
) -> Task101PilotBundleSummary:
    """Materialize or resume one deterministic batched Task 101 pilot bundle."""
    effective_runtime_fingerprint = expected_runtime_fingerprint
    effective_run_batch_fn = run_batch_fn
    if effective_run_batch_fn is None:
        if container_batch_span <= 0:
            raise ValueError("`container_batch_span` must be positive.")
        hf_mount, effective_runtime_fingerprint = prepare_task101_pilot_bundle_batch_runtime()

        def _run_containerized_batch(
            batch_output_root: Path,
            plan: Task101PilotBundleBatchPlan,
            manifest_family: ManifestFamily,
            batch_index: int,
            batch_audio_codes_chunk_size: int,
            batch_encode_audio_codes_fn: AudioCodesEncoderProtocol,
            batch_repo_root: Path,
        ) -> None:
            del batch_encode_audio_codes_fn
            if effective_runtime_fingerprint is None:
                raise RuntimeError(
                    "Task 101 containerized batch runner is missing a runtime fingerprint."
                )
            batch_count = _container_batch_span_for_request(
                plan=plan,
                output_root=batch_output_root,
                manifest_family=manifest_family,
                batch_index=batch_index,
                requested_span=container_batch_span,
                expected_runtime_fingerprint=effective_runtime_fingerprint,
            )
            run_containerized_task101_pilot_bundle_batch(
                repo_root=batch_repo_root,
                output_root=batch_output_root,
                manifest_family=manifest_family,
                batch_index=batch_index,
                batch_count=batch_count,
                audio_codes_chunk_size=batch_audio_codes_chunk_size,
                hf_mount=hf_mount,
                fingerprint=effective_runtime_fingerprint,
            )

        effective_run_batch_fn = _run_containerized_batch
    if task101_pilot_bundle_report_path(output_root).exists():
        plan = load_task101_pilot_bundle_batch_plan(output_root)
        _ensure_loaded_plan_matches_request(
            plan,
            source_root=source_root,
            output_root=output_root,
            train_manifest_family=train_manifest_family,
            eval_manifest_family=eval_manifest_family,
            tokenizer_model=tokenizer_model,
            finalization_batch_row_count=finalization_batch_row_count,
        )
        bundle_validation.validate_task101_pilot_bundle_paths(
            output_root,
            selected_manifest_families(plan),
        )
        _validate_completed_bundle_runtime(
            output_root=output_root,
            plan=plan,
            expected_runtime_fingerprint=effective_runtime_fingerprint,
        )
        return _load_task101_pilot_bundle_summary(output_root)
    plan = copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        repo_root=repo_root,
    )
    if effective_runtime_fingerprint is not None:
        write_task101_pilot_bundle_runtime_fingerprint(output_root, effective_runtime_fingerprint)
    for batch in plan.batches:
        if task101_pilot_bundle_batch_is_complete(
            output_root,
            batch,
            expected_runtime_fingerprint=effective_runtime_fingerprint,
        ):
            record_task101_pilot_bundle_progress_event(
                output_root=output_root,
                plan=plan,
                event="batch_skipped_existing",
                batch=batch,
                detail="validated_batch_shard_exists",
            )
            continue
        effective_run_batch_fn(
            output_root,
            plan,
            batch.manifest_family,
            batch.batch_index,
            audio_codes_chunk_size,
            encode_audio_codes_fn,
            repo_root,
        )
    return assemble_task101_pilot_bundle(output_root=output_root, plan=plan)


def copy_task101_pilot_bundle_inputs(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
    repo_root: Path,
) -> Task101PilotBundleBatchPlan:
    """Copy retained Task 101 inputs and emit the deterministic batch plan."""
    if task101_pilot_bundle_batch_plan_path(output_root).exists():
        plan = load_task101_pilot_bundle_batch_plan(output_root)
        _ensure_loaded_plan_matches_request(
            plan,
            source_root=source_root,
            output_root=output_root,
            train_manifest_family=train_manifest_family,
            eval_manifest_family=eval_manifest_family,
            tokenizer_model=tokenizer_model,
            finalization_batch_row_count=finalization_batch_row_count,
        )
        return plan
    if output_root.exists():
        raise ValueError(
            "Task 101 pilot-bundle output must be a new path unless it already "
            "contains `reports/task101_pilot_bundle_plan.json` for a resumable build."
        )
    selected_families = _selected_manifest_families(
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
    )
    owned_row_keys_path, conflict_row_keys_path, conflict_row_count = (
        bundle_source.freeze_artifact_paths(source_root)
    )
    owned_row_keys = load_row_key_records(owned_row_keys_path)
    bundle_source.ensure_bundle_output_capacity(
        source_root=source_root,
        output_root=output_root,
        owned_row_keys=owned_row_keys,
        selected_families=selected_families,
    )
    copied_row_count = 0
    for spool_row in iter_spool_rows(source_root):
        row_key = bundle_source.row_key_from_spool_row(spool_row)
        if row_key not in owned_row_keys:
            raise ValueError(
                "Frozen pilot bundle encountered a spool row not present in the owned-row ledger: "
                f"{row_key!r}"
            )
        selected_targets = tuple(
            family for family in spool_row.manifest_targets if family in selected_families
        )
        if spool_row.admission_decision != "admit" or not selected_targets:
            continue
        bundle_row = replace(
            spool_row,
            manifest_targets=selected_targets,
            reference_audio_24k_paths={
                family: relative_path
                for family, relative_path in spool_row.reference_audio_24k_paths.items()
                if family in selected_families
            },
        )
        write_spool_row(output_root, bundle_row)
        bundle_source.copy_artifact_with_fallback(
            source_path=source_root / bundle_row.audio_24k_path,
            output_root=output_root,
            relative_path=Path(bundle_row.audio_24k_path),
        )
        copied_row_count += 1
    if copied_row_count == 0:
        raise ValueError("Task 101 pilot bundle cannot be empty.")
    rebuild_completed_row_keys_index(output_root)
    ensure_reference_audio_paths(output_root, selected_families)
    plan = build_task101_pilot_bundle_batch_plan(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        finalization_batch_row_count=finalization_batch_row_count,
        retained_row_count=copied_row_count,
        conflict_row_count=conflict_row_count,
        owned_row_keys_path=owned_row_keys_path,
        conflict_row_keys_path=conflict_row_keys_path,
        repo_head=bundle_source.git_head(repo_root),
        generated_at=bundle_source.utc_now_iso(),
    )
    for family in selected_families:
        if plan.family_row_counts[family] <= 0:
            raise ValueError(f"Task 101 pilot bundle is missing retained rows for `{family}`.")
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="copy_completed",
        detail="retained_spool_and_audio_ready",
        extra_fields={
            "retained_row_count": copied_row_count,
            "finalization_batch_row_count": finalization_batch_row_count,
            "total_batch_count": len(plan.batches),
            "family_row_counts": plan.family_row_counts,
        },
    )
    return plan


def assemble_task101_pilot_bundle(
    *,
    output_root: Path,
    plan: Task101PilotBundleBatchPlan,
) -> Task101PilotBundleSummary:
    """Assemble final manifests/report from validated batch shards."""
    assemble_task101_pilot_bundle_from_batches(output_root=output_root, plan=plan)
    families = selected_manifest_families(plan)
    bundle_validation.validate_task101_pilot_bundle_paths(output_root, families)
    manifest_row_counts = bundle_validation.manifest_row_counts(output_root, families)
    for family in families:
        if manifest_row_counts[family] <= 0:
            raise ValueError(f"Task 101 pilot bundle is missing retained rows for `{family}`.")
    speaker_counts = bundle_validation.speaker_counts(output_root, families)
    summary = Task101PilotBundleSummary(
        source_root=plan.source_root,
        output_root=plan.output_root,
        train_manifest_family=plan.train_manifest_family,
        eval_manifest_family=plan.eval_manifest_family,
        tokenizer_model=plan.tokenizer_model,
        retained_row_count=plan.retained_row_count,
        conflict_row_count=plan.conflict_row_count,
        manifest_row_counts=manifest_row_counts,
        speaker_counts=speaker_counts,
        owned_row_keys_path=plan.owned_row_keys_path,
        conflict_row_keys_path=plan.conflict_row_keys_path,
        repo_head=plan.repo_head,
        generated_at=bundle_source.utc_now_iso(),
        finalization_batch_row_count=plan.finalization_batch_row_count,
        total_batch_count=len(plan.batches),
        batch_plan_path=task101_pilot_bundle_batch_plan_path(output_root).as_posix(),
        events_path=task101_pilot_bundle_progress_events_path(output_root).as_posix(),
        status_path=task101_pilot_bundle_progress_state_path(output_root).as_posix(),
    )
    write_json(task101_pilot_bundle_report_path(output_root), summary)
    record_task101_pilot_bundle_progress_event(
        output_root=output_root,
        plan=plan,
        event="report_completed",
        detail="task101_pilot_bundle_report.json",
        extra_fields={
            "manifest_row_counts": manifest_row_counts,
            "speaker_counts": speaker_counts,
            "total_batch_count": len(plan.batches),
        },
    )
    return summary


def _selected_manifest_families(
    *,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
) -> tuple[ManifestFamily, ManifestFamily]:
    """Return the canonical ordered manifest families for one pilot bundle."""
    if train_manifest_family == eval_manifest_family:
        raise ValueError("Train and eval manifest families must be distinct.")
    return (train_manifest_family, eval_manifest_family)


def _ensure_loaded_plan_matches_request(
    plan: Task101PilotBundleBatchPlan,
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    finalization_batch_row_count: int,
) -> None:
    """Fail closed when a resumable bundle root does not match the new request."""
    if Path(plan.source_root).resolve(strict=False) != source_root.resolve(strict=False):
        raise ValueError("Existing Task 101 batch plan source root does not match the request.")
    if Path(plan.output_root).resolve(strict=False) != output_root.resolve(strict=False):
        raise ValueError("Existing Task 101 batch plan output root does not match the request.")
    if plan.train_manifest_family != train_manifest_family:
        raise ValueError("Existing Task 101 batch plan train manifest family does not match.")
    if plan.eval_manifest_family != eval_manifest_family:
        raise ValueError("Existing Task 101 batch plan eval manifest family does not match.")
    if plan.tokenizer_model != tokenizer_model:
        raise ValueError("Existing Task 101 batch plan tokenizer model does not match.")
    if plan.finalization_batch_row_count != finalization_batch_row_count:
        raise ValueError("Existing Task 101 batch plan batch-row count does not match.")


def _container_batch_span_for_request(
    *,
    plan: Task101PilotBundleBatchPlan,
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
    requested_span: int,
    expected_runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None,
) -> int:
    """Return the contiguous incomplete batch count to launch in one container."""
    if requested_span <= 1:
        return 1
    selected_batches = [
        candidate
        for candidate in plan.batches
        if candidate.manifest_family == manifest_family and candidate.batch_index >= batch_index
    ]
    if not selected_batches:
        return 1
    contiguous_incomplete_count = 0
    expected_batch_index = batch_index
    for batch in selected_batches:
        if batch.batch_index != expected_batch_index:
            break
        if task101_pilot_bundle_batch_is_complete(
            output_root,
            batch,
            expected_runtime_fingerprint=expected_runtime_fingerprint,
        ):
            break
        contiguous_incomplete_count += 1
        expected_batch_index += 1
        if contiguous_incomplete_count >= requested_span:
            break
    return max(contiguous_incomplete_count, 1)


def _load_task101_pilot_bundle_summary(output_root: Path) -> Task101PilotBundleSummary:
    """Load one completed Task 101 pilot-bundle summary from disk."""
    payload = json.loads(task101_pilot_bundle_report_path(output_root).read_text("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Task 101 pilot bundle report must be one JSON object.")
    return Task101PilotBundleSummary(
        source_root=bundle_validation.required_string(payload, "source_root"),
        output_root=bundle_validation.required_string(payload, "output_root"),
        train_manifest_family=bundle_validation.required_manifest_family(
            payload,
            "train_manifest_family",
        ),
        eval_manifest_family=bundle_validation.required_manifest_family(
            payload,
            "eval_manifest_family",
        ),
        tokenizer_model=bundle_validation.required_string(payload, "tokenizer_model"),
        retained_row_count=bundle_validation.required_int(payload, "retained_row_count"),
        conflict_row_count=bundle_validation.required_int(payload, "conflict_row_count"),
        manifest_row_counts=bundle_validation.required_manifest_count_map(
            payload,
            "manifest_row_counts",
        ),
        speaker_counts=bundle_validation.required_manifest_count_map(
            payload,
            "speaker_counts",
        ),
        owned_row_keys_path=bundle_validation.required_string(payload, "owned_row_keys_path"),
        conflict_row_keys_path=bundle_validation.required_string(
            payload,
            "conflict_row_keys_path",
        ),
        repo_head=bundle_validation.required_string(payload, "repo_head"),
        generated_at=bundle_validation.required_string(payload, "generated_at"),
        finalization_batch_row_count=bundle_validation.required_int(
            payload,
            "finalization_batch_row_count",
        ),
        total_batch_count=bundle_validation.required_int(payload, "total_batch_count"),
        batch_plan_path=bundle_validation.required_string(payload, "batch_plan_path"),
        events_path=bundle_validation.required_string(payload, "events_path"),
        status_path=bundle_validation.required_string(payload, "status_path"),
    )


def _validate_completed_bundle_runtime(
    *,
    output_root: Path,
    plan: Task101PilotBundleBatchPlan,
    expected_runtime_fingerprint: Task101PilotBundleRuntimeFingerprint | None,
) -> None:
    """Fail closed when one completed bundle does not match the current runtime request."""
    if expected_runtime_fingerprint is None:
        return
    try:
        observed_runtime_fingerprint = bundle_validation.load_bundle_runtime_fingerprint(
            output_root
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "Existing completed Task 101 pilot bundle does not record the governed container "
            "runtime fingerprint required by the current request."
        ) from exc
    validate_runtime_fingerprint_matches(
        observed_runtime_fingerprint,
        expected_runtime_fingerprint,
    )
    for batch in plan.batches:
        validate_task101_pilot_bundle_batch_outputs(
            output_root,
            batch,
            expected_runtime_fingerprint=expected_runtime_fingerprint,
        )
