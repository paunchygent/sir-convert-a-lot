"""Tests for lightweight ref-input module imports.

Purpose:
    Protect the governed bundle-finalization path from importing the heavy
    Qwen runtime stack when it only needs precomputed ref-input metadata.

Relationships:
    - Exercises `sft_12hz_ref_inputs.py`.
    - Guards `bundle_precomputed_ref_inputs.py` import behavior used by
      containerized bundle finalization.
"""

from __future__ import annotations

import builtins
import importlib
import sys


def test_bundle_precomputed_ref_input_import_does_not_eagerly_import_qwen_tts(
    monkeypatch,
) -> None:
    """Metadata helper imports should not pull `qwen_tts` at module import time."""
    target_modules = (
        "scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs",
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_precomputed_ref_inputs",
    )
    for module_name in target_modules:
        sys.modules.pop(module_name, None)

    blocked_imports: list[str] = []
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("qwen_tts"):
            blocked_imports.append(name)
            raise AssertionError("`qwen_tts` should not be imported eagerly here.")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    imported_module = importlib.import_module(
        "scripts.sir_convert_a_lot.ml.qwen.training.bundle_precomputed_ref_inputs"
    )

    assert imported_module.PRECOMPUTED_REF_INPUT_KIND == "ref_mel"
    assert blocked_imports == []
