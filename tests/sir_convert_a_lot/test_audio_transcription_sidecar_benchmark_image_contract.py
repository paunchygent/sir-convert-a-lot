"""Audio transcription sidecar benchmark image contract behavior.

Purpose:
    The benchmark-only STT sidecar image owns Hemma live-proof runtime
    packaging for FasterWhisper on ROCm, including the governed CTranslate2
    backend and Torch ROCm library compatibility.

Relationships:
    - `containers/stt-sidecar-benchmark/Dockerfile` defines the isolated image
      contract for audio transcription backend readiness.
    - Live-observation and runtime-probe surfaces consume this image before
      profile-proof ingestion can evaluate FasterWhisper evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

DOCKERFILE_PATH = Path("containers/stt-sidecar-benchmark/Dockerfile")


def test_benchmark_image_installs_official_ctranslate2_rocm_wheel_after_stt_deps() -> None:
    dockerfile = _dockerfile_text()
    args = _arg_values(dockerfile)

    assert dockerfile.startswith("# syntax=docker/dockerfile:1")
    assert args["CTRANSLATE2_VERSION"] == "4.8.0"
    assert args["CTRANSLATE2_ROCM_WHEELS_ARCHIVE"] == "rocm-python-wheels-Linux.zip"
    assert args["CTRANSLATE2_ROCM_WHEELS_SHA256"] == (
        "9ec6d82e5682b27af6c535f56525665c949cc63fbef14a9028c47b0164717143"
    )
    assert args["CTRANSLATE2_ROCM_WHEEL"] == (
        "ctranslate2-4.8.0-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
    )
    assert args["CTRANSLATE2_RELEASE_BASE_URL"] == (
        "https://github.com/OpenNMT/CTranslate2/releases/download"
    )
    assert (
        "${CTRANSLATE2_RELEASE_BASE_URL}/v${CTRANSLATE2_VERSION}/${CTRANSLATE2_ROCM_WHEELS_ARCHIVE}"
    ) in dockerfile
    assert "sha256sum --check" in dockerfile
    assert "python -m pip install --force-reinstall --no-deps" in dockerfile
    _assert_ordered(
        dockerfile,
        "faster-whisper",
        "pyannote.audio",
        "sha256sum --check",
        "python -m pip install --force-reinstall --no-deps",
        "${CTRANSLATE2_ROCM_WHEEL}",
    )


def test_benchmark_image_keeps_ctranslate2_rocm_libraries_out_of_global_linker_state() -> None:
    dockerfile = _dockerfile_text()
    args = _arg_values(dockerfile)

    assert args["TORCH_ROCM_LIBRARY_DIR"] == ("/app/.venv/lib/python3.11/site-packages/torch/lib")
    assert args["CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR"] == "/opt/ctranslate2-rocm-libraries"
    assert "patchelf" in dockerfile
    assert 'find "${TORCH_ROCM_LIBRARY_DIR}" -maxdepth 1' in dockerfile
    assert "-name 'lib*.so*'" in dockerfile
    assert "! -name 'libtinfo.so*'" in dockerfile
    assert "-exec ln -sf '{}' \"${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/\"" in dockerfile
    assert (
        'ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhiprand.so" '
        '"${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhiprand.so.1"'
    ) in dockerfile
    assert (
        'ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhipblas.so" '
        '"${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libhipblas.so.3"'
    ) in dockerfile
    assert (
        'ln -sf "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libamdhip64.so" '
        '"${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}/libamdhip64.so.7"'
    ) in dockerfile
    assert (
        'patchelf --set-rpath "\\$ORIGIN/../ctranslate2.libs:'
        '${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}"'
    ) in dockerfile
    assert (
        'patchelf --set-rpath "\\$ORIGIN:${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}"'
    ) in dockerfile
    _assert_ordered(
        dockerfile,
        "python -m pip install --force-reinstall --no-deps",
        'mkdir -p "${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}"',
        'find "${TORCH_ROCM_LIBRARY_DIR}"',
        "libhiprand.so.1",
        'patchelf --set-rpath "\\$ORIGIN/../ctranslate2.libs:',
        'patchelf --set-rpath "\\$ORIGIN:${CTRANSLATE2_ROCM_RUNTIME_LIBRARY_DIR}"',
    )
    assert "/etc/ld.so.conf" not in dockerfile
    assert "ldconfig" not in dockerfile
    assert "LD_LIBRARY_PATH" not in dockerfile


def _dockerfile_text() -> str:
    return DOCKERFILE_PATH.read_text(encoding="utf-8")


def _arg_values(dockerfile: str) -> dict[str, str]:
    matches = re.finditer(
        r"^ARG (?P<name>[A-Z0-9_]+)=(?P<value>[^\n]+)$",
        dockerfile,
        flags=re.MULTILINE,
    )
    return {match.group("name"): match.group("value") for match in matches}


def _assert_ordered(dockerfile: str, *fragments: str) -> None:
    position = -1
    for fragment in fragments:
        next_position = dockerfile.find(fragment, position + 1)
        assert next_position > position, f"{fragment!r} was not found after prior fragment"
        position = next_position
