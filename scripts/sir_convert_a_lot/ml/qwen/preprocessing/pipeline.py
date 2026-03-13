"""Core facade for the Qwen Swedish preprocessing pipeline.

Purpose:
    Provide the stable internal entrypoint for the Swedish Qwen preprocessing
    pipeline, delegating to modular stage-oriented helpers.

Relationships:
    - Delegates row-processing, durable spool persistence, bounded
      finalization, and report generation to dedicated stage modules.
    - Reuses data contracts from `ml.qwen.common.models` and
      `ml.qwen.preprocessing.models`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    ManifestFamily,
    SourceRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.asr import (
    WhisperStrictScorer,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    build_reports,
    finalize_from_spool,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    encode_audio_codes as _encode_audio_codes,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    FinalizationHeartbeatCallback,
    PreprocessingReport,
    PreprocessingSettings,
    RowHeartbeatCallback,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.row_processing import (
    process_rows_to_spool,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sources.fixtures import (
    repo_fixture_source_records,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    prepare_output_root,
)

__all__ = [
    "CANONICAL_MANIFEST_FAMILIES",
    "ManifestFamily",
    "PreprocessingReport",
    "PreprocessingSettings",
    "WhisperStrictScorer",
    "run_preprocessing_pipeline",
]


def _resolve_source_records(source_records: Sequence[SourceRecord] | None) -> list[SourceRecord]:
    """Resolve the effective source-record set for one preprocessing run."""
    return list(source_records or repo_fixture_source_records(Path.cwd()))


def run_preprocessing_pipeline(
    settings: PreprocessingSettings,
    *,
    source_records: Sequence[SourceRecord] | None = None,
    row_heartbeat_callback: RowHeartbeatCallback | None = None,
    finalization_heartbeat_callback: FinalizationHeartbeatCallback | None = None,
) -> PreprocessingReport:
    """Run one deterministic Swedish Qwen preprocessing pass."""
    output_root = settings.output_root.resolve()

    if settings.stage == "all":
        prepare_output_root(output_root, stage="all")
        effective_source_records = _resolve_source_records(source_records)
        process_rows_to_spool(
            settings,
            output_root=output_root,
            source_records=effective_source_records,
            scorer_factory=WhisperStrictScorer,
            row_heartbeat_callback=row_heartbeat_callback,
        )
        # Note: We currently use the default CPU encoder as fallback.
        # Specialized in-container orchestration can override this.
        finalize_from_spool(
            settings,
            output_root=output_root,
            encode_audio_codes_fn=_encode_audio_codes,
            finalization_heartbeat_callback=finalization_heartbeat_callback,
        )
        return build_reports(settings, output_root=output_root)

    if settings.stage == "row-processing":
        prepare_output_root(
            output_root,
            stage="row-processing",
            resume_row_processing=settings.resume_row_processing,
        )
        effective_source_records = _resolve_source_records(source_records)
        process_rows_to_spool(
            settings,
            output_root=output_root,
            source_records=effective_source_records,
            scorer_factory=WhisperStrictScorer,
            row_heartbeat_callback=row_heartbeat_callback,
        )
        return build_reports(settings, output_root=output_root)

    if settings.stage == "finalization":
        prepare_output_root(output_root, stage="finalization")
        finalize_from_spool(
            settings,
            output_root=output_root,
            encode_audio_codes_fn=_encode_audio_codes,
            finalization_heartbeat_callback=finalization_heartbeat_callback,
        )
        return build_reports(settings, output_root=output_root)

    if settings.stage == "reports":
        prepare_output_root(output_root, stage="reports")
        return build_reports(settings, output_root=output_root)

    raise ValueError(f"Unsupported preprocessing stage: {settings.stage}")
