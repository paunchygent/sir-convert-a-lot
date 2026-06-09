"""Probe the native PaddleOCR/PaddleX AMD GPU container for formula recognition.

Purpose:
    Provide the governed Hemma-only Task 348 probe that inventories the
    official PaddleOCR-VL AMD GPU container and attempts formula-recognition
    inference only when the container exposes the required APIs.

Relationships:
    - Consumes an existing Task 346 rendered formula crop/page image.
    - Produces Task 348 runtime evidence under `build/verification/`.
    - Complements Task 347 by probing native AMD container support instead of
      the pip CUDA-wheel PaddlePaddle path.
"""

from __future__ import annotations

import argparse
import json
import platform
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

DEFAULT_IMAGE = (
    "ccr-2vdh3abv-pub.cnc.bj.baidubce.com/"
    "paddlepaddle/paddleocr-vl:latest-amd-gpu"
)
CONTAINER_INPUT_PATH = Path("/task348/input.png")
CONTAINER_OUTPUT_DIR = Path("/task348/output")
CONTAINER_PROBE_PATH = Path("/task348/output/task348_paddleocr_amd_inner_probe.py")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the native AMD PaddleOCR container probe."""
    args = build_parser().parse_args(argv)
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    probe_path = output_dir / "task348_paddleocr_amd_inner_probe.py"
    probe_path.write_text(render_inner_probe(), encoding="utf-8")
    command = build_docker_command(
        image=str(args.image),
        input_path=input_path,
        output_dir=output_dir,
        model_name=str(args.model_name),
        entrypoint_bash=bool(args.entrypoint_bash),
        inventory_only=bool(args.inventory_only),
        timeout_seconds=int(args.inner_timeout_seconds),
    )
    host_metadata = {
        "schema_version": "task348_paddleocr_amd_container_host_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "input_path": input_path.as_posix(),
        "output_dir": output_dir.as_posix(),
        "image": str(args.image),
        "model_name": str(args.model_name),
        "entrypoint_bash": bool(args.entrypoint_bash),
        "inventory_only": bool(args.inventory_only),
        "command": command,
    }
    (output_dir / "task348-paddleocr-amd-host-metadata.json").write_text(
        json.dumps(host_metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        command,
        check=False,
        text=True,
        timeout=float(args.host_timeout_seconds),
    )
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    """Build the Task 348 probe parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model-name", default="PP-FormulaNet_plus-M")
    parser.add_argument("--entrypoint-bash", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--inner-timeout-seconds", type=int, default=1800)
    parser.add_argument("--host-timeout-seconds", type=int, default=2400)
    return parser


def build_docker_command(
    *,
    image: str,
    input_path: Path,
    output_dir: Path,
    model_name: str,
    entrypoint_bash: bool,
    inventory_only: bool,
    timeout_seconds: int,
) -> list[str]:
    """Build the official/native AMD GPU Docker probe command."""
    inner_command = [
        "timeout",
        str(timeout_seconds),
        "python",
        CONTAINER_PROBE_PATH.as_posix(),
        "--input",
        CONTAINER_INPUT_PATH.as_posix(),
        "--output-dir",
        CONTAINER_OUTPUT_DIR.as_posix(),
        "--model-name",
        model_name,
    ]
    if inventory_only:
        inner_command.append("--inventory-only")
    command = [
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "--user",
        "root",
        "--device",
        "/dev:/dev",
        "--shm-size",
        "64g",
        "--network",
        "host",
        "-v",
        f"{input_path.as_posix()}:{CONTAINER_INPUT_PATH.as_posix()}:ro",
        "-v",
        f"{output_dir.as_posix()}:{CONTAINER_OUTPUT_DIR.as_posix()}",
    ]
    if entrypoint_bash:
        command.extend(["--entrypoint", "/bin/bash"])
    command.append(image)
    if not entrypoint_bash:
        command.append("bash")
    command.extend(["-lc", shlex.join(inner_command)])
    return command


def render_inner_probe() -> str:
    """Render the Python program executed inside the AMD GPU container."""
    return r'''"""Runtime inventory and formula-recognition probe inside PaddleOCR AMD image."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model-name", default="PP-FormulaNet_plus-M")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "schema_version": "task348_paddleocr_amd_container_inner_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "hostname": platform.node(),
        "python": platform.python_version(),
        "input": args.input.as_posix(),
        "model_name": args.model_name,
        "runtime": {},
        "imports": {},
        "formula_api": {},
        "formula_smoke": {"status": "not_attempted"},
    }
    paddle = try_import("paddle", payload["imports"])
    paddleocr = try_import("paddleocr", payload["imports"])
    paddlex = try_import("paddlex", payload["imports"])
    if paddle is not None:
        payload["runtime"] = collect_paddle_runtime(paddle)
    payload["formula_api"] = inspect_formula_api(paddleocr)
    write_payload(args.output_dir, payload)
    if args.inventory_only:
        payload["elapsed_ms"] = max(0, int((time.monotonic() - started) * 1000))
        write_payload(args.output_dir, payload)
        return 0
    if paddleocr is not None and formula_api_available(payload["formula_api"]):
        payload["formula_smoke"] = run_formula_smoke(
            paddleocr=paddleocr,
            input_path=args.input,
            output_dir=args.output_dir,
            model_name=args.model_name,
        )
    payload["elapsed_ms"] = max(0, int((time.monotonic() - started) * 1000))
    write_payload(args.output_dir, payload)
    return 0


def write_payload(output_dir: Path, payload: dict[str, object]) -> None:
    (output_dir / "task348-paddleocr-amd-probe.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def try_import(module_name: str, imports: object) -> object | None:
    imports_map = imports if isinstance(imports, dict) else {}
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        imports_map[module_name] = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        return None
    imports_map[module_name] = {
        "status": "succeeded",
        "version": getattr(module, "__version__", None),
    }
    return module


def collect_paddle_runtime(paddle: object) -> dict[str, object]:
    runtime: dict[str, object] = {"version": getattr(paddle, "__version__", None)}
    device = getattr(paddle, "device", None)
    if device is None:
        return runtime
    for name in (
        "is_compiled_with_rocm",
        "is_compiled_with_cuda",
        "get_device",
        "get_all_custom_device_type",
    ):
        attr = getattr(device, name, None)
        if callable(attr):
            try:
                runtime[name] = attr()
            except Exception as exc:
                runtime[name] = f"{type(exc).__name__}: {exc}"
    return runtime


def inspect_formula_api(paddleocr: object | None) -> dict[str, object]:
    api = {
        "FormulaRecognition": False,
        "FormulaRecognitionPipeline": False,
        "candidate_models": [
            "PP-FormulaNet_plus-M",
            "PP-FormulaNet_plus-S",
            "UniMERNet",
        ],
    }
    if paddleocr is None:
        return api
    api["FormulaRecognition"] = hasattr(paddleocr, "FormulaRecognition")
    api["FormulaRecognitionPipeline"] = hasattr(paddleocr, "FormulaRecognitionPipeline")
    api["paddleocr_public_names_sample"] = sorted(
        name for name in dir(paddleocr) if "Formula" in name or "formula" in name
    )[:50]
    return api


def formula_api_available(api: object) -> bool:
    return isinstance(api, dict) and bool(
        api.get("FormulaRecognition") or api.get("FormulaRecognitionPipeline")
    )


def run_formula_smoke(
    *,
    paddleocr: object,
    input_path: Path,
    output_dir: Path,
    model_name: str,
) -> dict[str, object]:
    started = time.monotonic()
    try:
        runner = "FormulaRecognition"
        model_cls = getattr(paddleocr, "FormulaRecognition", None)
        if model_cls is not None:
            model = model_cls(model_name=model_name, device="gpu")
            output = model.predict(input=input_path.as_posix(), batch_size=1)
        else:
            runner = "FormulaRecognitionPipeline"
            pipeline_cls = getattr(paddleocr, "FormulaRecognitionPipeline")
            pipeline = pipeline_cls(
                formula_recognition_model_name=model_name,
                device="gpu",
            )
            output = pipeline.predict(input_path.as_posix())
        records = []
        for index, result in enumerate(output):
            result_json_path = output_dir / f"formula-result-{index}.json"
            try:
                result.save_to_json(save_path=result_json_path.as_posix())
            except TypeError:
                result.save_to_json(save_path=output_dir.as_posix())
            try:
                result.save_to_img(save_path=output_dir.as_posix())
            except Exception:
                pass
            records.append({"index": index, "text": str(result)[:2000]})
        return {
            "status": "succeeded",
            "runner": runner,
            "model_name": model_name,
            "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
            "records": records,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "runner": locals().get("runner", "not_selected"),
            "model_name": model_name,
            "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback_tail": traceback.format_exc()[-4000:],
        }


if __name__ == "__main__":
    raise SystemExit(main())
'''


if __name__ == "__main__":
    raise SystemExit(main())
