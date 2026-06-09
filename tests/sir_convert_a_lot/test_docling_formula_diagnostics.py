"""Tests for Docling formula/code VLM diagnostics.

Purpose:
    Prove the low-level diagnostics used for Task 344 expose batching,
    generation, device, token, and converter-cache facts without document text.

Relationships:
    - Exercises `infrastructure.docling_formula_diagnostics`.
    - Complements `test_task344_page_window_replay` replay-boundary tests.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling.models.inference_engines.vlm import VlmEngineInput
from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
from docling_core.types.doc import (
    BoundingBox,
    DoclingDocument,
    FormulaItem,
    NodeItem,
    ProvenanceItem,
)
from PIL import Image

import scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics as diagnostics
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics import (
    FormulaDiagnosticsCollector,
    begin_docling_formula_diagnostics,
    emit_code_formula_batch_started,
    emit_transformers_predict_batch_started,
    end_docling_formula_diagnostics,
    record_docling_converter_cache_lookup,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_events import (
    DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR,
    DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR,
    emit_docling_formula_diagnostic_event,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_generation_diagnostics import (
    DOCLING_FORMULA_TEXT_SAMPLES_DIR_ENV_VAR,
    run_with_transformers_generate_events,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_runtime_controls import (
    activate_formula_model_runtime_controls,
    apply_formula_runtime_controls_to_inputs,
    disable_formula_torch_compile_for_rocm,
    reset_formula_model_runtime_controls,
)
from scripts.sir_convert_a_lot.infrastructure.docling_runtime_inventory import (
    build_docling_runtime_inventory,
)


@dataclass(frozen=True)
class _FakeKey:
    table_mode: str = "accurate"
    ocr_enabled: bool = False
    force_full_page_ocr: bool = False
    ocr_engine: str | None = None
    ocr_languages: tuple[str, ...] = ()
    ocr_use_gpu: bool | None = None
    acceleration_device: str = "cuda"
    layout_model_key: str = "docling_layout_egret_large"
    formula_enrichment: bool = True
    formula_preset: str = "codeformulav2"
    document_timeout_seconds: int = 97


@dataclass(frozen=True)
class _FakeItem:
    label: str


@dataclass(frozen=True)
class _FakeElement:
    item: _FakeItem
    image: object


@dataclass(frozen=True)
class _FakeInput:
    image: object
    prompt: str
    max_new_tokens: int


@dataclass(frozen=True)
class _FakeOutput:
    metadata: dict[str, object]


class _FakeOptions:
    use_kv_cache = True


class _FakeParameter:
    dtype = "torch.float16"


class _FakeModel:
    def parameters(self) -> object:
        """Return a minimal iterable that exposes dtype."""
        return iter((_FakeParameter(),))


class _FakeTransformersEngine:
    device = "cuda:0"
    options = _FakeOptions()
    vlm_model = _FakeModel()
    _initialized = True


@dataclass(frozen=True)
class _FakeTensor:
    shape: tuple[int, ...]


class _FakeGeneratedTensor:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows
        self.shape = (len(rows), len(rows[0]) if rows else 0)

    def __getitem__(self, key: object) -> "_FakeGeneratedTensor":
        assert isinstance(key, tuple)
        row_slice, column_slice = key
        assert isinstance(row_slice, slice)
        assert isinstance(column_slice, slice)
        return _FakeGeneratedTensor([row[column_slice] for row in self.rows[row_slice]])

    def tolist(self) -> list[list[int]]:
        return self.rows


class _FakeGenerationConfig:
    eos_token_id = 0
    pad_token_id = 1
    max_new_tokens = None


class _FakeGenerationConfigWithTerminalTokens:
    eos_token_id = 99
    pad_token_id = 0
    max_new_tokens = None


class _FakeStopStringCriteria:
    stop_strings = ("</formula>",)


class _FakeGenerativeModel:
    def __init__(self) -> None:
        self.restored = False

    def generate(self, **kwargs: object) -> _FakeTensor:
        input_ids = kwargs["input_ids"]
        assert isinstance(input_ids, _FakeTensor)
        max_new_tokens = kwargs["max_new_tokens"]
        assert isinstance(max_new_tokens, int)
        return _FakeTensor((input_ids.shape[0], input_ids.shape[1] + max_new_tokens))


class _FakeMixedLengthGenerativeModel:
    def generate(self, **_kwargs: object) -> _FakeGeneratedTensor:
        return _FakeGeneratedTensor(
            [
                [10, 11, 12, 101, 102, 99, 0, 0, 0, 0],
                [20, 21, 22, 201, 202, 203, 204, 205, 206, 207],
            ]
        )


class _FakeProcessor:
    def batch_decode(
        self,
        sequences: _FakeGeneratedTensor,
        **_kwargs: object,
    ) -> list[str]:
        rows = sequences.tolist()
        return [
            "decoded formula </formula>" if 99 in row else "decoded formula without terminator"
            for row in rows
        ]


class _FakeGenerationEngine:
    def __init__(self) -> None:
        self.vlm_model = _FakeGenerativeModel()


class _FakeGenerationEngineWithProcessor:
    def __init__(self) -> None:
        self.vlm_model = _FakeMixedLengthGenerativeModel()
        self.processor = _FakeProcessor()


class _FakeFormulaModelSpec:
    stop_strings = ["</doctag>", "<|end_of_text|>"]


class _FakeFormulaOptions:
    model_spec = _FakeFormulaModelSpec()


class _FakeCodeFormulaModelWithStops:
    options = _FakeFormulaOptions()


class _FakeOriginalModel:
    pass


class _FakeCompiledModel:
    def __init__(self, original_model: _FakeOriginalModel) -> None:
        self._orig_mod = original_model


class _FakeCompiledTransformersEngine:
    def __init__(self) -> None:
        self.original_model = _FakeOriginalModel()
        self.vlm_model = _FakeCompiledModel(self.original_model)


def test_formula_diagnostics_payload_exposes_generation_and_cache_facts() -> None:
    collector = FormulaDiagnosticsCollector()
    collector.record_converter_cache_lookup(hit=False, key=_FakeKey())
    collector.record_converter_cache_lookup(hit=True, key=_FakeKey())
    collector.record_code_formula_batch(
        model=object(),
        element_batch=(
            _FakeElement(item=_FakeItem(label="formula"), image=Image.new("RGB", (10, 20))),
            _FakeElement(item=_FakeItem(label="formula"), image=Image.new("RGB", (30, 40))),
        ),
        yielded_count=2,
        elapsed_ms=123,
    )
    collector.record_transformers_call(
        engine=_FakeTransformersEngine(),
        input_batch=(
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=2048),
            _FakeInput(image=Image.new("RGB", (30, 40)), prompt="<formula>", max_new_tokens=2048),
        ),
        outputs=(
            _FakeOutput(metadata={"num_tokens": 50}),
            _FakeOutput(metadata={"num_tokens": 70}),
        ),
        elapsed_ms=456,
        status="succeeded",
        error_type=None,
        initialized_before=True,
    )

    payload = collector.to_payload()

    assert payload["converter_cache_hits"] == 1
    assert payload["converter_cache_misses"] == 1
    assert payload["formula_vlm_batch_count"] == 1
    assert payload["formula_vlm_item_count"] == 2
    assert payload["formula_vlm_total_ms"] == 123
    assert payload["transformers_call_count"] == 1
    assert payload["transformers_total_ms"] == 456
    assert payload["transformers_generated_token_total"] == 120

    batches_obj = payload["code_formula_batches"]
    assert isinstance(batches_obj, list)
    first_batch = batches_obj[0]
    assert isinstance(first_batch, dict)
    assert first_batch["crop_pixel_area_total"] == 1400
    assert first_batch["label_counts"] == {"formula": 2}

    calls_obj = payload["transformers_calls"]
    assert isinstance(calls_obj, list)
    first_call = calls_obj[0]
    assert isinstance(first_call, dict)
    assert first_call["device"] == "cuda:0"
    assert first_call["model_dtype"] == "torch.float16"
    assert first_call["max_new_tokens_max"] == 2048
    assert first_call["generated_token_counts"] == [50, 70]
    assert first_call["generated_token_max"] == 70


def test_formula_diagnostics_context_records_cache_lookup() -> None:
    token = begin_docling_formula_diagnostics()
    record_docling_converter_cache_lookup(hit=False, key=_FakeKey(document_timeout_seconds=33))

    payload = end_docling_formula_diagnostics(token)

    assert payload["converter_cache_misses"] == 1
    requests_obj = payload["converter_requests"]
    assert isinstance(requests_obj, list)
    request = requests_obj[0]
    assert isinstance(request, dict)
    key_obj = request["key"]
    assert isinstance(key_obj, dict)
    assert key_obj["document_timeout_seconds"] == 33
    assert key_obj["formula_preset"] == "codeformulav2"


def test_docling_runtime_inventory_reports_package_versions() -> None:
    inventory = build_docling_runtime_inventory()

    packages_obj = inventory["packages"]
    assert isinstance(packages_obj, dict)
    assert isinstance(packages_obj["docling"], str)
    assert isinstance(packages_obj["transformers"], str)
    assert "torch" in inventory


def test_formula_diagnostic_event_writer_persists_sanitized_jsonl(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())

    emit_docling_formula_diagnostic_event(
        {
            "event": "transformers_predict_batch_started",
            "batch_size": 2,
            "max_new_tokens_max": 2048,
        }
    )

    line = events_path.read_text(encoding="utf-8").strip()
    assert '"event": "transformers_predict_batch_started"' in line
    assert '"batch_size": 2' in line
    assert '"max_new_tokens_max": 2048' in line


def test_code_formula_batch_sidecar_records_crop_metrics_without_pixels(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())

    emit_code_formula_batch_started(
        model=object(),
        element_batch=(
            _FakeElement(item=_FakeItem(label="formula"), image=Image.new("RGB", (10, 20))),
        ),
    )

    record = json.loads(events_path.read_text(encoding="utf-8"))
    assert record["event"] == "code_formula_batch_started"
    assert record["batch_size"] == 1
    crops_obj = record["crops"]
    assert isinstance(crops_obj, list)
    crop = crops_obj[0]
    assert crop["label"] == "formula"
    assert crop["image_width"] == 10
    assert crop["image_height"] == 20
    assert crop["pixel_area"] == 200
    assert isinstance(crop["image_sha256"], str)
    assert len(crop["image_sha256"]) == 64
    assert "image_bytes" not in crop


def test_code_formula_batch_sidecar_records_docling_item_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())

    emit_code_formula_batch_started(
        model=object(),
        element_batch=(
            ItemAndImageEnrichmentElement(
                item=FormulaItem(
                    self_ref="#/texts/7",
                    orig="",
                    text="",
                    prov=[
                        ProvenanceItem(
                            page_no=14,
                            bbox=BoundingBox(l=10.12345, t=20.23456, r=30.34567, b=5.45678),
                            charspan=(0, 0),
                        )
                    ],
                ),
                image=Image.new("RGB", (10, 20)),
            ),
        ),
    )

    record = json.loads(events_path.read_text(encoding="utf-8"))
    crop = record["crops"][0]
    assert crop["item_self_ref"] == "#/texts/7"
    assert crop["prov_page_no"] == 14
    assert crop["prov_bbox"] == {"b": 5.457, "l": 10.123, "r": 30.346, "t": 20.235}


def test_transformers_predict_batch_sidecar_records_started_event_before_generation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())

    emit_transformers_predict_batch_started(
        engine=_FakeTransformersEngine(),
        input_batch=(
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=2048),
        ),
        initialized_before=True,
    )

    records = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records[0]["event"] == "transformers_predict_batch_started"
    assert records[0]["engine_class"] == "_FakeTransformersEngine"
    assert records[0]["device"] == "cuda:0"
    assert records[0]["max_new_tokens_max"] == 2048
    assert records[0]["status"] == "started"


def test_formula_model_stop_strings_are_forwarded_to_vlm_inputs() -> None:
    source_input = VlmEngineInput(
        image=Image.new("RGB", (10, 20)),
        prompt="<formula>",
        temperature=0.0,
        max_new_tokens=2048,
    )
    token = activate_formula_model_runtime_controls(_FakeCodeFormulaModelWithStops())

    try:
        controlled_inputs = apply_formula_runtime_controls_to_inputs([source_input])
    finally:
        reset_formula_model_runtime_controls(token)

    assert source_input.stop_strings == []
    assert "</doctag>" in controlled_inputs[0].stop_strings
    assert "<|end_of_text|>" in controlled_inputs[0].stop_strings
    assert "</formula>" in controlled_inputs[0].stop_strings
    assert "<end_of_utterance" in controlled_inputs[0].stop_strings
    assert controlled_inputs[0].extra_generation_config["no_repeat_ngram_size"] == 64
    assert controlled_inputs[0].extra_generation_config["renormalize_logits"] is True


def test_formula_generation_controls_preserve_existing_decoder_options() -> None:
    source_input = VlmEngineInput(
        image=Image.new("RGB", (10, 20)),
        prompt="<formula>",
        temperature=0.0,
        max_new_tokens=2048,
        extra_generation_config={"skip_special_tokens": False},
    )
    token = activate_formula_model_runtime_controls(_FakeCodeFormulaModelWithStops())

    try:
        controlled_inputs = apply_formula_runtime_controls_to_inputs([source_input])
    finally:
        reset_formula_model_runtime_controls(token)

    assert controlled_inputs[0].extra_generation_config["skip_special_tokens"] is False
    assert controlled_inputs[0].extra_generation_config["no_repeat_ngram_size"] == 64
    assert controlled_inputs[0].extra_generation_config["renormalize_logits"] is True


def test_formula_compile_guard_unwraps_rocm_optimized_module() -> None:
    engine = _FakeCompiledTransformersEngine()
    token = activate_formula_model_runtime_controls(_FakeCodeFormulaModelWithStops())

    try:
        changed = disable_formula_torch_compile_for_rocm(
            engine,
            rocm_runtime_available=True,
        )
    finally:
        reset_formula_model_runtime_controls(token)

    assert changed is True
    assert engine.vlm_model is engine.original_model


def test_generate_sidecar_records_token_budget_exhaustion_without_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())
    engine = _FakeGenerationEngine()
    original_generate = engine.vlm_model.generate

    def predict_batch() -> str:
        generated = engine.vlm_model.generate(
            input_ids=_FakeTensor((2, 5)),
            attention_mask=_FakeTensor((2, 5)),
            pixel_values=_FakeTensor((2, 3, 10, 20)),
            max_new_tokens=7,
            use_cache=True,
            do_sample=False,
            generation_config=_FakeGenerationConfig(),
        )
        assert generated.shape == (2, 12)
        return "ok"

    result = run_with_transformers_generate_events(
        engine=engine,
        input_batch=(
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
        ),
        predict_batch=predict_batch,
    )

    assert result == "ok"
    assert engine.vlm_model.generate == original_generate
    records = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["event"] for record in records] == [
        "transformers_generate_started",
        "transformers_generate_completed",
    ]
    assert records[0]["input_ids_shape"] == [2, 5]
    assert records[0]["pixel_values_shape"] == [2, 3, 10, 20]
    assert records[0]["max_new_tokens"] == 7
    assert records[0]["stopping_criteria_count"] is None
    assert records[1]["generated_ids_shape"] == [2, 12]
    assert records[1]["generated_new_token_counts"] == [7, 7]
    assert records[1]["generated_new_token_max"] == 7
    assert records[1]["max_new_tokens_exhausted"] is True
    assert "text" not in records[1]


def test_generate_sidecar_records_effective_counts_and_stop_markers_without_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())
    engine = _FakeGenerationEngineWithProcessor()

    def predict_batch() -> str:
        generated = engine.vlm_model.generate(
            input_ids=_FakeTensor((2, 3)),
            max_new_tokens=7,
            generation_config=_FakeGenerationConfigWithTerminalTokens(),
            stopping_criteria=[_FakeStopStringCriteria()],
        )
        assert generated.shape == (2, 10)
        return "ok"

    result = run_with_transformers_generate_events(
        engine=engine,
        input_batch=(
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
        ),
        predict_batch=predict_batch,
    )

    assert result == "ok"
    records = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed = records[1]
    assert completed["generated_new_token_counts"] == [7, 7]
    assert completed["generated_new_token_counts_effective"] == [3, 7]
    assert completed["generated_new_token_effective_max"] == 7
    assert completed["max_new_tokens_exhausted"] is True
    assert completed["decoded_stop_string_anywhere_count"] == 1
    assert completed["decoded_stop_string_terminal_count"] == 1
    assert "decoded formula" not in json.dumps(completed)


def test_generate_sidecar_can_write_opt_in_decoded_text_samples(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    sample_dir = tmp_path / "samples"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())
    monkeypatch.setenv(DOCLING_FORMULA_TEXT_SAMPLES_DIR_ENV_VAR, sample_dir.as_posix())
    engine = _FakeGenerationEngineWithProcessor()

    def predict_batch() -> str:
        engine.vlm_model.generate(
            input_ids=_FakeTensor((2, 3)),
            max_new_tokens=7,
            generation_config=_FakeGenerationConfigWithTerminalTokens(),
            stopping_criteria=[_FakeStopStringCriteria()],
        )
        return "ok"

    run_with_transformers_generate_events(
        engine=engine,
        input_batch=(
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
            _FakeInput(image=Image.new("RGB", (10, 20)), prompt="<formula>", max_new_tokens=7),
        ),
        predict_batch=predict_batch,
    )

    records = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sample_paths = records[1]["decoded_text_sample_paths"]
    assert isinstance(sample_paths, list)
    assert len(sample_paths) == 2
    sample_text = Path(sample_paths[0]).read_text(encoding="utf-8")
    assert sample_text == "decoded formula </formula>"


def test_single_item_replay_isolates_formula_batches_in_sidecar_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events_path = tmp_path / "formula-events.jsonl"
    monkeypatch.setenv(DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR, events_path.as_posix())
    monkeypatch.setenv(DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR, "1")
    received_batches: list[tuple[ItemAndImageEnrichmentElement, ...]] = []

    def fake_original(
        model: CodeFormulaVlmModel,
        doc: DoclingDocument,
        element_batch: Iterable[ItemAndImageEnrichmentElement],
    ) -> Iterable[NodeItem]:
        received_batch = tuple(element_batch)
        received_batches.append(received_batch)
        return (received_batch[0].item,)

    monkeypatch.setattr(diagnostics, "_ORIGINAL_CODE_FORMULA_CALL", fake_original)
    model = CodeFormulaVlmModel.__new__(CodeFormulaVlmModel)
    setattr(model, "engine", None)
    document = DoclingDocument(name="diagnostic")
    elements = (
        ItemAndImageEnrichmentElement(
            item=FormulaItem(self_ref="#/texts/0", orig="", text=""),
            image=Image.new("RGB", (10, 20)),
        ),
        ItemAndImageEnrichmentElement(
            item=FormulaItem(self_ref="#/texts/1", orig="", text=""),
            image=Image.new("RGB", (30, 40)),
        ),
    )

    yielded = list(diagnostics._instrumented_code_formula_call(model, document, elements))

    assert yielded == [elements[0].item, elements[1].item]
    assert received_batches == [(elements[0],), (elements[1],)]
    records = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records[0]["event"] == "code_formula_batch_split_started"
    assert records[0]["batch_size"] == 2
    assert [record["batch_size"] for record in records[1:]] == [1, 1]
    assert [record["crops"][0]["index"] for record in records[1:]] == [0, 0]


def test_duplicate_formula_item_self_ref_is_not_sent_to_vlm_twice(
    monkeypatch,
) -> None:
    received_batches: list[tuple[ItemAndImageEnrichmentElement, ...]] = []

    def fake_original(
        model: CodeFormulaVlmModel,
        doc: DoclingDocument,
        element_batch: Iterable[ItemAndImageEnrichmentElement],
    ) -> Iterable[NodeItem]:
        received_batch = tuple(element_batch)
        received_batches.append(received_batch)
        return tuple(element.item for element in received_batch)

    monkeypatch.delenv(DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR, raising=False)
    monkeypatch.setattr(diagnostics, "_ORIGINAL_CODE_FORMULA_CALL", fake_original)
    token = begin_docling_formula_diagnostics()
    model = CodeFormulaVlmModel.__new__(CodeFormulaVlmModel)
    setattr(model, "engine", None)
    document = DoclingDocument(name="diagnostic")
    repeated = ItemAndImageEnrichmentElement(
        item=FormulaItem(self_ref="#/texts/5", orig="", text=""),
        image=Image.new("RGB", (10, 20)),
    )

    first_yielded = list(diagnostics._instrumented_code_formula_call(model, document, (repeated,)))
    second_yielded = list(diagnostics._instrumented_code_formula_call(model, document, (repeated,)))
    payload = end_docling_formula_diagnostics(token)

    assert first_yielded == [repeated.item]
    assert second_yielded == [repeated.item]
    assert received_batches == [(repeated,)]
    assert payload["formula_vlm_item_count"] == 1
