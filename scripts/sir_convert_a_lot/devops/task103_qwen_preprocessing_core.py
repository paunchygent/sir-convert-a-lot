"""Core preprocessing helpers for the Task 103 Qwen Swedish corpus pipeline.

Purpose:
    Materialize deterministic inventory, curated, raw-manifest, and
    prepared-manifest layers for Swedish Qwen preprocessing from adapter-shaped
    source records instead of fixture-only local assumptions.

Relationships:
    - Used by `run_task103_qwen_swedish_preprocessing.py` as the committed
      runner surface for Task 103 and Task 106 preprocessing work.
    - Consumes source adapters from `task103_qwen_source_*.py`.
    - Emits artifacts under `build/reference/qwen3-tts-swedish-corpus/` in the
      shape defined by `ref-qwen3-tts-swedish-preprocessing-and-manifest-spec`.
    - Produces JSONL rows consumed directly by the patched
      `scripts/devops/qwen_finetuning_patches/dataset.py` and
      `scripts/devops/qwen_finetuning_patches/sft_12hz.py`.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import unicodedata
import wave
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Literal, Protocol, Sequence, TypedDict

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    ManifestFamily,
    manifest_target_for_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import AudioLocator, SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_source_repo_fixture import (
    repo_fixture_source_records,
)

CANONICAL_SAMPLE_RATE_HZ = 24_000
HIGH_TRUST_WER_MAX = 0.15
MEDIUM_TRUST_WER_MAX = 0.20
CANONICAL_MANIFEST_FAMILIES: tuple[ManifestFamily, ...] = (
    "swedish_smoke_train",
    "swedish_pilot_train",
    "swedish_scaleup_train",
    "swedish_checkpoint_dev",
    "swedish_final_test",
    "swedish_waxholm_control",
)

QualityTier = Literal["high_trust", "medium_trust", "rejected"]
SpeakerQualityGate = Literal["speaker_from_id", "manual_review", "rejected_multi_speaker"]
AdmissionDecision = Literal["admit", "reject"]


class TorchTensorProtocol(Protocol):
    """Minimal tensor surface needed by the local ASR helper."""

    def to(self, *args: object, **kwargs: object) -> "TorchTensorProtocol":
        """Move one tensor to the requested device and dtype."""


class ProcessorOutputProtocol(Protocol):
    """Minimal processor output surface used by the local ASR helper."""

    input_features: TorchTensorProtocol
    attention_mask: TorchTensorProtocol | None


class WhisperProcessorProtocol(Protocol):
    """Minimal processor surface used by the local ASR helper."""

    feature_extractor: "WhisperFeatureExtractorProtocol"

    def __call__(
        self,
        waveform: object,
        *,
        sampling_rate: int,
        return_tensors: str,
        return_attention_mask: bool,
    ) -> ProcessorOutputProtocol:
        """Encode one waveform into input features."""

    def batch_decode(self, sequences: object, *, skip_special_tokens: bool) -> list[str]:
        """Decode generated token ids into text."""


class WhisperFeatureExtractorProtocol(Protocol):
    """Minimal feature extractor metadata used by the local ASR helper."""

    sampling_rate: int


class TorchDeviceProtocol(Protocol):
    """Minimal device surface used by the local ASR helper."""

    type: str


class WhisperModelProtocol(Protocol):
    """Minimal seq2seq model surface used by the local ASR helper."""

    def to(self, device: TorchDeviceProtocol) -> "WhisperModelProtocol":
        """Move the model to one target device."""

    def eval(self) -> None:
        """Set the model to evaluation mode."""

    def generate(
        self,
        input_features: TorchTensorProtocol,
        *,
        attention_mask: TorchTensorProtocol | None = None,
        max_new_tokens: int,
        task: str,
    ) -> object:
        """Generate one transcription token sequence."""


class RawManifestRow(TypedDict):
    """Raw Qwen manifest row emitted before `audio_codes` are generated."""

    audio: str
    text: str
    ref_audio: str
    speaker_id: str
    dataset: str
    source_split: str
    quality_tier: QualityTier


@dataclass(frozen=True)
class InventoryRow:
    """One deterministic inventory row before curation."""

    dataset: str
    source_split: str
    dataset_row_id: str
    source_audio_path: str
    source_sample_rate_hz: int
    duration_seconds: float
    text_raw: str
    text_normalized: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    speaker_total_hours: float
    language: str
    has_label_files: bool
    speaker_audio_meta_ok: bool
    boilerplate_group: str | None
    notes: str | None


@dataclass(frozen=True)
class CuratedRow:
    """One deterministic curated row after filtering and scoring."""

    dataset: str
    source_split: str
    dataset_row_id: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    source_audio_path: str
    audio_24k_path: str
    duration_seconds: float
    text_normalized: str
    reference_audio_24k_path: str
    asr_model: str
    asr_revision: str
    asr_transcript: str
    asr_wer: float
    quality_tier: QualityTier
    speaker_quality_gate: SpeakerQualityGate
    dedup_applied: bool
    admission_decision: AdmissionDecision
    manifest_target: ManifestFamily


@dataclass(frozen=True)
class PreparedManifestRow:
    """One Qwen-ready prepared manifest row with `audio_codes`."""

    audio: str
    text: str
    ref_audio: str
    speaker_id: str
    dataset: str
    source_split: str
    quality_tier: QualityTier
    audio_codes: list[list[int]]


@dataclass(frozen=True)
class Task103PreprocessingSettings:
    """Normalized Task 103 runtime settings."""

    output_root: Path
    asr_model: str
    asr_revision: str
    tokenizer_model: str


@dataclass(frozen=True)
class Task103PreprocessingReport:
    """Top-level report for one Task 103 preprocessing pass."""

    output_root: str
    datasets: list[str]
    asr_model: str
    asr_revision: str
    tokenizer_model: str
    inventory_rows: int
    curated_rows: int
    admitted_rows: int
    prepared_rows: int
    speaker_ids: list[str]
    manifest_counts: dict[ManifestFamily, int]


def json_default(value: object) -> object:
    """Serialize supported objects into stable JSON payloads."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


def write_json(path: Path, payload: object) -> None:
    """Write deterministic JSON output."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Sequence[object]) -> None:
    """Write deterministic JSONL output."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered_rows = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, default=json_default) for row in rows
    ]
    path.write_text("\n".join(rendered_rows) + ("\n" if rendered_rows else ""), encoding="utf-8")


def _sha256_hex(path: Path) -> str:
    """Hash one file with SHA256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare_output_root(output_root: Path) -> None:
    """Reset the deterministic generated subtree for the current run."""
    output_root.mkdir(parents=True, exist_ok=True)
    for subdir_name in ("inventory", "curated", "refs", "audio_24k", "manifests", "reports"):
        subdir = output_root / subdir_name
        if subdir.exists():
            shutil.rmtree(subdir)
    for generated_name in ("report.json", "report.md", "failure.txt"):
        generated_path = output_root / generated_name
        if generated_path.exists():
            generated_path.unlink()


def _normalize_text(text: str) -> str:
    """Normalize one Swedish transcript into the repo's canonical orthography form."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u00a0", " ").replace("’", "'").replace("`", "'")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized == "":
        raise ValueError("Transcript normalization produced an empty string.")
    if normalized[-1] not in ".!?":
        normalized = f"{normalized}."
    return normalized


def normalize_for_wer(text: str) -> str:
    """Normalize text into a WER-friendly token space."""
    lowered = _normalize_text(text).lower()
    without_punctuation = re.sub(r"[^\w\såäöÅÄÖ]", " ", lowered, flags=re.UNICODE)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def word_error_rate(reference_text: str, hypothesis_text: str) -> float:
    """Compute deterministic word error rate without external runtime dependencies."""
    reference_words = normalize_for_wer(reference_text).split()
    hypothesis_words = normalize_for_wer(hypothesis_text).split()
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0

    previous_row = list(range(len(hypothesis_words) + 1))
    for row_index, reference_word in enumerate(reference_words, start=1):
        current_row = [row_index]
        for column_index, hypothesis_word in enumerate(hypothesis_words, start=1):
            substitution_cost = 0 if reference_word == hypothesis_word else 1
            current_row.append(
                min(
                    previous_row[column_index] + 1,
                    current_row[column_index - 1] + 1,
                    previous_row[column_index - 1] + substitution_cost,
                )
            )
        previous_row = current_row
    return round(previous_row[-1] / len(reference_words), 6)


def quality_tier_for_wer(asr_wer: float) -> QualityTier:
    """Assign the fixed T102/T103 quality tier for one WER score."""
    if asr_wer <= HIGH_TRUST_WER_MAX:
        return "high_trust"
    if asr_wer <= MEDIUM_TRUST_WER_MAX:
        return "medium_trust"
    return "rejected"


def _speaker_quality_gate_for_source(source_record: SourceRecord) -> SpeakerQualityGate:
    """Assign one speaker-quality gate from the dataset-native source metadata."""
    if source_record.speaker_from_id and source_record.speaker_audio_meta_ok:
        return "speaker_from_id"
    return "manual_review"


def admission_decision_for_source(
    quality_tier: QualityTier,
    speaker_quality_gate: SpeakerQualityGate,
) -> AdmissionDecision:
    """Map quality and speaker gates to one bounded pilot admission decision."""
    if quality_tier == "high_trust" and speaker_quality_gate == "speaker_from_id":
        return "admit"
    return "reject"


def _wav_metadata(audio_path: Path) -> tuple[int, float]:
    """Read sample rate and duration for one WAV file."""
    with wave.open(audio_path.as_posix(), "rb") as handle:
        sample_rate_hz = handle.getframerate()
        duration_seconds = handle.getnframes() / sample_rate_hz
    return int(sample_rate_hz), round(duration_seconds, 6)


def _inventory_row_for_source(source_record: SourceRecord) -> InventoryRow:
    """Build one inventory row from one adapter-shaped source record."""
    if (
        source_record.source_sample_rate_hz is not None
        and source_record.duration_seconds is not None
    ):
        source_sample_rate_hz = source_record.source_sample_rate_hz
        duration_seconds = source_record.duration_seconds
    elif (
        source_record.source_audio_locator is not None
        and source_record.source_audio_locator.archive_member is None
    ):
        source_sample_rate_hz, duration_seconds = _wav_metadata(
            source_record.source_audio_locator.path
        )
    else:
        raise ValueError(
            "Source record must provide sample-rate and duration hints when audio "
            "metadata cannot be derived from a direct WAV path."
        )

    transcript_normalized = _normalize_text(source_record.text_raw)
    speaker_total_hours = source_record.speaker_total_hours
    if speaker_total_hours is None:
        speaker_total_hours = round(duration_seconds / 3600.0, 6)

    notes = source_record.notes
    if (
        source_record.source_audio_locator is not None
        and source_record.source_audio_locator.archive_member is None
    ):
        notes_prefix = f"sha256:{_sha256_hex(source_record.source_audio_locator.path)[:16]}"
        notes = notes_prefix if notes is None else f"{notes_prefix};{notes}"

    return InventoryRow(
        dataset=source_record.dataset,
        source_split=source_record.source_split,
        dataset_row_id=source_record.dataset_row_id,
        source_audio_path=source_record.source_audio_path,
        source_sample_rate_hz=source_sample_rate_hz,
        duration_seconds=round(duration_seconds, 6),
        text_raw=source_record.text_raw,
        text_normalized=transcript_normalized,
        speaker_id=source_record.speaker_id,
        speaker_name=source_record.speaker_name,
        speaker_from_id=source_record.speaker_from_id,
        speaker_total_hours=round(float(speaker_total_hours), 6),
        language=source_record.language,
        has_label_files=source_record.has_label_files,
        speaker_audio_meta_ok=source_record.speaker_audio_meta_ok,
        boilerplate_group=source_record.boilerplate_group,
        notes=notes,
    )


def _resample_and_write_audio(source_path: Path, target_path: Path) -> float:
    """Standardize one waveform to the fixed 24 kHz training-side contract."""
    import librosa
    import numpy as np
    import soundfile

    waveform, sample_rate_hz = soundfile.read(source_path.as_posix(), dtype="float32")
    if getattr(waveform, "ndim", 1) > 1:
        waveform = waveform.mean(axis=1)
    if sample_rate_hz != CANONICAL_SAMPLE_RATE_HZ:
        waveform = librosa.resample(
            np.asarray(waveform, dtype=np.float32),
            orig_sr=sample_rate_hz,
            target_sr=CANONICAL_SAMPLE_RATE_HZ,
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    soundfile.write(target_path.as_posix(), waveform, CANONICAL_SAMPLE_RATE_HZ)
    _, duration_seconds = _wav_metadata(target_path)
    return duration_seconds


def _materialize_audio_locator(audio_locator: AudioLocator, target_path: Path) -> float:
    """Materialize one source audio locator to the canonical 24 kHz target path."""
    if audio_locator.archive_member is None:
        return _resample_and_write_audio(audio_locator.path, target_path)

    with tarfile.open(audio_locator.path, "r:*") as archive:
        extracted = archive.extractfile(audio_locator.archive_member)
        if extracted is None:
            raise FileNotFoundError(
                f"Missing archive member {audio_locator.archive_member} in {audio_locator.path}"
            )
        suffix = Path(audio_locator.archive_member).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
            handle.write(extracted.read())
            handle.flush()
            return _resample_and_write_audio(Path(handle.name), target_path)


@dataclass
class WhisperStrictScorer:
    """Lazy Swedish ASR scorer backed by `KBLab/kb-whisper-large` strict."""

    model_id: str
    revision: str
    _model: WhisperModelProtocol | None = None
    _processor: WhisperProcessorProtocol | None = None
    _device: TorchDeviceProtocol | None = None
    _dtype: object | None = None

    def _ensure_loaded(self) -> None:
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

        if self._model is not None and self._processor is not None and self._device is not None:
            return

        if torch.cuda.is_available():
            device = torch.device("cuda")
            dtype = torch.float16
        elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            device = torch.device("mps")
            dtype = torch.float32
        else:
            device = torch.device("cpu")
            dtype = torch.float32

        processor = AutoProcessor.from_pretrained(self.model_id, revision=self.revision)
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.model_id,
            revision=self.revision,
            dtype=dtype,
            low_cpu_mem_usage=True,
        )
        model.to(device)
        model.eval()

        self._processor = processor
        self._model = model
        self._device = device
        self._dtype = dtype

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe one short audio clip with deterministic generation settings."""
        import librosa
        import numpy as np
        import soundfile
        import torch

        self._ensure_loaded()
        assert self._model is not None
        assert self._processor is not None
        assert self._device is not None
        assert self._dtype is not None

        waveform, sample_rate_hz = soundfile.read(audio_path.as_posix(), dtype="float32")
        if getattr(waveform, "ndim", 1) > 1:
            waveform = waveform.mean(axis=1)
        target_sample_rate_hz = int(self._processor.feature_extractor.sampling_rate)
        if sample_rate_hz != target_sample_rate_hz:
            waveform = librosa.resample(
                np.asarray(waveform, dtype=np.float32),
                orig_sr=sample_rate_hz,
                target_sr=target_sample_rate_hz,
            )
            sample_rate_hz = target_sample_rate_hz
        processed = self._processor(
            waveform,
            sampling_rate=sample_rate_hz,
            return_tensors="pt",
            return_attention_mask=True,
        )
        input_features = processed.input_features.to(self._device)
        attention_mask = processed.attention_mask
        if attention_mask is not None:
            attention_mask = attention_mask.to(self._device)
        if self._device.type == "cuda":
            input_features = input_features.to(dtype=self._dtype)
        with torch.inference_mode():
            predicted_ids = self._model.generate(
                input_features,
                attention_mask=attention_mask,
                max_new_tokens=256,
                task="transcribe",
            )
        decoded = self._processor.batch_decode(predicted_ids, skip_special_tokens=True)
        if not decoded:
            raise RuntimeError(f"ASR transcription returned no text for {audio_path}.")
        return decoded[0].strip()


def _encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Generate Qwen `audio_codes` for the admitted audio paths."""
    from qwen_tts import Qwen3TTSTokenizer

    tokenizer = Qwen3TTSTokenizer.from_pretrained(tokenizer_model)
    encoded = tokenizer.encode(
        [path.as_posix() for path in audio_paths],
        sr=CANONICAL_SAMPLE_RATE_HZ,
    )
    audio_codes_list = encoded.audio_codes
    rendered_codes: list[list[list[int]]] = []
    for audio_codes in audio_codes_list:
        rendered_codes.append([[int(value) for value in row] for row in audio_codes.tolist()])
    return rendered_codes


def _build_report_markdown(report: Task103PreprocessingReport) -> str:
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


def run_task103_preprocessing(
    settings: Task103PreprocessingSettings,
    *,
    source_records: Sequence[SourceRecord] | None = None,
) -> Task103PreprocessingReport:
    """Run one deterministic Task 103 preprocessing pass from source records."""
    output_root = settings.output_root.resolve()
    _prepare_output_root(output_root)

    inventory_dir = output_root / "inventory"
    curated_dir = output_root / "curated"
    refs_dir = output_root / "refs"
    audio_24k_dir = output_root / "audio_24k"
    manifests_dir = output_root / "manifests"
    reports_dir = output_root / "reports"

    effective_source_records = list(source_records or repo_fixture_source_records(Path.cwd()))
    inventory_rows = [
        _inventory_row_for_source(source_row) for source_row in effective_source_records
    ]

    inventory_rows_by_dataset_split: dict[str, list[InventoryRow]] = defaultdict(list)
    for inventory_row in inventory_rows:
        dataset_split_key = f"{inventory_row.dataset}-{inventory_row.source_split}"
        inventory_rows_by_dataset_split[dataset_split_key].append(inventory_row)
    for dataset_split_key, rows in inventory_rows_by_dataset_split.items():
        write_jsonl(inventory_dir / f"{dataset_split_key}.jsonl", [asdict(row) for row in rows])

    scorer = WhisperStrictScorer(model_id=settings.asr_model, revision=settings.asr_revision)
    curated_rows_by_family: dict[ManifestFamily, list[CuratedRow]] = {
        family: [] for family in CANONICAL_MANIFEST_FAMILIES
    }
    raw_manifest_rows_by_family: dict[ManifestFamily, list[RawManifestRow]] = {
        family: [] for family in CANONICAL_MANIFEST_FAMILIES
    }
    prepared_manifest_rows_by_family: dict[ManifestFamily, list[PreparedManifestRow]] = {
        family: [] for family in CANONICAL_MANIFEST_FAMILIES
    }

    canonical_reference_paths: dict[tuple[ManifestFamily, str], Path] = {}
    canonical_reference_locators: dict[tuple[ManifestFamily, str], AudioLocator] = {}
    all_curated_rows: list[CuratedRow] = []
    admitted_rows: list[CuratedRow] = []
    inventory_rows_by_key = {
        (row.dataset, row.source_split, row.dataset_row_id): row for row in inventory_rows
    }

    for source_row in effective_source_records:
        manifest_target = manifest_target_for_source(source_row)
        if manifest_target is None or source_row.source_audio_locator is None:
            continue

        inventory_row = inventory_rows_by_key[
            (source_row.dataset, source_row.source_split, source_row.dataset_row_id)
        ]
        utterance_slug = source_row.dataset_row_id.replace("_", "-")
        audio_24k_path = (
            audio_24k_dir
            / source_row.dataset
            / source_row.source_split
            / source_row.speaker_id
            / f"{utterance_slug}.wav"
        )

        reference_key = (manifest_target, source_row.speaker_id)
        reference_locator = canonical_reference_locators.setdefault(
            reference_key,
            source_row.reference_audio_locator or source_row.source_audio_locator,
        )
        reference_audio_24k_path = refs_dir / manifest_target / source_row.speaker_id / "ref.wav"
        canonical_reference_paths[reference_key] = reference_audio_24k_path
        if not reference_audio_24k_path.exists():
            _materialize_audio_locator(reference_locator, reference_audio_24k_path)

        duration_seconds = _materialize_audio_locator(
            source_row.source_audio_locator,
            audio_24k_path,
        )
        asr_transcript = scorer.transcribe(audio_24k_path)
        asr_wer = word_error_rate(inventory_row.text_normalized, asr_transcript)
        quality_tier = quality_tier_for_wer(asr_wer)
        speaker_quality_gate = _speaker_quality_gate_for_source(source_row)
        admission_decision = admission_decision_for_source(quality_tier, speaker_quality_gate)

        curated_row = CuratedRow(
            dataset=source_row.dataset,
            source_split=source_row.source_split,
            dataset_row_id=source_row.dataset_row_id,
            speaker_id=source_row.speaker_id,
            speaker_name=source_row.speaker_name,
            speaker_from_id=source_row.speaker_from_id,
            source_audio_path=source_row.source_audio_path,
            audio_24k_path=audio_24k_path.relative_to(output_root).as_posix(),
            duration_seconds=duration_seconds,
            text_normalized=inventory_row.text_normalized,
            reference_audio_24k_path=reference_audio_24k_path.relative_to(output_root).as_posix(),
            asr_model=settings.asr_model,
            asr_revision=settings.asr_revision,
            asr_transcript=asr_transcript,
            asr_wer=asr_wer,
            quality_tier=quality_tier,
            speaker_quality_gate=speaker_quality_gate,
            dedup_applied=False,
            admission_decision=admission_decision,
            manifest_target=manifest_target,
        )
        curated_rows_by_family[manifest_target].append(curated_row)
        all_curated_rows.append(curated_row)
        if curated_row.admission_decision == "admit":
            admitted_rows.append(curated_row)
            raw_manifest_rows_by_family[manifest_target].append(
                RawManifestRow(
                    audio=curated_row.audio_24k_path,
                    text=curated_row.text_normalized,
                    ref_audio=curated_row.reference_audio_24k_path,
                    speaker_id=curated_row.speaker_id,
                    dataset=curated_row.dataset,
                    source_split=curated_row.source_split,
                    quality_tier=curated_row.quality_tier,
                )
            )

    for family in CANONICAL_MANIFEST_FAMILIES:
        write_jsonl(
            curated_dir / f"{family}.jsonl",
            [asdict(row) for row in curated_rows_by_family[family]],
        )

        if raw_manifest_rows_by_family[family]:
            admitted_audio_paths = [
                output_root / row["audio"] for row in raw_manifest_rows_by_family[family]
            ]
            audio_codes_list = _encode_audio_codes(
                tokenizer_model=settings.tokenizer_model,
                audio_paths=admitted_audio_paths,
            )
            for raw_row, audio_codes in zip(
                raw_manifest_rows_by_family[family],
                audio_codes_list,
                strict=True,
            ):
                prepared_manifest_rows_by_family[family].append(
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

        write_jsonl(manifests_dir / f"{family}.raw.jsonl", raw_manifest_rows_by_family[family])
        write_jsonl(
            manifests_dir / f"{family}.prepared.jsonl",
            [asdict(row) for row in prepared_manifest_rows_by_family[family]],
        )

    manifest_counts = {
        family: len(prepared_manifest_rows_by_family[family])
        for family in CANONICAL_MANIFEST_FAMILIES
    }
    quality_tier_counts = Counter(row.quality_tier for row in all_curated_rows)
    curated_dataset_split_counts = Counter(
        f"{row.dataset}-{row.source_split}" for row in all_curated_rows
    )
    inventory_dataset_split_counts = Counter(
        f"{row.dataset}-{row.source_split}" for row in inventory_rows
    )

    write_json(
        reports_dir / "inventory_summary.json",
        {
            "dataset_split_counts": dict(sorted(inventory_dataset_split_counts.items())),
            "speaker_ids": sorted({row.speaker_id for row in inventory_rows}),
        },
    )
    write_json(
        reports_dir / "filter_summary.json",
        {
            "curated_rows": len(all_curated_rows),
            "admitted_rows": len(admitted_rows),
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
        {
            "speaker_reference_paths": {
                f"{family}:{speaker_id}": path.relative_to(output_root).as_posix()
                for (family, speaker_id), path in sorted(canonical_reference_paths.items())
            }
        },
    )
    write_json(
        reports_dir / "manifest_summary.json",
        {
            "manifest_counts": manifest_counts,
            "admitted_speaker_ids": sorted({row.speaker_id for row in admitted_rows}),
        },
    )

    report = Task103PreprocessingReport(
        output_root=output_root.as_posix(),
        datasets=sorted({row.dataset for row in effective_source_records}),
        asr_model=settings.asr_model,
        asr_revision=settings.asr_revision,
        tokenizer_model=settings.tokenizer_model,
        inventory_rows=len(inventory_rows),
        curated_rows=len(all_curated_rows),
        admitted_rows=len(admitted_rows),
        prepared_rows=sum(len(rows) for rows in prepared_manifest_rows_by_family.values()),
        speaker_ids=sorted({row.speaker_id for row in effective_source_records}),
        manifest_counts=manifest_counts,
    )
    write_json(output_root / "report.json", report)
    (output_root / "report.md").write_text(_build_report_markdown(report) + "\n", encoding="utf-8")
    return report
