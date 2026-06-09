"""Docling Transformers generation diagnostics.

Purpose:
    Observe formula/code VLM calls at the Hugging Face `generate` boundary.
    Decoded model output is retained only when an explicit diagnostic sample
    directory is configured for root-cause replay.

Relationships:
    - Called by `infrastructure.docling_formula_diagnostics`.
    - Emits JSONL events through `docling_formula_diagnostics_events`.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence, Sized
from hashlib import sha256
from os import environ
from pathlib import Path
from typing import TypeVar

from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_events import (
    docling_formula_diagnostic_events_enabled,
    emit_docling_formula_diagnostic_event,
)

ResultT = TypeVar("ResultT")
PredictBatchCall = Callable[[], ResultT]
GenerateCall = Callable[..., object]
DOCLING_FORMULA_TEXT_SAMPLES_DIR_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_TEXT_SAMPLES_DIR"
DOCLING_FORMULA_TOKEN_PROBE_DIR_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_TOKEN_PROBE_DIR"


def run_with_transformers_generate_events(
    *,
    engine: object,
    input_batch: Sequence[object],
    predict_batch: PredictBatchCall[ResultT],
) -> ResultT:
    """Run a Transformers VLM batch while emitting generation-boundary events."""
    if not docling_formula_diagnostic_events_enabled():
        return predict_batch()
    model = getattr(engine, "vlm_model", None)
    original_generate = getattr(model, "generate", None)
    if model is None or not callable(original_generate):
        return predict_batch()
    return _run_with_patched_generate(
        engine=engine,
        model=model,
        original_generate=original_generate,
        input_batch=input_batch,
        predict_batch=predict_batch,
    )


def _run_with_patched_generate(
    *,
    engine: object,
    model: object,
    original_generate: GenerateCall,
    input_batch: Sequence[object],
    predict_batch: PredictBatchCall[ResultT],
) -> ResultT:
    def instrumented_generate(*args: object, **kwargs: object) -> object:
        started = time.perf_counter()
        token_probe = _attach_token_probe(engine=engine, kwargs=kwargs)
        emit_docling_formula_diagnostic_event(
            {
                "event": "transformers_generate_started",
                **_generate_started_payload(
                    model=model,
                    input_batch=input_batch,
                    kwargs=kwargs,
                ),
            }
        )
        try:
            result = original_generate(*args, **kwargs)
            token_probe_path = _write_token_probe(
                probe=token_probe,
                generated=result,
                kwargs=kwargs,
            )
        except Exception as exc:
            emit_docling_formula_diagnostic_event(
                {
                    "event": "transformers_generate_failed",
                    "elapsed_ms": _elapsed_ms(started),
                    "error_type": type(exc).__name__,
                    **_cuda_memory_payload(),
                }
            )
            raise
        emit_docling_formula_diagnostic_event(
            {
                "event": "transformers_generate_completed",
                "elapsed_ms": _elapsed_ms(started),
                **_generate_completed_payload(
                    engine=engine,
                    generated=result,
                    kwargs=kwargs,
                ),
                **({"token_probe_path": token_probe_path} if token_probe_path else {}),
                **_cuda_memory_payload(),
            }
        )
        return result

    try:
        setattr(model, "generate", instrumented_generate)
    except Exception as exc:
        emit_docling_formula_diagnostic_event(
            {
                "event": "transformers_generate_patch_failed",
                "error_type": type(exc).__name__,
            }
        )
        return predict_batch()
    try:
        return predict_batch()
    finally:
        try:
            setattr(model, "generate", original_generate)
        except Exception:
            pass


def _generate_started_payload(
    *,
    model: object,
    input_batch: Sequence[object],
    kwargs: dict[str, object],
) -> dict[str, object]:
    generation_config = kwargs.get("generation_config")
    return {
        "model_class": type(model).__name__,
        "wrapped_model_class": _wrapped_model_class(model),
        "batch_size": len(input_batch),
        "input_ids_shape": _shape_payload(kwargs.get("input_ids")),
        "attention_mask_shape": _shape_payload(kwargs.get("attention_mask")),
        "pixel_values_shape": _shape_payload(kwargs.get("pixel_values")),
        "image_sizes_shape": _shape_payload(kwargs.get("image_sizes")),
        "max_new_tokens": _positive_int(kwargs.get("max_new_tokens")),
        "use_cache": _bool_or_none(kwargs.get("use_cache")),
        "do_sample": _bool_or_none(kwargs.get("do_sample")),
        "stopping_criteria_count": _sequence_length(kwargs.get("stopping_criteria")),
        "generation_config_eos_token_id": _simple_config_value(
            generation_config,
            "eos_token_id",
        ),
        "generation_config_pad_token_id": _simple_config_value(
            generation_config,
            "pad_token_id",
        ),
        "generation_config_max_new_tokens": _positive_int(
            getattr(generation_config, "max_new_tokens", None)
        ),
        "no_repeat_ngram_size": _positive_int(kwargs.get("no_repeat_ngram_size")),
        "renormalize_logits": _bool_or_none(kwargs.get("renormalize_logits")),
        **_cuda_memory_payload(),
    }


def _generate_completed_payload(
    *,
    engine: object,
    generated: object,
    kwargs: dict[str, object],
) -> dict[str, object]:
    sequences = getattr(generated, "sequences", generated)
    input_shape = _shape_payload(kwargs.get("input_ids"))
    output_shape = _shape_payload(sequences)
    input_length = _second_dimension(input_shape)
    max_new_tokens = _positive_int(kwargs.get("max_new_tokens"))
    generated_new_token_counts = _new_token_counts(
        output_shape=output_shape,
        input_length=input_length,
    )
    effective_counts = _effective_new_token_counts(
        sequences=sequences,
        input_length=input_length,
        terminal_token_ids=_terminal_token_ids(kwargs.get("generation_config")),
    )
    exhaustion_counts = effective_counts or generated_new_token_counts
    exhausted = (
        max(exhaustion_counts) >= max_new_tokens
        if exhaustion_counts and max_new_tokens is not None
        else None
    )
    return {
        "generated_ids_shape": output_shape,
        "input_token_length": input_length,
        "generated_new_token_counts": generated_new_token_counts,
        "generated_new_token_counts_effective": effective_counts,
        "generated_new_token_max": max(generated_new_token_counts)
        if generated_new_token_counts
        else None,
        "generated_new_token_effective_max": max(effective_counts) if effective_counts else None,
        "max_new_tokens": max_new_tokens,
        "max_new_tokens_exhausted": exhausted,
        **_decoded_stop_string_payload(
            engine=engine,
            sequences=sequences,
            input_length=input_length,
            kwargs=kwargs,
        ),
    }


def _shape_payload(value: object) -> list[int] | None:
    shape = getattr(value, "shape", None)
    if shape is None:
        return None
    result: list[int] = []
    try:
        for dimension in shape:
            if isinstance(dimension, bool):
                return None
            result.append(int(dimension))
    except Exception:
        return None
    return result


def _new_token_counts(
    *,
    output_shape: list[int] | None,
    input_length: int | None,
) -> list[int]:
    if output_shape is None or len(output_shape) < 2 or input_length is None:
        return []
    batch_size = max(0, output_shape[0])
    output_length = max(0, output_shape[1])
    new_tokens = max(0, output_length - input_length)
    return [new_tokens for _ in range(batch_size)]


def _effective_new_token_counts(
    *,
    sequences: object,
    input_length: int | None,
    terminal_token_ids: set[int],
) -> list[int] | None:
    if input_length is None or not terminal_token_ids:
        return None
    rows = _sequence_rows(sequences)
    if rows is None:
        return None

    counts: list[int] = []
    for row in rows:
        generated_ids = row[input_length:]
        terminal_suffix_start = _terminal_suffix_start(
            generated_ids,
            terminal_token_ids,
        )
        if terminal_suffix_start is None:
            counts.append(len(generated_ids))
            continue
        counts.append(terminal_suffix_start + 1)
    return counts


def _terminal_suffix_start(
    token_ids: list[int],
    terminal_token_ids: set[int],
) -> int | None:
    for index, token_id in enumerate(token_ids):
        if token_id not in terminal_token_ids:
            continue
        if all(candidate in terminal_token_ids for candidate in token_ids[index:]):
            return index
    return None


def _decoded_stop_string_payload(
    *,
    engine: object,
    sequences: object,
    input_length: int | None,
    kwargs: dict[str, object],
) -> dict[str, object]:
    stop_strings = _stop_strings_from_kwargs(kwargs)
    if input_length is None or not stop_strings:
        return {}
    try:
        decoded_texts = _decode_generated_texts(
            engine=engine,
            sequences=sequences,
            input_length=input_length,
        )
    except Exception as exc:
        return {"decoded_stop_string_probe_error_type": type(exc).__name__}
    if decoded_texts is None:
        return {}

    char_counts = [len(text) for text in decoded_texts]
    sample_payload = _write_decoded_text_samples(decoded_texts)
    return {
        "decoded_text_count": len(decoded_texts),
        "decoded_text_char_count_min": min(char_counts) if char_counts else None,
        "decoded_text_char_count_max": max(char_counts) if char_counts else None,
        "decoded_text_sha256": [_text_sha256(text) for text in decoded_texts],
        "decoded_stop_string_anywhere_count": sum(
            1 for text in decoded_texts if _contains_stop_string(text, stop_strings)
        ),
        "decoded_stop_string_terminal_count": sum(
            1 for text in decoded_texts if _ends_with_stop_string(text, stop_strings)
        ),
        **sample_payload,
    }


def _decode_generated_texts(
    *,
    engine: object,
    sequences: object,
    input_length: int,
) -> list[str] | None:
    processor = getattr(engine, "processor", None)
    decode_fn = getattr(processor, "batch_decode", None)
    if decode_fn is None:
        tokenizer = getattr(processor, "tokenizer", None)
        decode_fn = getattr(tokenizer, "batch_decode", None)
    if decode_fn is None:
        return None

    trimmed = _trim_sequences(sequences, input_length)
    try:
        decoded = decode_fn(
            trimmed,
            skip_special_tokens=False,
            clean_up_tokenization_spaces=False,
        )
    except TypeError:
        decoded = decode_fn(trimmed)
    return [text for text in decoded if isinstance(text, str)]


def _write_decoded_text_samples(decoded_texts: list[str]) -> dict[str, object]:
    sample_dir_raw = environ.get(DOCLING_FORMULA_TEXT_SAMPLES_DIR_ENV_VAR)
    if not sample_dir_raw:
        return {}
    sample_dir = Path(sample_dir_raw)
    sample_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for index, text in enumerate(decoded_texts):
        digest = _text_sha256(text)
        path = sample_dir / f"formula-output-{index:02d}-{digest[:16]}.txt"
        path.write_text(text, encoding="utf-8")
        paths.append(path.as_posix())
    return {"decoded_text_sample_paths": paths}


def _text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _attach_token_probe(
    *,
    engine: object,
    kwargs: dict[str, object],
) -> object | None:
    probe_dir_raw = environ.get(DOCLING_FORMULA_TOKEN_PROBE_DIR_ENV_VAR)
    if not probe_dir_raw:
        return None
    input_length = _second_dimension(_shape_payload(kwargs.get("input_ids")))
    if input_length is None:
        return None
    try:
        from transformers import LogitsProcessorList
    except Exception:
        return None

    probe = _TokenProbe(
        engine=engine,
        input_length=input_length,
        probe_dir=Path(probe_dir_raw),
        generation_config=kwargs.get("generation_config"),
        stop_strings=_stop_strings_from_kwargs(kwargs),
    )
    existing_processors = kwargs.get("logits_processor")
    if existing_processors is None:
        kwargs["logits_processor"] = LogitsProcessorList([probe])
        return probe
    append = getattr(existing_processors, "append", None)
    if callable(append):
        append(probe)
        return probe
    return None


class _TokenProbe:
    def __init__(
        self,
        *,
        engine: object,
        input_length: int,
        probe_dir: Path,
        generation_config: object,
        stop_strings: tuple[str, ...],
    ) -> None:
        processor = getattr(engine, "processor", None)
        self.tokenizer = getattr(processor, "tokenizer", None)
        self.input_length = input_length
        self.probe_dir = probe_dir
        self.terminal_token_ids = sorted(_terminal_token_ids(generation_config))
        self.stop_string_token_ids = _stop_string_token_ids(
            tokenizer=self.tokenizer,
            stop_strings=stop_strings,
        )
        self.records: list[dict[str, object]] = []

    def __call__(self, input_ids: object, scores: object) -> object:
        generated_so_far = _generated_so_far(input_ids, self.input_length)
        if generated_so_far is None or not _should_record_probe_step(generated_so_far):
            return scores
        row_scores = _first_score_row(scores)
        if row_scores is None:
            return scores
        previous_token_id = _previous_token_id(input_ids)
        self.records.append(
            {
                "generated_so_far": generated_so_far,
                "previous_token_id": previous_token_id,
                "previous_token_text": _decode_token(self.tokenizer, previous_token_id),
                "top_tokens": _top_token_records(
                    tokenizer=self.tokenizer,
                    row_scores=row_scores,
                    token_ids_of_interest=set(self.terminal_token_ids)
                    | set(self.stop_string_token_ids),
                ),
            }
        )
        return scores


def _write_token_probe(
    *,
    probe: object | None,
    generated: object,
    kwargs: dict[str, object],
) -> str | None:
    if not isinstance(probe, _TokenProbe):
        return None
    sequences = getattr(generated, "sequences", generated)
    rows = _sequence_rows(sequences)
    if rows is None or not rows:
        return None
    probe.probe_dir.mkdir(parents=True, exist_ok=True)
    path = probe.probe_dir / f"token-probe-{time.time_ns()}.json"
    import json

    payload = {
        "input_length": probe.input_length,
        "max_new_tokens": _positive_int(kwargs.get("max_new_tokens")),
        "terminal_token_ids": probe.terminal_token_ids,
        "stop_string_token_ids": probe.stop_string_token_ids,
        "generated_new_token_counts_effective": _effective_new_token_counts(
            sequences=sequences,
            input_length=probe.input_length,
            terminal_token_ids=set(probe.terminal_token_ids),
        ),
        "generated_token_tail": [
            {
                "token_id": token_id,
                "token_text": _decode_token(probe.tokenizer, token_id),
            }
            for token_id in rows[0][max(probe.input_length, len(rows[0]) - 48) :]
        ],
        "records": probe.records,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return path.as_posix()


def _stop_string_token_ids(
    *,
    tokenizer: object,
    stop_strings: tuple[str, ...],
) -> list[int]:
    encode = getattr(tokenizer, "encode", None)
    if not callable(encode):
        return []
    token_ids: set[int] = set()
    for stop_string in stop_strings:
        try:
            encoded = encode(stop_string, add_special_tokens=False)
        except Exception:
            continue
        if isinstance(encoded, list):
            token_ids.update(int(token_id) for token_id in encoded if isinstance(token_id, int))
    return sorted(token_ids)


def _generated_so_far(input_ids: object, input_length: int) -> int | None:
    current_length = _second_dimension(_shape_payload(input_ids))
    if current_length is None:
        return None
    return max(0, current_length - input_length)


def _should_record_probe_step(generated_so_far: int) -> bool:
    return generated_so_far < 128 or generated_so_far % 128 == 0


def _first_score_row(scores: object) -> object | None:
    getitem = getattr(scores, "__getitem__", None)
    if not callable(getitem):
        return None
    try:
        first_row: object = getitem(0)
        return first_row
    except Exception:
        return None


def _previous_token_id(input_ids: object) -> int | None:
    rows = _sequence_rows(input_ids)
    if not rows or not rows[0]:
        return None
    return rows[0][-1]


def _top_token_records(
    *,
    tokenizer: object,
    row_scores: object,
    token_ids_of_interest: set[int],
) -> list[dict[str, object]]:
    try:
        import torch

        detach = getattr(row_scores, "detach", None)
        if not callable(detach):
            return []
        detached_scores = detach()
        as_float = getattr(detached_scores, "float", None)
        if not callable(as_float):
            return []
        scores = as_float()
        probabilities = torch.softmax(scores, dim=-1)
        values, indices = torch.topk(probabilities, k=8)
        top_ids = [int(token_id) for token_id in indices.tolist()]
        records = [
            _token_score_record(
                tokenizer=tokenizer,
                token_id=token_id,
                probability=float(values[index].item()),
                rank_hint=index + 1,
            )
            for index, token_id in enumerate(top_ids)
        ]
        for token_id in sorted(token_ids_of_interest - set(top_ids)):
            if token_id < 0 or token_id >= int(probabilities.shape[0]):
                continue
            records.append(
                _token_score_record(
                    tokenizer=tokenizer,
                    token_id=token_id,
                    probability=float(probabilities[token_id].item()),
                    rank_hint=None,
                )
            )
        return records
    except Exception:
        return []


def _token_score_record(
    *,
    tokenizer: object,
    token_id: int,
    probability: float,
    rank_hint: int | None,
) -> dict[str, object]:
    return {
        "token_id": token_id,
        "token_text": _decode_token(tokenizer, token_id),
        "probability": probability,
        "rank_hint": rank_hint,
    }


def _decode_token(tokenizer: object, token_id: int | None) -> str | None:
    if token_id is None:
        return None
    decode = getattr(tokenizer, "decode", None)
    if not callable(decode):
        return None
    try:
        value = decode([token_id])
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _trim_sequences(sequences: object, input_length: int) -> object:
    getitem = getattr(sequences, "__getitem__", None)
    if callable(getitem):
        try:
            return getitem((slice(None), slice(input_length, None)))
        except Exception:
            pass
    rows = _sequence_rows(sequences)
    if rows is None:
        return sequences
    return [row[input_length:] for row in rows]


def _sequence_rows(sequences: object) -> list[list[int]] | None:
    tolist = getattr(sequences, "tolist", None)
    if callable(tolist):
        try:
            rows = tolist()
        except Exception:
            return None
    else:
        rows = sequences
    if not isinstance(rows, list):
        return None

    normalized_rows: list[list[int]] = []
    for row in rows:
        if not isinstance(row, list):
            return None
        normalized_rows.append([int(token_id) for token_id in row])
    return normalized_rows


def _terminal_token_ids(generation_config: object) -> set[int]:
    token_ids: set[int] = set()
    for value in (
        _simple_config_value(generation_config, "eos_token_id"),
        _simple_config_value(generation_config, "pad_token_id"),
    ):
        token_ids.update(_flatten_ints(value))
    return token_ids


def _flatten_ints(value: object) -> set[int]:
    if value is None:
        return set()
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            value = tolist()
        except Exception:
            return set()
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, list | tuple | set):
        result: set[int] = set()
        for item in value:
            result.update(_flatten_ints(item))
        return result
    return set()


def _stop_strings_from_kwargs(kwargs: dict[str, object]) -> tuple[str, ...]:
    values: list[str] = []
    generation_config = kwargs.get("generation_config")
    values.extend(_string_sequence(getattr(generation_config, "stop_strings", None)))
    stopping_criteria = kwargs.get("stopping_criteria")
    if isinstance(stopping_criteria, Sequence):
        for criteria in stopping_criteria:
            values.extend(_string_sequence(getattr(criteria, "stop_strings", None)))
    return _dedupe_strings(values)


def _string_sequence(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list | tuple):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dedupe_strings(values: list[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)


def _contains_stop_string(text: str, stop_strings: tuple[str, ...]) -> bool:
    return any(stop_string in text for stop_string in stop_strings)


def _ends_with_stop_string(text: str, stop_strings: tuple[str, ...]) -> bool:
    stripped_text = text.rstrip()
    return any(stripped_text.endswith(stop_string) for stop_string in stop_strings)


def _second_dimension(shape: list[int] | None) -> int | None:
    if shape is None or len(shape) < 2:
        return None
    return max(0, shape[1])


def _wrapped_model_class(model: object) -> str | None:
    wrapped = getattr(model, "_orig_mod", None)
    if wrapped is None:
        return None
    return type(wrapped).__name__


def _simple_config_value(config: object, name: str) -> object:
    value = getattr(config, name, None)
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list | tuple):
        return list(value)
    return str(value)


def _sequence_length(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, Sized):
        return len(value)
    return None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, value)


def _bool_or_none(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _cuda_memory_payload() -> dict[str, object]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {"cuda_available": False}
        return {
            "cuda_available": True,
            "cuda_memory_allocated_bytes": int(torch.cuda.memory_allocated()),
            "cuda_memory_reserved_bytes": int(torch.cuda.memory_reserved()),
            "cuda_max_memory_allocated_bytes": int(torch.cuda.max_memory_allocated()),
            "cuda_max_memory_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        }
    except Exception:
        return {}


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
