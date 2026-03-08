"""Tests for the Task 103 Qwen Swedish preprocessing surface."""

from __future__ import annotations

import json
import math
import wave
from pathlib import Path

import numpy as np
import pytest

from scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing import (
    DEFAULT_ASR_MODEL,
    DEFAULT_ASR_REVISION,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_TOKENIZER_MODEL,
    _parse_args,
    main,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    CANONICAL_MANIFEST_FAMILIES,
    ProcessorOutputProtocol,
    SourceFixtureRow,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    TorchTensorProtocol,
    WhisperStrictScorer,
    run_task103_preprocessing,
)


def _write_test_wav(path: Path, *, sample_rate_hz: int, duration_seconds: float) -> None:
    """Write one deterministic mono WAV fixture for the Task 103 tests."""
    frame_count = int(sample_rate_hz * duration_seconds)
    amplitude = 12_000
    frequency_hz = 220.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(path.as_posix(), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        frames = bytearray()
        for frame_index in range(frame_count):
            sample = int(
                amplitude * math.sin((2.0 * math.pi * frequency_hz * frame_index) / sample_rate_hz)
            )
            frames.extend(sample.to_bytes(length=2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def test_task103_parse_args_defaults() -> None:
    """The Task 103 runner should expose deterministic defaults."""
    settings = _parse_args([])

    assert settings.output_root == DEFAULT_OUTPUT_ROOT
    assert settings.asr_model == DEFAULT_ASR_MODEL
    assert settings.asr_revision == DEFAULT_ASR_REVISION
    assert settings.tokenizer_model == DEFAULT_TOKENIZER_MODEL


def test_task103_preprocessing_emits_deterministic_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 103 core should emit inventory, curated, raw, and prepared layers."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    reference_audio_path = workspace_root / "fixtures/ref.wav"
    transcript_path = workspace_root / "fixtures/text.txt"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.25)
    _write_test_wav(reference_audio_path, sample_rate_hz=16_000, duration_seconds=6.0)
    transcript_path.write_text("Hej från Sverige.", encoding="utf-8")

    monkeypatch.chdir(workspace_root)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.repo_fixture_rows",
        lambda _: [
            SourceFixtureRow(
                dataset="repo_fixture_sv",
                source_split="fixture",
                dataset_row_id="repo-fixture-test-001",
                speaker_id="speaker_test",
                speaker_name="Test Speaker",
                speaker_from_id=True,
                source_audio_path=source_audio_path,
                reference_source_audio_path=reference_audio_path,
                transcript_path=transcript_path,
                language="sv-SE",
                manifest_target="swedish_smoke_train",
            )
        ],
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core._encode_audio_codes",
        lambda *, tokenizer_model, audio_paths: [[[11, 12, 13]] for _ in audio_paths],
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        )
    )

    assert report.inventory_rows == 1
    assert report.curated_rows == 1
    assert report.admitted_rows == 1
    assert report.prepared_rows == 1
    assert report.manifest_counts["swedish_smoke_train"] == 1

    output_root = Path(report.output_root)
    inventory_path = output_root / "inventory/repo_fixture_sv-fixture.jsonl"
    curated_path = output_root / "curated/swedish_smoke_train.jsonl"
    raw_manifest_path = output_root / "manifests/swedish_smoke_train.raw.jsonl"
    prepared_manifest_path = output_root / "manifests/swedish_smoke_train.prepared.jsonl"
    manifest_summary_path = output_root / "reports/manifest_summary.json"
    report_json_path = output_root / "report.json"

    assert inventory_path.is_file()
    assert curated_path.is_file()
    assert raw_manifest_path.is_file()
    assert prepared_manifest_path.is_file()
    assert manifest_summary_path.is_file()
    assert report_json_path.is_file()

    inventory_row = json.loads(inventory_path.read_text(encoding="utf-8").splitlines()[0])
    curated_row = json.loads(curated_path.read_text(encoding="utf-8").splitlines()[0])
    prepared_row = json.loads(prepared_manifest_path.read_text(encoding="utf-8").splitlines()[0])
    manifest_summary = json.loads(manifest_summary_path.read_text(encoding="utf-8"))

    assert inventory_row["source_sample_rate_hz"] == 16_000
    assert curated_row["quality_tier"] == "high_trust"
    assert curated_row["admission_decision"] == "admit"
    assert prepared_row["audio_codes"] == [[11, 12, 13]]
    assert manifest_summary["manifest_counts"]["swedish_smoke_train"] == 1

    for family in CANONICAL_MANIFEST_FAMILIES:
        assert (output_root / f"manifests/{family}.raw.jsonl").is_file()
        assert (output_root / f"manifests/{family}.prepared.jsonl").is_file()

    with wave.open((output_root / curated_row["audio_24k_path"]).as_posix(), "rb") as handle:
        assert handle.getframerate() == 24_000


def test_task103_runner_main_prints_report_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Task 103 runner should print the completed report as JSON."""
    expected_report = Task103PreprocessingReport(
        output_root="build/reference/qwen3-tts-swedish-corpus",
        fixture_dataset="repo_fixture_sv",
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=2,
        curated_rows=2,
        admitted_rows=2,
        prepared_rows=2,
        speaker_ids=["speaker_a", "speaker_b"],
        manifest_counts={"swedish_smoke_train": 2},
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        lambda settings: expected_report,
    )

    exit_code = main([])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["output_root"] == expected_report.output_root
    assert stdout_payload["prepared_rows"] == 2


def test_whisper_strict_scorer_resamples_to_processor_rate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The ASR scorer should resample 24 kHz training audio to 16 kHz for Whisper."""

    class _FakeInputFeatures:
        def __init__(self) -> None:
            self.dtype_received: object | None = None

        def to(self, *args: object, **kwargs: object) -> TorchTensorProtocol:
            self.dtype_received = kwargs.get("dtype")
            return self

    class _FakeProcessor:
        def __init__(self) -> None:
            self.feature_extractor = type("_FeatureExtractor", (), {"sampling_rate": 16_000})()
            self.sampling_rate_seen: int | None = None

        class _Processed:
            def __init__(self) -> None:
                self.input_features: TorchTensorProtocol = _FakeInputFeatures()
                self.attention_mask: TorchTensorProtocol | None = _FakeInputFeatures()

        def __call__(
            self,
            waveform: object,
            *,
            sampling_rate: int,
            return_tensors: str,
            return_attention_mask: bool,
        ) -> ProcessorOutputProtocol:
            assert return_tensors == "pt"
            assert return_attention_mask is True
            self.sampling_rate_seen = sampling_rate
            return self._Processed()

        def batch_decode(self, sequences: object, *, skip_special_tokens: bool) -> list[str]:
            assert skip_special_tokens is True
            return ["Hej från Sverige."]

    class _FakeModel:
        def to(self, device: object) -> "_FakeModel":
            return self

        def eval(self) -> None:
            return None

        def generate(
            self,
            input_features: object,
            *,
            attention_mask: object = None,
            max_new_tokens: int,
            task: str,
        ) -> list[list[int]]:
            assert attention_mask is not None
            assert max_new_tokens == 256
            assert task == "transcribe"
            return [[1, 2, 3]]

    fake_processor = _FakeProcessor()
    scorer = WhisperStrictScorer(
        model_id="KBLab/kb-whisper-large",
        revision="strict",
        _model=_FakeModel(),
        _processor=fake_processor,
        _device=type("_FakeDevice", (), {"type": "cpu"})(),
        _dtype=np.float32,
    )

    monkeypatch.setattr(
        "soundfile.read",
        lambda path, dtype: (np.ones(24_000, dtype=np.float32), 24_000),
    )
    monkeypatch.setattr(
        "librosa.resample",
        lambda waveform, *, orig_sr, target_sr: np.ones(target_sr, dtype=np.float32),
    )

    transcript = scorer.transcribe(tmp_path / "sample.wav")

    assert transcript == "Hej från Sverige."
    assert fake_processor.sampling_rate_seen == 16_000
