"""Finalization and report helpers for the staged Qwen preprocessing pipeline.

Purpose:
    Consume durable spool rows to emit curated manifests, raw/prepared Qwen
    manifests, chunked `audio_codes`, and deterministic report artifacts
    without depending on one whole-run in-memory accumulator.

Relationships:
    - Called by the Task 103 core facade during the `all` and `finalization`
      stages.
    - Reads durable spool output produced by the row-processing stage.
    - Owns the bounded-chunk finalization behavior introduced by `T110`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Protocol

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CANONICAL_MANIFEST_FAMILIES,
    CuratedRow,
    ManifestFamily,
    PreparedManifestRow,
    RawManifestRow,
    SpoolRow,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    JsonlAtomicWriter,
    iter_jsonl_objects,
    iter_spool_rows,
    write_json,
)


class AudioCodesEncoderProtocol(Protocol):
    """Minimal callable surface for chunked `audio_codes` generation."""

    def __call__(
        self,
        *,
        tokenizer_model: str,
        audio_paths: list[Path],
    ) -> list[list[list[int]]]:
        """Encode one bounded chunk of audio paths into Qwen audio codes."""


def encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Generate Qwen `audio_codes` for one bounded audio-path chunk."""
    from qwen_tts import Qwen3TTSTokenizer

    tokenizer = Qwen3TTSTokenizer.from_pretrained(tokenizer_model)
    rendered_codes: list[list[list[int]]] = []
    encoded = tokenizer.encode([path.as_posix() for path in audio_paths], sr=24_000)
    for audio_codes in encoded.audio_codes:
        rendered_codes.append([[int(value) for value in row] for row in audio_codes.tolist()])
    return rendered_codes


def _curated_row_from_spool(spool_row: SpoolRow, manifest_target: ManifestFamily) -> CuratedRow:
    """Project one spool row into one family-specific curated row."""
    return CuratedRow(
        dataset=spool_row.dataset,
        source_split=spool_row.source_split,
        dataset_row_id=spool_row.dataset_row_id,
        speaker_id=spool_row.speaker_id,
        speaker_name=spool_row.speaker_name,
        speaker_from_id=spool_row.speaker_from_id,
        source_audio_path=spool_row.source_audio_path,
        audio_24k_path=spool_row.audio_24k_path,
        duration_seconds=spool_row.duration_seconds,
        text_normalized=spool_row.text_normalized,
        reference_audio_24k_path=spool_row.reference_audio_24k_paths[manifest_target],
        asr_model=spool_row.asr_model,
        asr_revision=spool_row.asr_revision,
        asr_transcript=spool_row.asr_transcript,
        asr_wer=spool_row.asr_wer,
        quality_tier=spool_row.quality_tier,
        speaker_quality_gate=spool_row.speaker_quality_gate,
        dedup_applied=spool_row.dedup_applied,
        admission_decision=spool_row.admission_decision,
        manifest_target=manifest_target,
    )


def _raw_manifest_row_from_curated(curated_row: CuratedRow) -> RawManifestRow:
    """Project one curated row into one raw Qwen manifest row."""
    return RawManifestRow(
        audio=curated_row.audio_24k_path,
        text=curated_row.text_normalized,
        ref_audio=curated_row.reference_audio_24k_path,
        speaker_id=curated_row.speaker_id,
        dataset=curated_row.dataset,
        source_split=curated_row.source_split,
        quality_tier=curated_row.quality_tier,
    )


def _flush_audio_codes_chunk(
    *,
    output_root: Path,
    raw_writer: JsonlAtomicWriter,
    prepared_writer: JsonlAtomicWriter,
    raw_rows: list[RawManifestRow],
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    tokenizer_model: str,
) -> int:
    """Encode one bounded raw-row chunk and write raw/prepared manifest rows."""
    if not raw_rows:
        return 0
    audio_codes_list = encode_audio_codes_fn(
        tokenizer_model=tokenizer_model,
        audio_paths=[output_root / raw_row["audio"] for raw_row in raw_rows],
    )
    prepared_count = 0
    for raw_row, audio_codes in zip(raw_rows, audio_codes_list, strict=True):
        raw_writer.write_row(raw_row)
        prepared_writer.write_row(
            PreparedManifestRow(
                audio=raw_row["audio"],
                text=raw_row["text"],
                ref_audio=raw_row["ref_audio"],
                speaker_id=raw_row["speaker_id"],
                dataset=raw_row["dataset"],
                source_split=raw_row["source_split"],
                quality_tier=raw_row["quality_tier"],
                audio_codes=audio_codes,
            )
        )
        prepared_count += 1
    raw_rows.clear()
    return prepared_count


def finalize_from_spool(
    settings: Task103PreprocessingSettings,
    *,
    output_root: Path,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
) -> None:
    """Project durable spool rows into curated/raw/prepared manifest artifacts."""
    if settings.audio_codes_chunk_size <= 0:
        raise ValueError("`audio_codes_chunk_size` must be positive.")
    selected_families = set(settings.finalization_families)
    curated_dir = output_root / "curated"
    manifests_dir = output_root / "manifests"
    for family in CANONICAL_MANIFEST_FAMILIES:
        if family not in selected_families:
            continue
        raw_chunk: list[RawManifestRow] = []
        with (
            JsonlAtomicWriter(curated_dir / f"{family}.jsonl") as curated_writer,
            JsonlAtomicWriter(manifests_dir / f"{family}.raw.jsonl") as raw_writer,
            JsonlAtomicWriter(manifests_dir / f"{family}.prepared.jsonl") as prepared_writer,
        ):
            for spool_row in iter_spool_rows(output_root):
                if family not in spool_row.manifest_targets:
                    continue
                curated_row = _curated_row_from_spool(spool_row, family)
                curated_writer.write_row(curated_row)
                if curated_row.admission_decision == "admit":
                    raw_chunk.append(_raw_manifest_row_from_curated(curated_row))
                    if len(raw_chunk) >= settings.audio_codes_chunk_size:
                        _flush_audio_codes_chunk(
                            output_root=output_root,
                            raw_writer=raw_writer,
                            prepared_writer=prepared_writer,
                            raw_rows=raw_chunk,
                            encode_audio_codes_fn=encode_audio_codes_fn,
                            tokenizer_model=settings.tokenizer_model,
                        )
            _flush_audio_codes_chunk(
                output_root=output_root,
                raw_writer=raw_writer,
                prepared_writer=prepared_writer,
                raw_rows=raw_chunk,
                encode_audio_codes_fn=encode_audio_codes_fn,
                tokenizer_model=settings.tokenizer_model,
            )


def _count_jsonl_rows(path: Path) -> int:
    """Count one JSONL artifact deterministically."""
    return sum(1 for _ in iter_jsonl_objects(path))


def _report_markdown(report: Task103PreprocessingReport) -> str:
    """Render one concise markdown summary for the completed preprocessing pass."""
    manifest_lines = "\n".join(
        f"- `{family}`: `{count}`" for family, count in sorted(report.manifest_counts.items())
    )
    dataset_lines = "\n".join(f"- `{dataset}`" for dataset in report.datasets)
    speaker_lines = "\n".join(f"- `{speaker_id}`" for speaker_id in report.speaker_ids)
    return (
        "# Task 103 Qwen Swedish Preprocessing Report\n\n"
        f"- output_root: `{report.output_root}`\n"
        f"- asr_model: `{report.asr_model}`\n"
        f"- asr_revision: `{report.asr_revision}`\n"
        f"- tokenizer_model: `{report.tokenizer_model}`\n"
        f"- inventory_rows: `{report.inventory_rows}`\n"
        f"- curated_rows: `{report.curated_rows}`\n"
        f"- admitted_rows: `{report.admitted_rows}`\n"
        f"- prepared_rows: `{report.prepared_rows}`\n\n"
        "## Datasets\n\n"
        f"{dataset_lines}\n\n"
        "## Speakers\n\n"
        f"{speaker_lines}\n\n"
        "## Manifest Counts\n\n"
        f"{manifest_lines}\n"
    )


def build_reports(
    settings: Task103PreprocessingSettings,
    *,
    output_root: Path,
) -> Task103PreprocessingReport:
    """Rebuild report artifacts from deterministic on-disk pipeline outputs."""
    inventory_dir = output_root / "inventory"
    curated_dir = output_root / "curated"
    manifests_dir = output_root / "manifests"
    reports_dir = output_root / "reports"

    inventory_dataset_split_counts: Counter[str] = Counter()
    datasets: set[str] = set()
    speaker_ids: set[str] = set()
    for inventory_path in sorted(inventory_dir.glob("*.jsonl")):
        for row in iter_jsonl_objects(inventory_path):
            dataset = _required_str(row, "dataset", inventory_path)
            source_split = _required_str(row, "source_split", inventory_path)
            speaker_id = _required_str(row, "speaker_id", inventory_path)
            inventory_dataset_split_counts[f"{dataset}-{source_split}"] += 1
            datasets.add(dataset)
            speaker_ids.add(speaker_id)

    curated_dataset_split_counts: Counter[str] = Counter()
    quality_tier_counts: Counter[str] = Counter()
    reference_paths: dict[str, str] = {}
    curated_rows = 0
    for curated_path in sorted(curated_dir.glob("*.jsonl")):
        for row in iter_jsonl_objects(curated_path):
            curated_rows += 1
            dataset = _required_str(row, "dataset", curated_path)
            source_split = _required_str(row, "source_split", curated_path)
            quality_tier = _required_str(row, "quality_tier", curated_path)
            manifest_target = _required_str(row, "manifest_target", curated_path)
            speaker_id = _required_str(row, "speaker_id", curated_path)
            reference_audio_24k_path = _required_str(row, "reference_audio_24k_path", curated_path)
            curated_dataset_split_counts[f"{dataset}-{source_split}"] += 1
            quality_tier_counts[quality_tier] += 1
            reference_paths[f"{manifest_target}:{speaker_id}"] = reference_audio_24k_path

    manifest_counts: dict[ManifestFamily, int] = {}
    admitted_rows = 0
    prepared_rows = 0
    admitted_speaker_ids: set[str] = set()
    for family in CANONICAL_MANIFEST_FAMILIES:
        raw_path = manifests_dir / f"{family}.raw.jsonl"
        prepared_path = manifests_dir / f"{family}.prepared.jsonl"
        raw_count = _count_jsonl_rows(raw_path)
        prepared_count = _count_jsonl_rows(prepared_path)
        manifest_counts[family] = prepared_count
        admitted_rows += raw_count
        prepared_rows += prepared_count
        for row in iter_jsonl_objects(raw_path):
            admitted_speaker_ids.add(_required_str(row, "speaker_id", raw_path))

    write_json(
        reports_dir / "inventory_summary.json",
        {
            "dataset_split_counts": dict(sorted(inventory_dataset_split_counts.items())),
            "speaker_ids": sorted(speaker_ids),
        },
    )
    write_json(
        reports_dir / "filter_summary.json",
        {
            "curated_rows": curated_rows,
            "admitted_rows": admitted_rows,
            "quality_tier_counts": {
                "high_trust": quality_tier_counts.get("high_trust", 0),
                "medium_trust": quality_tier_counts.get("medium_trust", 0),
                "rejected": quality_tier_counts.get("rejected", 0),
            },
            "dataset_split_counts": dict(sorted(curated_dataset_split_counts.items())),
        },
    )
    write_json(
        reports_dir / "reference_selection_summary.json",
        {"speaker_reference_paths": dict(sorted(reference_paths.items()))},
    )
    write_json(
        reports_dir / "manifest_summary.json",
        {
            "manifest_counts": manifest_counts,
            "admitted_speaker_ids": sorted(admitted_speaker_ids),
        },
    )

    report = Task103PreprocessingReport(
        output_root=output_root.as_posix(),
        datasets=sorted(datasets),
        asr_model=settings.asr_model,
        asr_revision=settings.asr_revision,
        tokenizer_model=settings.tokenizer_model,
        inventory_rows=sum(inventory_dataset_split_counts.values()),
        curated_rows=curated_rows,
        admitted_rows=admitted_rows,
        prepared_rows=prepared_rows,
        speaker_ids=sorted(speaker_ids),
        manifest_counts=manifest_counts,
    )
    write_json(output_root / "report.json", report)
    (output_root / "report.md").write_text(_report_markdown(report) + "\n", encoding="utf-8")
    return report


def _required_str(payload: dict[str, object], key: str, path: Path) -> str:
    """Return one required string field from one JSONL report source."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in {path}.")
    return value
