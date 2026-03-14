"""Public CLI entrypoint for the Qwen Swedish preprocessing pipeline.

Purpose:
    Provide the canonical preprocessing runner for source selection,
    row-processing, finalization, and report promotion under the new
    domain-centric Qwen structure.

Relationships:
    - Wraps `ml.qwen.preprocessing.pipeline`.
    - Persists selected-source artifacts through `ml.qwen.preprocessing.sharding`.
    - Uses staged public-corpus loading from `ml.qwen.preprocessing.public_corpus`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import traceback
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Sequence

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    FinalizationHeartbeat,
    ManifestFamily,
    RowProcessingHeartbeat,
    SourceRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import (
    default_data_root,
    ensure_bulk_data_storage_path,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    PreprocessingReport,
    PreprocessingSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.pipeline import (
    run_preprocessing_pipeline,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.public_corpus import (
    resolve_selected_source_records_for_local_data,
    staged_public_corpus_source_records,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
    SourceSelectionHeartbeat,
    SourceSelectionSummary,
    load_selected_source_records,
    load_source_records_from_jsonl_path,
    write_selected_source_records,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import write_json

DEFAULT_OUTPUT_ROOT = Path("build/reference/qwen3-tts-swedish-corpus")
DEFAULT_RUNS_ROOT = Path("build/runs/qwen3-tts-swedish-preprocessing")
DEFAULT_ASR_MODEL = "KBLab/kb-whisper-large"
DEFAULT_ASR_REVISION = "strict"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_SOURCE_MODE = "repo-fixture"
DEFAULT_FLEURS_SPLITS = ("dev", "test")
DEFAULT_RIXVOX_SPLITS = ("dev", "test")
DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT: int | None = None
DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT: int | None = None
DEFAULT_STAGE = "row-processing"
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 8
DEFAULT_ROW_WORKER_COUNT = 1
DEFAULT_GPU_ASR_WORKER_COUNT = 1

SourceMode = Literal["repo-fixture", "staged-public-corpus", "selected-source-records"]
RunStatus = Literal["allocated", "running", "failed", "completed", "promoted"]


@dataclass(frozen=True)
class RunContext:
    """Resolved run-root context for one preprocessing invocation."""

    run_id: str
    run_root: Path
    promoted_root: Path
    runs_root: Path
    uses_run_root: bool
    promote_on_success: bool


@dataclass(frozen=True)
class PreprocessingRunnerSettings:
    """Normalized CLI settings for the public preprocessing runner."""

    preprocessing: PreprocessingSettings
    source_mode: SourceMode
    data_root: Path
    selected_source_records_path: Path | None
    fleurs_splits: tuple[str, ...]
    fleurs_max_rows_per_split: int | None
    rixvox_splits: tuple[str, ...]
    rixvox_max_rows_per_split: int | None
    runs_root: Path
    run_id: str | None
    run_root: Path | None
    promote_on_success: bool


def _utc_now_iso() -> str:
    """Return the current UTC time in RFC3339 form."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_run_id() -> str:
    """Return a deterministic timestamp-based run id."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ").lower()


def _parse_csv_list(raw_value: str) -> tuple[str, ...]:
    """Parse one comma-separated CLI list into a normalized tuple."""
    parsed_values = tuple(value.strip() for value in raw_value.split(",") if value.strip() != "")
    if not parsed_values:
        raise SystemExit("Expected at least one split value.")
    return parsed_values


def _manifest_family_from_cli_value(value: str) -> ManifestFamily:
    """Convert one manifest-family CLI value into the typed literal."""
    if value == "swedish_smoke_train":
        return "swedish_smoke_train"
    if value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if value == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if value == "swedish_final_test":
        return "swedish_final_test"
    if value == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise SystemExit(f"Unknown manifest family: {value}")


def _parse_manifest_families(raw_value: str) -> tuple[ManifestFamily, ...]:
    """Parse one manifest-family CSV list into typed family literals."""
    return tuple(_manifest_family_from_cli_value(value) for value in _parse_csv_list(raw_value))


def _parse_args(argv: list[str] | None) -> PreprocessingRunnerSettings:
    """Parse CLI arguments into normalized preprocessing runner settings."""
    parser = argparse.ArgumentParser(description="Run the canonical Qwen preprocessing bundle.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument(
        "--promote-on-success",
        action="store_true",
        help="Promote the completed run root into the canonical shared corpus path.",
    )
    parser.add_argument("--asr-model", default=DEFAULT_ASR_MODEL)
    parser.add_argument("--asr-revision", default=DEFAULT_ASR_REVISION)
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    parser.add_argument(
        "--stage",
        choices=("all", "source-selection", "row-processing", "finalization", "reports"),
        default=DEFAULT_STAGE,
    )
    parser.add_argument(
        "--allow-noncanonical-stage-all",
        action="store_true",
        help="Allow one combined `all` stage for explicit local debugging only.",
    )
    parser.add_argument("--finalization-families", default=",".join(CANONICAL_MANIFEST_FAMILIES))
    parser.add_argument(
        "--audio-codes-chunk-size",
        type=int,
        default=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )
    parser.add_argument("--audio-codes-device-map", default=None)
    parser.add_argument(
        "--audio-codes-dtype",
        choices=("float16", "bfloat16", "float32"),
        default=None,
    )
    parser.add_argument(
        "--audio-codes-attn-implementation",
        choices=("eager", "sdpa", "flash_attention_2"),
        default=None,
    )
    parser.add_argument("--require-audio-codes-gpu", action="store_true")
    parser.add_argument("--row-worker-count", type=int, default=DEFAULT_ROW_WORKER_COUNT)
    parser.add_argument(
        "--gpu-asr-worker-count",
        type=int,
        default=DEFAULT_GPU_ASR_WORKER_COUNT,
    )
    parser.add_argument(
        "--resume-row-processing",
        action="store_true",
        help="Resume row-processing from an existing run root instead of wiping spool/audio state.",
    )
    parser.add_argument(
        "--source-mode",
        choices=("repo-fixture", "staged-public-corpus", "selected-source-records"),
        default=DEFAULT_SOURCE_MODE,
    )
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--selected-source-records-path", type=Path, default=None)
    parser.add_argument("--fleurs-splits", default=",".join(DEFAULT_FLEURS_SPLITS))
    parser.add_argument(
        "--fleurs-max-rows-per-split",
        type=int,
        default=DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    )
    parser.add_argument("--rixvox-splits", default=",".join(DEFAULT_RIXVOX_SPLITS))
    parser.add_argument(
        "--rixvox-max-rows-per-split",
        type=int,
        default=DEFAULT_RIXVOX_MAX_ROWS_PER_SPLIT,
    )
    args = parser.parse_args(argv)

    if args.stage == "all" and not bool(args.allow_noncanonical_stage_all):
        raise SystemExit(
            "The canonical preprocessing runner no longer treats `stage=all` as canonical. "
            "Use explicit row-processing/finalization/reports stages instead."
        )
    if bool(args.promote_on_success) and str(args.stage) != "reports":
        raise SystemExit(
            "Preprocessing promotion is only allowed for the `reports` stage. "
            "Run row-processing and finalization first, then promote from reports."
        )
    if bool(args.resume_row_processing) and str(args.stage) != "row-processing":
        raise SystemExit("`--resume-row-processing` is only valid for the `row-processing` stage.")

    return PreprocessingRunnerSettings(
        preprocessing=PreprocessingSettings(
            output_root=Path(args.output_root),
            asr_model=str(args.asr_model),
            asr_revision=str(args.asr_revision),
            tokenizer_model=str(args.tokenizer_model),
            stage=args.stage,
            finalization_families=_parse_manifest_families(str(args.finalization_families)),
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            row_worker_count=int(args.row_worker_count),
            gpu_asr_worker_count=int(args.gpu_asr_worker_count),
            resume_row_processing=bool(args.resume_row_processing),
        ),
        source_mode=args.source_mode,
        data_root=Path(args.data_root),
        selected_source_records_path=(
            None
            if args.selected_source_records_path is None
            else Path(args.selected_source_records_path)
        ),
        fleurs_splits=_parse_csv_list(str(args.fleurs_splits)),
        fleurs_max_rows_per_split=args.fleurs_max_rows_per_split,
        rixvox_splits=_parse_csv_list(str(args.rixvox_splits)),
        rixvox_max_rows_per_split=args.rixvox_max_rows_per_split,
        runs_root=Path(args.runs_root),
        run_id=None if args.run_id is None else str(args.run_id),
        run_root=None if args.run_root is None else Path(args.run_root),
        promote_on_success=bool(args.promote_on_success),
    )


def _resolve_run_context(settings: PreprocessingRunnerSettings) -> RunContext:
    """Resolve the effective run-root context for one preprocessing invocation."""
    promoted_root = settings.preprocessing.output_root.resolve()
    runs_root = settings.runs_root.resolve()
    if settings.run_root is not None and settings.run_id is not None:
        raise SystemExit("Use either `--run-root` or `--run-id`, not both.")
    if settings.run_root is not None:
        resolved_run_root = settings.run_root.resolve()
        run_id = resolved_run_root.name
        uses_run_root = True
    elif (
        settings.source_mode == "staged-public-corpus"
        or settings.run_id is not None
        or settings.promote_on_success
    ):
        run_id = settings.run_id or _default_run_id()
        resolved_run_root = (runs_root / run_id).resolve()
        uses_run_root = True
    else:
        run_id = "direct-output"
        resolved_run_root = promoted_root
        uses_run_root = False
    return RunContext(
        run_id=run_id,
        run_root=resolved_run_root,
        promoted_root=promoted_root,
        runs_root=runs_root,
        uses_run_root=uses_run_root,
        promote_on_success=settings.promote_on_success,
    )


def _prepare_run_root(context: RunContext) -> None:
    """Create the run root and supporting metadata directories when needed."""
    enforce_generated_output_path(context.run_root, label="run_root")
    context.run_root.mkdir(parents=True, exist_ok=True)
    (context.run_root / "logs").mkdir(parents=True, exist_ok=True)


def _write_run_metadata(
    settings: PreprocessingRunnerSettings,
    *,
    context: RunContext,
) -> None:
    """Write deterministic run metadata into the run root."""
    write_json(
        context.run_root / "run.json",
        {
            "run_id": context.run_id,
            "run_root": context.run_root.as_posix(),
            "promoted_root": context.promoted_root.as_posix(),
            "runs_root": context.runs_root.as_posix(),
            "uses_run_root": context.uses_run_root,
            "promote_on_success": context.promote_on_success,
            "source_mode": settings.source_mode,
            "stage": settings.preprocessing.stage,
            "generated_at": _utc_now_iso(),
            "runner_settings": {
                "source_mode": settings.source_mode,
                "data_root": settings.data_root.as_posix(),
                "selected_source_records_path": (
                    None
                    if settings.selected_source_records_path is None
                    else settings.selected_source_records_path.as_posix()
                ),
                "fleurs_splits": list(settings.fleurs_splits),
                "fleurs_max_rows_per_split": settings.fleurs_max_rows_per_split,
                "rixvox_splits": list(settings.rixvox_splits),
                "rixvox_max_rows_per_split": settings.rixvox_max_rows_per_split,
                "preprocessing": asdict(
                    PreprocessingSettings(
                        output_root=context.run_root,
                        asr_model=settings.preprocessing.asr_model,
                        asr_revision=settings.preprocessing.asr_revision,
                        tokenizer_model=settings.preprocessing.tokenizer_model,
                        stage=settings.preprocessing.stage,
                        finalization_families=settings.preprocessing.finalization_families,
                        audio_codes_chunk_size=settings.preprocessing.audio_codes_chunk_size,
                        audio_codes_runtime=settings.preprocessing.audio_codes_runtime,
                        row_worker_count=settings.preprocessing.row_worker_count,
                        gpu_asr_worker_count=settings.preprocessing.gpu_asr_worker_count,
                        resume_row_processing=settings.preprocessing.resume_row_processing,
                    )
                ),
            },
        },
    )


def _write_status(
    context: RunContext,
    *,
    source_mode: SourceMode,
    stage: str,
    status: RunStatus,
    error: str | None = None,
    heartbeat_payload: dict[str, object] | None = None,
) -> None:
    """Write one deterministic status payload into the run root."""
    status_path = context.run_root / "status.json"
    existing_payload: dict[str, object] = {}
    if status_path.exists():
        loaded = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing_payload = loaded
    payload: dict[str, object] = {
        "run_id": context.run_id,
        "run_root": context.run_root.as_posix(),
        "promoted_root": context.promoted_root.as_posix(),
        "status": status,
        "stage": stage,
        "source_mode": source_mode,
        "updated_at": _utc_now_iso(),
        "error": error,
    }
    for key, value in existing_payload.items():
        if key not in payload:
            payload[key] = value
    if heartbeat_payload is not None:
        payload.update(heartbeat_payload)
    write_json(status_path, payload)


@dataclass(frozen=True)
class RunStatusReporter:
    """Persist stable run-status transitions and heartbeats for one run."""

    context: RunContext
    source_mode: SourceMode
    stage: str

    def write_allocated(self) -> None:
        """Persist the initial allocated status."""
        _write_status(
            self.context, source_mode=self.source_mode, stage=self.stage, status="allocated"
        )

    def write_stage_running(self) -> None:
        """Persist the generic running status for the current stage."""
        _write_status(
            self.context, source_mode=self.source_mode, stage=self.stage, status="running"
        )

    def write_source_selection_running(
        self,
        *,
        selected_row_count: int,
        target_row_cap: int | None,
    ) -> None:
        """Persist source-selection status once selection is resolved."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage="source-selection",
            status="running",
            heartbeat_payload={
                "selected_row_count": selected_row_count,
                "target_row_cap": target_row_cap,
            },
        )

    def write_failed(self, error: str) -> None:
        """Persist a failed status with traceback text."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="failed",
            error=error,
        )

    def write_finished(self, *, promoted: bool) -> None:
        """Persist the terminal completed or promoted status."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="promoted" if promoted else "completed",
        )

    def source_selection_heartbeat(self, heartbeat: SourceSelectionHeartbeat) -> None:
        """Persist one source-selection heartbeat."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage="source-selection",
            status="running",
            heartbeat_payload={
                "current_split": heartbeat.current_split,
                "selected_row_count": heartbeat.selected_row_count,
                "target_row_cap": heartbeat.target_row_cap,
                "current_parquet_batch_index": heartbeat.current_parquet_batch_index,
                "resolved_audio_locator_count": heartbeat.resolved_audio_locator_count,
                "required_audio_locator_count": heartbeat.required_audio_locator_count,
            },
        )

    def row_processing_heartbeat(self, heartbeat: RowProcessingHeartbeat) -> None:
        """Persist one row-processing heartbeat."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="running",
            heartbeat_payload={
                "processed_row_count": heartbeat.processed_row_count,
                "total_row_count": heartbeat.total_row_count,
                "current_dataset_row_id": heartbeat.current_dataset_row_id,
            },
        )

    def finalization_heartbeat(self, heartbeat: FinalizationHeartbeat) -> None:
        """Persist one finalization heartbeat."""
        _write_status(
            self.context,
            source_mode=self.source_mode,
            stage=self.stage,
            status="running",
            heartbeat_payload={
                "current_family": heartbeat.current_family,
                "completed_families": list(heartbeat.completed_families),
                "current_chunk_index": heartbeat.current_chunk_index,
                "completed_chunk_count": heartbeat.completed_chunk_count,
                "total_chunk_count": heartbeat.total_chunk_count,
            },
        )


def _effective_preprocessing_settings(
    settings: PreprocessingRunnerSettings,
    *,
    output_root: Path,
) -> PreprocessingSettings:
    """Build the effective preprocessing settings for one resolved run root."""
    return PreprocessingSettings(
        output_root=output_root,
        asr_model=settings.preprocessing.asr_model,
        asr_revision=settings.preprocessing.asr_revision,
        tokenizer_model=settings.preprocessing.tokenizer_model,
        stage=settings.preprocessing.stage,
        finalization_families=settings.preprocessing.finalization_families,
        audio_codes_chunk_size=settings.preprocessing.audio_codes_chunk_size,
        audio_codes_runtime=settings.preprocessing.audio_codes_runtime,
        row_worker_count=settings.preprocessing.row_worker_count,
        gpu_asr_worker_count=settings.preprocessing.gpu_asr_worker_count,
        resume_row_processing=settings.preprocessing.resume_row_processing,
    )


def _resolve_source_records(
    settings: PreprocessingRunnerSettings,
    *,
    output_root: Path,
    source_selection_heartbeat_callback=None,
) -> Sequence[SourceRecord] | None:
    """Resolve source records for the requested public runner mode."""
    if settings.source_mode == "repo-fixture":
        return None
    if settings.source_mode == "selected-source-records":
        selected_source_records_path = settings.selected_source_records_path
        if selected_source_records_path is None:
            raise SystemExit(
                "`--selected-source-records-path` is required for "
                "`--source-mode selected-source-records`."
            )
        persisted_source_records = load_source_records_from_jsonl_path(selected_source_records_path)
        return resolve_selected_source_records_for_local_data(
            data_root=settings.data_root,
            source_records=persisted_source_records,
            source_selection_heartbeat_callback=source_selection_heartbeat_callback,
        )
    if settings.preprocessing.stage == "row-processing":
        selected_source_records = load_selected_source_records(output_root)
        if selected_source_records is not None:
            return selected_source_records
    ensure_bulk_data_storage_path(settings.data_root, label="data_root")
    source_records = list(
        staged_public_corpus_source_records(
            settings.data_root,
            fleurs_splits=settings.fleurs_splits,
            fleurs_max_rows_per_split=settings.fleurs_max_rows_per_split,
            rixvox_splits=settings.rixvox_splits,
            rixvox_max_rows_per_split=settings.rixvox_max_rows_per_split,
            source_selection_heartbeat_callback=source_selection_heartbeat_callback,
        )
    )
    write_selected_source_records(
        output_root,
        source_records=source_records,
        summary=SourceSelectionSummary(
            source_mode=settings.source_mode,
            total_selected_rows=len(source_records),
            datasets=sorted({row.dataset for row in source_records}),
            fleurs_splits=list(settings.fleurs_splits),
            rixvox_splits=list(settings.rixvox_splits),
            rixvox_max_rows_per_split=settings.rixvox_max_rows_per_split,
        ),
    )
    return source_records


def _source_selection_report(
    *,
    output_root: Path,
    settings: PreprocessingRunnerSettings,
    source_records: Sequence[SourceRecord] | None,
) -> PreprocessingReport:
    """Build one synthetic report for the source-selection-only stage."""
    effective_source_records = list(source_records or [])
    return PreprocessingReport(
        output_root=output_root.as_posix(),
        datasets=sorted({row.dataset for row in effective_source_records}),
        asr_model=settings.preprocessing.asr_model,
        asr_revision=settings.preprocessing.asr_revision,
        tokenizer_model=settings.preprocessing.tokenizer_model,
        inventory_rows=len(effective_source_records),
        curated_rows=0,
        admitted_rows=0,
        prepared_rows=0,
        speaker_ids=sorted({row.speaker_id for row in effective_source_records}),
        manifest_counts={family: 0 for family in CANONICAL_MANIFEST_FAMILIES},
    )


def _promote_run_root(context: RunContext) -> None:
    """Promote one successful run root into the canonical shared corpus path."""
    if not context.uses_run_root:
        return
    promoted_root = context.promoted_root
    enforce_generated_output_path(promoted_root, label="promoted_root")
    promoted_root.parent.mkdir(parents=True, exist_ok=True)
    if promoted_root.is_symlink() or promoted_root.is_file():
        promoted_root.unlink()
    elif promoted_root.exists():
        shutil.rmtree(promoted_root)
    promoted_root.symlink_to(context.run_root, target_is_directory=True)


def _render_stdout_summary(report: PreprocessingReport) -> str:
    """Render one stable stdout summary for the completed preprocessing run."""
    return json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    """Run the canonical preprocessing bundle and print one JSON summary."""
    settings = _parse_args(argv)
    enforce_generated_output_path(settings.preprocessing.output_root, label="output_root")
    context = _resolve_run_context(settings)
    _prepare_run_root(context)
    _write_run_metadata(settings, context=context)
    effective_settings = _effective_preprocessing_settings(settings, output_root=context.run_root)
    status_reporter = RunStatusReporter(
        context=context,
        source_mode=settings.source_mode,
        stage=effective_settings.stage,
    )
    status_reporter.write_allocated()

    try:
        source_records = _resolve_source_records(
            settings,
            output_root=context.run_root,
            source_selection_heartbeat_callback=status_reporter.source_selection_heartbeat,
        )
        if settings.preprocessing.stage == "source-selection":
            status_reporter.write_source_selection_running(
                selected_row_count=0 if source_records is None else len(source_records),
                target_row_cap=settings.rixvox_max_rows_per_split,
            )
            report = _source_selection_report(
                output_root=context.run_root,
                settings=settings,
                source_records=source_records,
            )
        else:
            status_reporter.write_stage_running()
            report = run_preprocessing_pipeline(
                effective_settings,
                source_records=source_records,
                row_heartbeat_callback=status_reporter.row_processing_heartbeat,
                finalization_heartbeat_callback=status_reporter.finalization_heartbeat,
            )
    except Exception:
        status_reporter.write_failed(traceback.format_exc().strip())
        raise

    promoted = context.promote_on_success and effective_settings.stage == "reports"
    if promoted:
        _promote_run_root(context)
    status_reporter.write_finished(promoted=promoted)
    print(_render_stdout_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
