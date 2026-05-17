"""Tests for the Qwen provider build/runtime split.

Purpose:
    Lock the Hemma runbook contract that llama.cpp HIP builds are serialized,
    bounded to `-j8`, and run with `nice -n 10`, while Docker Compose only
    starts the already-built provider runtime.

Relationships:
    - Exercises `scripts/devops/qwen-llama-provider-build.sh`.
    - Complements compose tests for the `sir_convert_qwen_answer_key` service.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "devops" / "qwen-llama-provider-build.sh"
QWEN_DOCKERFILE = REPO_ROOT / "Dockerfile.qwen-provider"


def test_qwen_llama_provider_build_enforces_runbook_jobs_and_niceness() -> None:
    script = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert 'LLAMA_CPP_BUILD_JOBS="${SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_JOBS:-8}"' in script
    assert 'LLAMA_CPP_BUILD_NICE="${SIR_CONVERT_A_LOT_LLAMA_CPP_BUILD_NICE:-10}"' in script
    assert "MAX_LLAMA_CPP_BUILD_JOBS=8" in script
    assert "MIN_LLAMA_CPP_BUILD_NICE=10" in script
    assert 'nice -n "${LLAMA_CPP_BUILD_NICE}" ninja' in script
    assert '-j"${LLAMA_CPP_BUILD_JOBS}" llama-server' in script
    assert "-DCMAKE_POSITION_INDEPENDENT_CODE=ON" in script
    assert "-DGGML_HIP=ON" in script
    assert "-DAMDGPU_TARGETS=gfx1201" in script


def test_qwen_provider_image_does_not_hide_llama_cpp_build() -> None:
    dockerfile = QWEN_DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM ${QWEN_PROVIDER_BASE_IMAGE} AS qwen-provider-runtime" in dockerfile
    assert "EXPOSE 8082" in dockerfile
    assert "_rocm_sdk_devel/lib" in dockerfile
    assert "_rocm_sdk_libraries_gfx120X_all/lib" in dockerfile
    assert "_rocm_sdk_core/lib" in dockerfile
    assert "/opt/rocm-7.2.0/lib" not in dockerfile
    assert "/opt/amdgpu/lib" not in dockerfile
    assert "RUN cmake" not in dockerfile
    assert "RUN ninja" not in dockerfile
    assert "git clone" not in dockerfile
