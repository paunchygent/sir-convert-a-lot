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
DEPS_DOCKERFILE_PATH = Path("Dockerfile.deps")


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
        "ctranslate2-4.8.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
    )
    assert args["CTRANSLATE2_RELEASE_BASE_URL"] == (
        "https://github.com/OpenNMT/CTranslate2/releases/download"
    )
    assert (
        "${CTRANSLATE2_RELEASE_BASE_URL}/v${CTRANSLATE2_VERSION}/${CTRANSLATE2_ROCM_WHEELS_ARCHIVE}"
    ) in dockerfile
    assert "sha256sum --check" in dockerfile
    assert "python -m pip install --force-reinstall --no-deps" in dockerfile
    assert '"pyannote.audio==4.0.4"' in dockerfile
    assert '"torchcodec==0.10.0"' in dockerfile
    _assert_ordered(
        dockerfile,
        "faster-whisper",
        '"pyannote.audio==4.0.4"',
        '"torchcodec==0.10.0"',
        "sha256sum --check",
        "python -m pip install --force-reinstall --no-deps",
        "${CTRANSLATE2_ROCM_WHEEL}",
    )


def test_benchmark_image_installs_miopen_hiprtc_header_dependencies() -> None:
    dockerfile = _dockerfile_text()

    assert "librocrand-dev" in dockerfile
    assert "libc6-dev" in dockerfile
    _assert_ordered(
        dockerfile,
        "ffmpeg",
        "libc6-dev",
        "librocrand-dev",
        "patchelf",
        "python -m pip install --upgrade",
    )


def test_benchmark_image_keeps_ctranslate2_rocm_libraries_out_of_global_linker_state() -> None:
    dockerfile = _dockerfile_text()
    args = _arg_values(dockerfile)

    assert args["TORCH_ROCM_LIBRARY_DIR"] == "/app/.venv/lib/python3.12/site-packages/torch/lib"
    assert args["CTRANSLATE2_PYTHON_PACKAGE_DIR"] == (
        "/app/.venv/lib/python3.12/site-packages/ctranslate2"
    )
    assert args["CTRANSLATE2_WHEEL_LIBRARY_DIR"] == (
        "/app/.venv/lib/python3.12/site-packages/ctranslate2.libs"
    )
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


def test_sidecar_image_exposes_long_running_http_service_and_probe_modules() -> None:
    dockerfile = _dockerfile_text()

    assert '"fastapi>=0.128.8"' in dockerfile
    assert '"uvicorn[standard]>=0.40.0"' in dockerfile
    assert "COPY scripts/sir_convert_a_lot/stt_sidecar" in dockerfile
    assert "COPY scripts/sir_convert_a_lot/devops" in dockerfile
    assert "EXPOSE 8095" in dockerfile
    assert (
        'CMD ["uvicorn", "scripts.sir_convert_a_lot.stt_sidecar.app:app", '
        '"--host", "0.0.0.0", "--port", "8095"]'
    ) in dockerfile


def test_benchmark_image_contract_matches_deps_base_cpython_3_12() -> None:
    deps_dockerfile = DEPS_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert _arg_values(deps_dockerfile)["PYTHON_IMAGE"] == "python:3.12-slim"


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
