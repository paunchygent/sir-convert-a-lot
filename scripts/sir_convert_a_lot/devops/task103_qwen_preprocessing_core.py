"""Core facade for the Task 103/T110 Qwen Swedish preprocessing pipeline.

Purpose:
    Preserve the stable public import surface for Task 103 while delegating the
    actual preprocessing work to modular stage-oriented helpers.

Relationships:
    - Used by `run_task103_qwen_swedish_preprocessing.py` as the committed
      runner surface for Task 103 and later hardening tasks.
    - Re-exports the core contracts consumed by tests and the containerized
      Task 109 runtime.
    - Delegates row-processing, durable spool persistence, bounded
      finalization, and report generation to dedicated stage modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_asr import (
    ProcessorOutputProtocol,
    TorchTensorProtocol,
    WhisperStrictScorer,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    build_reports,
    finalize_from_spool,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    encode_audio_codes as _encode_audio_codes,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CANONICAL_MANIFEST_FAMILIES,
    ManifestFamily,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_row_stage import (
    process_rows_to_spool,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    prepare_output_root,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_source_repo_fixture import (
    repo_fixture_source_records,
)

__all__ = [
    "CANONICAL_MANIFEST_FAMILIES",
    "ManifestFamily",
    "ProcessorOutputProtocol",
    "Task103PreprocessingReport",
    "Task103PreprocessingSettings",
    "TorchTensorProtocol",
    "WhisperStrictScorer",
    "run_task103_preprocessing",
]


def _resolve_source_records(source_records: Sequence[SourceRecord] | None) -> list[SourceRecord]:
    """Resolve the effective source-record set for one preprocessing run."""
    return list(source_records or repo_fixture_source_records(Path.cwd()))


def run_task103_preprocessing(
    settings: Task103PreprocessingSettings,
    *,
    source_records: Sequence[SourceRecord] | None = None,
) -> Task103PreprocessingReport:
    """Run one deterministic Task 103/T110 preprocessing pass."""
    output_root = settings.output_root.resolve()

    if settings.stage == "all":
        prepare_output_root(output_root, stage="all")
        effective_source_records = _resolve_source_records(source_records)
        process_rows_to_spool(
            settings,
            output_root=output_root,
            source_records=effective_source_records,
            scorer_factory=WhisperStrictScorer,
        )
        finalize_from_spool(
            settings,
            output_root=output_root,
            encode_audio_codes_fn=_encode_audio_codes,
        )
        return build_reports(settings, output_root=output_root)

    if settings.stage == "row-processing":
        prepare_output_root(output_root, stage="row-processing")
        effective_source_records = _resolve_source_records(source_records)
        process_rows_to_spool(
            settings,
            output_root=output_root,
            source_records=effective_source_records,
            scorer_factory=WhisperStrictScorer,
        )
        return build_reports(settings, output_root=output_root)

    if settings.stage == "finalization":
        prepare_output_root(output_root, stage="finalization")
        finalize_from_spool(
            settings,
            output_root=output_root,
            encode_audio_codes_fn=_encode_audio_codes,
        )
        return build_reports(settings, output_root=output_root)

    raise ValueError(f"Unsupported Task 103 stage: {settings.stage}")
