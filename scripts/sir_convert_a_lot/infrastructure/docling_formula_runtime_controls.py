"""Docling formula VLM runtime controls.

Purpose:
    Carry Docling code/formula model-spec controls, such as stop strings, from
    `CodeFormulaVlmModel` into the generic VLM engine inputs.

Relationships:
    - Activated by `infrastructure.docling_formula_diagnostics` around Docling
      formula/code enrichment calls.
    - Applies controls to `VlmEngineInput` objects before Transformers
      generation receives them.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from os import environ

from docling.models.inference_engines.vlm import VlmEngineInput

_ACTIVE_FORMULA_STOP_STRINGS: ContextVar[tuple[str, ...]] = ContextVar(
    "sir_convert_a_lot_docling_formula_stop_strings",
    default=(),
)
_DOCLING_CODE_FORMULA_STAGE_STOP_STRINGS: tuple[str, ...] = (
    "</formula>",
    "</code>",
    "<end_of_utterance>",
    "<end_of_utterance",
)
_DOCLING_FORMULA_NO_REPEAT_NGRAM_SIZE = 64
_FORMULA_NO_REPEAT_NGRAM_SIZE_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_NO_REPEAT_NGRAM_SIZE"


def activate_formula_model_runtime_controls(model: object) -> Token[tuple[str, ...]]:
    """Activate formula model-spec controls for nested VLM engine calls."""
    return _ACTIVE_FORMULA_STOP_STRINGS.set(_formula_model_stop_strings(model))


def reset_formula_model_runtime_controls(token: Token[tuple[str, ...]]) -> None:
    """Reset formula runtime controls after a formula/model call."""
    _ACTIVE_FORMULA_STOP_STRINGS.reset(token)


def apply_formula_runtime_controls_to_inputs(
    input_batch: list[VlmEngineInput],
) -> list[VlmEngineInput]:
    """Return VLM inputs with active formula runtime controls applied."""
    stop_strings = _ACTIVE_FORMULA_STOP_STRINGS.get()
    if not stop_strings:
        return input_batch
    generation_config = _formula_generation_config()

    controlled_inputs: list[VlmEngineInput] = []
    changed = False
    for input_item in input_batch:
        update: dict[str, object] = {}
        if not input_item.stop_strings:
            update["stop_strings"] = list(stop_strings)
        merged_generation_config = {
            **input_item.extra_generation_config,
            **generation_config,
        }
        if merged_generation_config != input_item.extra_generation_config:
            update["extra_generation_config"] = merged_generation_config
        if not update:
            controlled_inputs.append(input_item)
            continue
        controlled_inputs.append(input_item.model_copy(update=update))
        changed = True
    return controlled_inputs if changed else input_batch


def disable_formula_torch_compile_for_rocm(
    engine: object,
    *,
    rocm_runtime_available: bool | None = None,
) -> bool:
    """Disable compiled Torch wrapper for active ROCm formula VLM generation."""
    if not _ACTIVE_FORMULA_STOP_STRINGS.get():
        return False
    if rocm_runtime_available is None:
        rocm_runtime_available = _rocm_runtime_available()
    if not rocm_runtime_available:
        return False
    model = getattr(engine, "vlm_model", None)
    original_model = getattr(model, "_orig_mod", None)
    if original_model is None:
        return False
    setattr(engine, "vlm_model", original_model)
    return True


def _formula_model_stop_strings(model: object) -> tuple[str, ...]:
    options = getattr(model, "options", None)
    model_spec = getattr(options, "model_spec", None)
    raw_stop_strings = getattr(model_spec, "stop_strings", ())
    if not isinstance(raw_stop_strings, list | tuple):
        return ()
    return _dedupe_stop_strings(
        tuple(value for value in raw_stop_strings if isinstance(value, str) and value.strip())
        + _DOCLING_CODE_FORMULA_STAGE_STOP_STRINGS
    )


def _formula_generation_config() -> dict[str, object]:
    no_repeat_ngram_size = (
        _positive_int_env(_FORMULA_NO_REPEAT_NGRAM_SIZE_ENV_VAR)
        or _DOCLING_FORMULA_NO_REPEAT_NGRAM_SIZE
    )
    return {
        "no_repeat_ngram_size": no_repeat_ngram_size,
        "renormalize_logits": True,
    }


def _positive_int_env(name: str) -> int | None:
    raw_value = environ.get(name)
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError:
        return None
    return value if value > 0 else None


def _rocm_runtime_available() -> bool:
    try:
        import torch

        version = getattr(torch, "version", None)
        return bool(
            torch.cuda.is_available()
            and getattr(version, "hip", None) is not None
            and getattr(version, "cuda", None) is None
        )
    except Exception:
        return False


def _dedupe_stop_strings(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        result.append(value)
        seen.add(value)
    return tuple(result)
