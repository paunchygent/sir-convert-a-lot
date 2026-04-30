"""Canonical Hemma runner for the Task 74 throughput benchmark.

Purpose:
    Execute the full Task 74 Hemma benchmark workflow against a parity-checked
    revision by synchronizing the prod env mirror, verifying the server-side
    env contract, syncing the host PDM runtime, warming a host EasyOCR cache,
    rerunning the live host-lane smoke, and then invoking the benchmark
    harness with explicit parity metadata.

Relationships:
    - Reuses `scripts/devops/sync-prod-env-mirror.sh` for canonical Hemma env
      mirroring and symlink refresh.
    - Reuses `scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions` to
      prove the live deployed runtime is healthy before benchmarking.
    - Invokes `scripts.sir_convert_a_lot.benchmark_story20_throughput_report`
      as the canonical Task 74 harness after host-runtime preflight.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

CANONICAL_REPO_ROOT = Path("/home/paunchygent/apps/sir-convert-a-lot")
CANONICAL_ENV_PATH = Path("/home/paunchygent/infrastructure/env/prod/sir-convert-a-lot.env")
CANONICAL_ENV_LINK = CANONICAL_REPO_ROOT / ".env"
DEFAULT_SERVICE_URL = "http://127.0.0.1:28085"
DEFAULT_OUTPUT_JSON = Path("build/benchmarks/story-20/task-74-throughput-benchmark-hemma.json")
DEFAULT_OUTPUT_REPORT = Path("build/benchmarks/story-20/task-74-throughput-report-hemma.md")
DEFAULT_CORPUS_ROOT = Path("build/benchmarks/story-20/task-74-corpus")
DEFAULT_DATA_ROOT = Path("build/benchmarks/story-20/task-74-runtime")
DEFAULT_SWEEP_OUTPUT_JSON = Path("build/benchmarks/story-20/task-74-two-worker-sweep-hemma.json")
DEFAULT_SWEEP_OUTPUT_REPORT = Path(
    "build/benchmarks/story-20/task-74-two-worker-sweep-report-hemma.md"
)
DEFAULT_SWEEP_CORPUS_ROOT = Path("build/benchmarks/story-20/task-74-two-worker-sweep-corpus")
DEFAULT_SWEEP_DATA_ROOT = Path("build/benchmarks/story-20/task-74-two-worker-sweep-runtime")
DEFAULT_HOST_EASYOCR_CACHE = Path("/home/paunchygent/.cache/sir-convert-a-lot/easyocr-models")
DEFAULT_MIOPEN_CACHE_ROOT = Path("/srv/scratch/sir-convert-a-lot/cache/miopen")
DEFAULT_MIOPEN_USER_DB_PATH = DEFAULT_MIOPEN_CACHE_ROOT / "user-db"
DEFAULT_MIOPEN_KERNEL_CACHE_DIR = DEFAULT_MIOPEN_CACHE_ROOT / "kernel-cache"
DEFAULT_MIOPEN_FIND_MODE = "FAST"


@dataclass(frozen=True)
class Task74HemmaSettings:
    """Canonical settings for running Task 74 on Hemma."""

    expected_revision: str
    service_url: str
    output_json: Path
    output_report: Path
    corpus_root: Path
    data_root: Path
    page_counts: str
    host_easyocr_cache_dir: Path
    smoke_output_root: Path
    two_worker_sweep: bool
    two_worker_chunk_sizes: str
    two_worker_gpu_stage_caps: str
    dirty_corpus_manifest: Path | None
    dirty_corpus_source_root: Path | None


@dataclass(frozen=True)
class VerifiedEnvContract:
    """Server-side env contract data required for the benchmark workflow."""

    api_key: str
    default_ocr_engine: str
    default_ocr_languages: tuple[str, ...]
    canonical_env_path: Path
    repo_env_link: Path


def _parse_args(argv: list[str]) -> Task74HemmaSettings:
    parser = argparse.ArgumentParser(description="Run the canonical Task 74 Hemma benchmark.")
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--page-counts", default="120,180,240")
    parser.add_argument(
        "--host-easyocr-cache-dir",
        type=Path,
        default=DEFAULT_HOST_EASYOCR_CACHE,
    )
    parser.add_argument("--smoke-output-root", type=Path)
    parser.add_argument("--two-worker-sweep", action="store_true")
    parser.add_argument("--two-worker-chunk-sizes", default="2,3,4,6,8")
    parser.add_argument("--two-worker-gpu-stage-caps", default="1,2")
    parser.add_argument(
        "--dirty-corpus-manifest",
        type=Path,
        help="Metadata-only dirty PDF OCR corpus manifest to embed in Task 74 evidence.",
    )
    parser.add_argument(
        "--dirty-corpus-source-root",
        type=Path,
        help="Private Hemma directory containing dirty PDFs whose hashes match the manifest.",
    )
    args = parser.parse_args(argv)
    output_json = (
        args.output_json
        if args.output_json is not None
        else (DEFAULT_SWEEP_OUTPUT_JSON if args.two_worker_sweep else DEFAULT_OUTPUT_JSON)
    )
    output_report = (
        args.output_report
        if args.output_report is not None
        else (DEFAULT_SWEEP_OUTPUT_REPORT if args.two_worker_sweep else DEFAULT_OUTPUT_REPORT)
    )
    corpus_root = (
        args.corpus_root
        if args.corpus_root is not None
        else (DEFAULT_SWEEP_CORPUS_ROOT if args.two_worker_sweep else DEFAULT_CORPUS_ROOT)
    )
    data_root = (
        args.data_root
        if args.data_root is not None
        else (DEFAULT_SWEEP_DATA_ROOT if args.two_worker_sweep else DEFAULT_DATA_ROOT)
    )
    smoke_output_root = args.smoke_output_root or Path(
        f"build/verification/task-76-hemma-deploy-verify/v2-smoke-{args.expected_revision[:7]}"
    )
    return Task74HemmaSettings(
        expected_revision=str(args.expected_revision),
        service_url=str(args.service_url),
        output_json=Path(output_json),
        output_report=Path(output_report),
        corpus_root=Path(corpus_root),
        data_root=Path(data_root),
        page_counts=str(args.page_counts),
        host_easyocr_cache_dir=Path(args.host_easyocr_cache_dir),
        smoke_output_root=Path(smoke_output_root),
        two_worker_sweep=bool(args.two_worker_sweep),
        two_worker_chunk_sizes=str(args.two_worker_chunk_sizes),
        two_worker_gpu_stage_caps=str(args.two_worker_gpu_stage_caps),
        dirty_corpus_manifest=args.dirty_corpus_manifest,
        dirty_corpus_source_root=args.dirty_corpus_source_root,
    )


def _redact(text: str, *, redactions: tuple[str, ...]) -> str:
    redacted = text
    for secret in redactions:
        if secret != "":
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


def _run_command(
    argv: list[str],
    *,
    label: str,
    cwd: Path = CANONICAL_REPO_ROOT,
    redactions: tuple[str, ...] = (),
    env_overrides: dict[str, str] | None = None,
) -> str:
    process_env = None
    if env_overrides is not None:
        process_env = {**os.environ, **env_overrides}
    result = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=process_env,
    )
    if result.returncode != 0:
        stdout = _redact(result.stdout.strip(), redactions=redactions)
        stderr = _redact(result.stderr.strip(), redactions=redactions)
        raise SystemExit(
            f"{label} failed with exit code {result.returncode}.\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
    return result.stdout


def _strip_optional_quotes(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1]
    return stripped


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _strip_optional_quotes(value)
    return values


def _verify_env_contract() -> VerifiedEnvContract:
    _run_command(
        ["bash", "scripts/devops/sync-prod-env-mirror.sh"],
        label="sync-prod-env-mirror",
    )

    if not CANONICAL_ENV_LINK.is_symlink():
        raise SystemExit(
            f"Expected `{CANONICAL_ENV_LINK}` to be a symlink to the canonical env file."
        )

    resolved_link = CANONICAL_ENV_LINK.resolve()
    if resolved_link != CANONICAL_ENV_PATH:
        raise SystemExit(
            f"Expected `{CANONICAL_ENV_LINK}` to resolve to `{CANONICAL_ENV_PATH}`, "
            f"got `{resolved_link}`."
        )

    if not CANONICAL_ENV_PATH.exists():
        raise SystemExit(f"Canonical env file is missing: `{CANONICAL_ENV_PATH}`.")

    env_values = _parse_env_file(CANONICAL_ENV_PATH)
    required_keys = (
        "SIR_CONVERT_A_LOT_V2_API_KEY",
        "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE",
        "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES",
        "SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR",
    )
    missing = [key for key in required_keys if env_values.get(key, "").strip() == ""]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(
            "Canonical Hemma env file is missing required Task 74 keys: "
            f"{joined}. Run `pdm run hemma-sync-prod-env-mirror` and repair the env."
        )

    default_languages = tuple(
        candidate.strip()
        for candidate in env_values["SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES"].split(",")
        if candidate.strip() != ""
    )
    if not default_languages:
        raise SystemExit("SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES must not be empty.")

    return VerifiedEnvContract(
        api_key=env_values["SIR_CONVERT_A_LOT_V2_API_KEY"],
        default_ocr_engine=env_values["SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE"],
        default_ocr_languages=default_languages,
        canonical_env_path=CANONICAL_ENV_PATH,
        repo_env_link=CANONICAL_ENV_LINK,
    )


def _sync_host_runtime() -> None:
    _run_command(
        ["pdm", "sync", "--prod", "--no-editable", "--no-self"],
        label="pdm sync --prod --no-editable --no-self",
    )


def _ensure_module_installed(module_name: str) -> None:
    if importlib.util.find_spec(module_name) is None:
        raise SystemExit(
            f"Required module `{module_name}` is missing from the Hemma host PDM runtime "
            "after `pdm sync`."
        )


def _warm_easyocr_cache(cache_dir: Path, *, languages: tuple[str, ...]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    easyocr_module = importlib.import_module("easyocr")
    reader_cls = getattr(easyocr_module, "Reader", None)
    if not callable(reader_cls):
        raise SystemExit("easyocr.Reader is unavailable in the Hemma host runtime.")
    reader_cls(
        list(languages),
        gpu=False,
        model_storage_directory=cache_dir.as_posix(),
        download_enabled=True,
        verbose=False,
    )


def _prepare_miopen_cache() -> dict[str, str]:
    """Create scratch-backed MIOpen cache roots and return process env overrides."""
    DEFAULT_MIOPEN_USER_DB_PATH.mkdir(parents=True, exist_ok=True)
    DEFAULT_MIOPEN_KERNEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "MIOPEN_FIND_MODE": DEFAULT_MIOPEN_FIND_MODE,
        "MIOPEN_USER_DB_PATH": DEFAULT_MIOPEN_USER_DB_PATH.as_posix(),
        "MIOPEN_CUSTOM_CACHE_DIR": DEFAULT_MIOPEN_KERNEL_CACHE_DIR.as_posix(),
    }


def _read_json_object(path: Path, *, label: str) -> dict[str, object]:
    payload_obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload_obj, dict):
        raise SystemExit(f"{label} at `{path}` is not a JSON object.")
    return payload_obj


def _require_string(payload: dict[str, object], *, key: str, label: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit(f"{label} is missing required string field `{key}`.")
    return value


def _verify_expected_revision(expected_revision: str) -> str:
    remote_revision = _run_command(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD").strip()
    if remote_revision != expected_revision:
        raise SystemExit(
            f"Remote repo HEAD `{remote_revision}` does not match expected revision "
            f"`{expected_revision}`."
        )
    return remote_revision


def _run_live_smoke(smoke_output_root: Path, *, api_key: str) -> dict[str, object]:
    _run_command(
        [
            "pdm",
            "run",
            "python",
            "-m",
            "scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions",
            "--lane",
            "host",
            "--api-key",
            api_key,
            "--output-root",
            smoke_output_root.as_posix(),
        ],
        label="verify_hemma_v2_conversions",
        redactions=(api_key,),
    )
    return _read_json_object(smoke_output_root / "readyz.json", label="Task 76 smoke readyz")


def _run_task74_benchmark(
    settings: Task74HemmaSettings,
    *,
    api_key: str,
    remote_revision: str,
    service_revision: str,
    default_ocr_engine: str,
    default_ocr_languages: tuple[str, ...],
) -> None:
    benchmark_args = [
        "pdm",
        "run",
        "benchmark:task-74",
        "--output-json",
        settings.output_json.as_posix(),
        "--output-report",
        settings.output_report.as_posix(),
        "--corpus-root",
        settings.corpus_root.as_posix(),
        "--data-root",
        settings.data_root.as_posix(),
        "--page-counts",
        settings.page_counts,
        "--api-key",
        api_key,
        "--gpu-available",
        "--ocr-mode",
        "force",
        "--ocr-engine",
        default_ocr_engine,
        "--ocr-languages",
        ",".join(default_ocr_languages),
        "--runtime-mode",
        "in_process_app",
        "--runtime-host",
        "hemma",
        "--runtime-service-url",
        settings.service_url,
        "--easyocr-model-storage-dir",
        settings.host_easyocr_cache_dir.as_posix(),
        "--parity-status",
        "passed",
        "--parity-lane",
        "host",
        "--parity-expected-revision",
        settings.expected_revision,
        "--parity-remote-revision",
        remote_revision,
        "--parity-service-revision",
        service_revision,
        "--parity-expected-remote-ok",
        "--parity-service-remote-ok",
        "--parity-live-smoke-passed",
        "--parity-metrics-scan-passed",
    ]
    if settings.two_worker_sweep:
        benchmark_args.extend(
            [
                "--two-worker-sweep",
                "--two-worker-chunk-sizes",
                settings.two_worker_chunk_sizes,
                "--two-worker-gpu-stage-caps",
                settings.two_worker_gpu_stage_caps,
            ]
        )
    if settings.dirty_corpus_manifest is not None:
        if settings.dirty_corpus_source_root is None:
            raise ValueError(
                "--dirty-corpus-manifest requires --dirty-corpus-source-root so "
                "executed private PDFs can be hash-verified."
            )
        benchmark_args.extend(
            [
                "--dirty-corpus-manifest",
                settings.dirty_corpus_manifest.as_posix(),
                "--dirty-corpus-source-root",
                settings.dirty_corpus_source_root.as_posix(),
            ]
        )
    _run_command(
        benchmark_args,
        label="benchmark:task-74",
        redactions=(api_key,),
        env_overrides=_prepare_miopen_cache(),
    )


def execute_workflow(settings: Task74HemmaSettings) -> dict[str, object]:
    """Run the canonical Task 74 Hemma workflow and return the benchmark payload."""
    env_contract = _verify_env_contract()
    remote_revision = _verify_expected_revision(settings.expected_revision)
    _sync_host_runtime()
    _ensure_module_installed("easyocr")
    _warm_easyocr_cache(
        settings.host_easyocr_cache_dir,
        languages=env_contract.default_ocr_languages,
    )

    readyz_payload = _run_live_smoke(settings.smoke_output_root, api_key=env_contract.api_key)
    service_revision = _require_string(
        readyz_payload,
        key="service_revision",
        label="Task 76 smoke readyz payload",
    )
    if service_revision != remote_revision:
        raise SystemExit(
            f"Service revision `{service_revision}` does not match remote revision "
            f"`{remote_revision}` after live smoke."
        )

    _run_task74_benchmark(
        settings,
        api_key=env_contract.api_key,
        remote_revision=remote_revision,
        service_revision=service_revision,
        default_ocr_engine=env_contract.default_ocr_engine,
        default_ocr_languages=env_contract.default_ocr_languages,
    )
    return _read_json_object(settings.output_json, label="Task 74 benchmark payload")


def _build_stdout_summary(
    *,
    settings: Task74HemmaSettings,
    payload: dict[str, object],
) -> dict[str, object]:
    runtime_parity_obj = payload.get("runtime_parity")
    if not isinstance(runtime_parity_obj, dict):
        raise SystemExit("Task 74 benchmark payload is missing `runtime_parity`.")
    dirty_corpus_obj = payload.get("dirty_corpus")
    dirty_corpus_loaded = dirty_corpus_obj is not None
    all_profiles_safe: object = None
    source_hashes_verified: object = None
    if isinstance(dirty_corpus_obj, dict):
        all_profiles_safe = dirty_corpus_obj.get("all_profiles_safe")
        manifest_obj = dirty_corpus_obj.get("manifest")
        if isinstance(manifest_obj, dict):
            source_hashes_verified = manifest_obj.get("source_hashes_verified")
    return {
        "output_json": settings.output_json.as_posix(),
        "output_report": settings.output_report.as_posix(),
        "runtime_parity_proven": runtime_parity_obj.get("parity_proven"),
        "dirty_corpus_manifest_loaded": dirty_corpus_loaded,
        "dirty_corpus_all_profiles_safe": all_profiles_safe,
        "dirty_corpus_source_hashes_verified": source_hashes_verified,
    }


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the workflow, and print a compact machine-readable summary."""
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    payload = execute_workflow(settings)
    print(json.dumps(_build_stdout_summary(settings=settings, payload=payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
