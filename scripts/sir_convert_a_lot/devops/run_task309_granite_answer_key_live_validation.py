"""Task 309 Granite answer-key live-validation runner.

Purpose:
    Provide the committed command surface for preparing and inspecting Task 309
    live-validation artifacts before long Hemma Granite/vLLM runs are launched.

Relationships:
    - Uses `domain.digiexam_answer_key_live_validation_manifest` for the
      versioned DigiExam DXE corpus manifest and expected-answer worklist.
    - Complements the Hemma detached command and resource-monitor surfaces used
      by `docs/runbooks/runbook-hemma-devops-and-gpu.md`.
    - Feeds Task 309 reports retained under `build/verification/` or the
      scratch-backed Hemma verification root.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_CACHE_PATHS,
    DEFAULT_PROVIDER_CONTAINER_NAME,
    DEFAULT_PROVIDER_HOST_CACHE,
    DEFAULT_PROVIDER_IMAGE,
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_PORT,
    Task309HemmaPreflight,
    Task309LlamaProviderLaunchResult,
    Task309ProviderLaunchResult,
    Task309ProviderStatus,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_launch import (
    build_task309_provider_launch_plan,
    launch_task309_provider,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_reporting import (
    write_task309_hemma_preflight_artifacts,
    write_task309_llama_provider_launch_artifacts,
    write_task309_provider_launch_artifacts,
    write_task309_provider_status_artifacts,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_status import (
    build_task309_hemma_preflight,
    build_task309_provider_status,
)
from scripts.sir_convert_a_lot.devops.task309_live_evaluation import (
    evaluate_task309_advisory_reports,
    write_task309_advisory_evaluation,
)
from scripts.sir_convert_a_lot.devops.task309_live_execution import (
    Task309AdvisoryCorpusRunReport,
    run_task309_advisory_corpus,
)
from scripts.sir_convert_a_lot.devops.task309_live_microprobes import (
    Task309MicroprobeReport,
    run_task309_microprobes,
)
from scripts.sir_convert_a_lot.devops.task309_llama_provider_launch import (
    build_task309_llama_provider_launch_plan,
    launch_task309_llama_provider,
    qwen36_llama_required_process_args,
)
from scripts.sir_convert_a_lot.devops.task309_request_shape_preview import (
    Task309RequestShapePreview,
    build_task309_request_shape_preview,
    write_task309_request_shape_preview,
)
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    QWEN36_LLAMA_CPP_CACHE_PATH,
    QWEN36_LLAMA_CPP_HF_FILE,
    QWEN36_LLAMA_CPP_HF_REPO,
    QWEN36_LLAMA_CPP_SERVER_BINARY,
    Task309ProviderDefaults,
    Task309ProviderProfileName,
    parse_task309_provider_runtime,
    task309_defaults_for_provider_profile,
    task309_provider_profile_values,
    task309_provider_runtime_values,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_goldens import (
    Task309GoldenValidationReport,
    validate_task309_expected_answer_manifest,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    build_task309_expected_answer_worklist,
    build_task309_live_validation_manifest,
    write_task309_json,
)

DEFAULT_CORPUS_ROOT = Path("inputs/examples/digiexam-dxe-fixtures/2026-05-12-onedrive-pure-dxe")
DEFAULT_OUTPUT_ROOT = Path("build/verification/task-309-granite-answer-key-live")
DEFAULT_SOURCE_ROOT_HINT = DEFAULT_CORPUS_ROOT.as_posix()
DEFAULT_EXPECTED_ANSWER_MANIFEST = DEFAULT_CORPUS_ROOT / "expected-answer-manifest.json"
DEFAULT_VALIDATION_CORPUS_MANIFEST = DEFAULT_CORPUS_ROOT / "validation-corpus-manifest.json"
DEFAULT_CORPUS_REPORTS_ROOT = DEFAULT_OUTPUT_ROOT / "advisory-corpus-reports"


def main(argv: list[str] | None = None) -> int:
    """Run the Task 309 operator CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    _apply_provider_defaults(args)
    if args.command == "prepare-manifests":
        _prepare_manifests(
            corpus_root=args.corpus_root,
            output_root=args.output_root,
            source_root_hint=args.source_root_hint,
        )
        return 0
    if args.command == "status":
        _status(output_root=args.output_root)
        return 0
    if args.command == "validate-goldens":
        report = _validate_goldens(
            corpus_root=args.corpus_root,
            expected_answer_manifest=args.expected_answer_manifest,
            output_root=args.output_root,
        )
        return _blocked_exit_code(report.summary.valid, fail_on_blocked=args.fail_on_blocked)
    if args.command == "preview-request-shape":
        preview = build_task309_request_shape_preview(
            corpus_root=args.corpus_root,
            provider_url=args.provider_url,
            model=args.model,
            provider_runtime=parse_task309_provider_runtime(args.provider_runtime),
            supports_multimodal_vision=_supports_multimodal_vision(args),
            vision_media_path=args.output_root / "vision-assets",
        )
        _write_request_shape_preview(output_root=args.output_root, preview=preview)
        return _blocked_exit_code(preview.ok, fail_on_blocked=args.fail_on_blocked)
    if args.command == "launch-provider":
        provider_launch_result = _launch_provider(
            output_root=args.output_root,
            container_name=args.container_name,
            image=args.image,
            model=args.model,
            port=args.port,
            host_cache_path=args.host_cache_path,
            execute=args.execute,
        )
        return _blocked_exit_code(provider_launch_result.ok, fail_on_blocked=args.fail_on_blocked)
    if args.command == "launch-llama-provider":
        _require_hemma_server("launch-llama-provider")
        llama_launch_result = _launch_llama_provider(
            output_root=args.output_root,
            provider_profile=args.provider_profile,
            provider_url=args.provider_url,
            model=args.model,
            port=args.port,
            server_binary=args.server_binary,
            hf_repo=args.hf_repo,
            hf_file=args.hf_file,
            llama_cache_path=args.llama_cache_path,
            execute=args.execute,
        )
        return _blocked_exit_code(llama_launch_result.ok, fail_on_blocked=args.fail_on_blocked)
    if args.command == "provider-status":
        status = build_task309_provider_status(
            provider_url=args.provider_url,
            container_name=args.container_name,
            port=args.port,
            timeout_seconds=args.timeout_seconds,
            expected_model_id=_expected_model_id(args),
            required_process_args=_required_process_args(args),
        )
        _write_provider_status(output_root=args.output_root, status=status)
        return _blocked_exit_code(status.ready, fail_on_blocked=args.fail_on_blocked)
    if args.command == "hemma-preflight":
        cache_paths = tuple(args.cache_path or DEFAULT_CACHE_PATHS)
        preflight = build_task309_hemma_preflight(
            manifest_path=args.manifest_path,
            provider_url=args.provider_url,
            container_name=args.container_name,
            port=args.port,
            cache_paths=cache_paths,
            timeout_seconds=args.timeout_seconds,
            expected_model_id=_expected_model_id(args),
            required_process_args=_required_process_args(args),
        )
        _write_hemma_preflight(output_root=args.output_root, preflight=preflight)
        return _blocked_exit_code(preflight.ready, fail_on_blocked=args.fail_on_blocked)
    if args.command == "microprobes":
        microprobe_report = run_task309_microprobes(
            provider_url=args.provider_url,
            model=args.model,
            provider_runtime=parse_task309_provider_runtime(args.provider_runtime),
            supports_multimodal_vision=_supports_multimodal_vision(args),
            require_provider_ready=not args.skip_provider_ready_check,
            timeout_seconds=args.timeout_seconds,
            vision_media_path=args.output_root / "vision-assets",
        )
        _write_microprobes(output_root=args.output_root, report=microprobe_report)
        return _blocked_exit_code(
            not microprobe_report.blocked,
            fail_on_blocked=args.fail_on_blocked,
        )
    if args.command == "run-advisory-corpus":
        reports_root = args.reports_root or (args.output_root / "advisory-corpus-reports")
        corpus_report = run_task309_advisory_corpus(
            corpus_root=args.corpus_root,
            reports_root=reports_root,
            provider_url=args.provider_url,
            model=args.model,
            provider_runtime=parse_task309_provider_runtime(args.provider_runtime),
            supports_multimodal_vision=_supports_multimodal_vision(args),
            vision_media_path=args.output_root / "vision-assets",
            require_provider_ready=not args.skip_provider_ready_check,
            timeout_seconds=args.timeout_seconds,
        )
        _write_advisory_corpus(output_root=args.output_root, report=corpus_report)
        return _blocked_exit_code(
            not corpus_report.blocked,
            fail_on_blocked=args.fail_on_blocked,
        )
    if args.command == "evaluate-advisory-corpus":
        reports_root = args.reports_root or (args.output_root / "advisory-corpus-reports")
        evaluation = evaluate_task309_advisory_reports(
            expected_answer_manifest_path=args.expected_answer_manifest,
            reports_root=reports_root,
        )
        json_path, markdown_path = write_task309_advisory_evaluation(
            output_root=args.output_root,
            report=evaluation,
        )
        print(f"Wrote {json_path}")
        print(f"Wrote {markdown_path}")
        return _blocked_exit_code(
            evaluation.wrong_but_valid_count == 0
            and evaluation.unknown_id_count == 0
            and evaluation.duplicate_id_count == 0
            and evaluation.malformed_success_count == 0,
            fail_on_blocked=args.fail_on_blocked,
        )
    raise SystemExit(f"Unsupported Task 309 command: {args.command}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and inspect Task 309 live-validation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare-manifests",
        help="Build the Task 309 corpus manifest and expected-answer worklist.",
    )
    prepare.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--source-root-hint", default=DEFAULT_SOURCE_ROOT_HINT)

    status = subparsers.add_parser("status", help="Inspect prepared Task 309 manifests.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)

    goldens = subparsers.add_parser(
        "validate-goldens",
        help="Validate the teacher-verified expected-answer manifest.",
    )
    goldens.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    goldens.add_argument(
        "--expected-answer-manifest",
        type=Path,
        default=DEFAULT_EXPECTED_ANSWER_MANIFEST,
    )
    _add_provider_profile_arg(goldens)
    goldens.add_argument("--output-root", type=Path, default=None)
    goldens.add_argument("--fail-on-blocked", action="store_true")

    preview = subparsers.add_parser(
        "preview-request-shape",
        help="Preview model-facing request shape without calling the provider.",
    )
    _add_provider_args(preview)
    preview.add_argument("--model", default=None)
    _add_provider_runtime_arg(preview)
    preview.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    preview.add_argument("--output-root", type=Path, default=None)
    preview.add_argument("--fail-on-blocked", action="store_true")

    launch = subparsers.add_parser(
        "launch-provider",
        help="Launch or dry-run the persistent Granite/vLLM provider container.",
    )
    launch.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    launch.add_argument("--container-name", default=DEFAULT_PROVIDER_CONTAINER_NAME)
    launch.add_argument("--image", default=DEFAULT_PROVIDER_IMAGE)
    launch.add_argument("--model", default=DEFAULT_PROVIDER_MODEL)
    launch.add_argument("--port", type=int, default=DEFAULT_PROVIDER_PORT)
    launch.add_argument("--host-cache-path", default=DEFAULT_PROVIDER_HOST_CACHE)
    launch.add_argument("--execute", action="store_true")
    launch.add_argument("--fail-on-blocked", action="store_true")

    llama_launch = subparsers.add_parser(
        "launch-llama-provider",
        help="Launch or dry-run the persistent Hemma-local llama.cpp provider.",
    )
    _add_provider_args(llama_launch)
    llama_launch.set_defaults(provider_profile=Task309ProviderProfileName.QWEN36_LLAMA_CPP.value)
    llama_launch.add_argument("--model", default=None)
    llama_launch.add_argument("--output-root", type=Path, default=None)
    llama_launch.add_argument("--server-binary", default=QWEN36_LLAMA_CPP_SERVER_BINARY)
    llama_launch.add_argument("--hf-repo", default=QWEN36_LLAMA_CPP_HF_REPO)
    llama_launch.add_argument("--hf-file", default=QWEN36_LLAMA_CPP_HF_FILE)
    llama_launch.add_argument("--llama-cache-path", default=QWEN36_LLAMA_CPP_CACHE_PATH)
    llama_launch.add_argument("--execute", action="store_true")
    llama_launch.add_argument("--fail-on-blocked", action="store_true")

    provider = subparsers.add_parser(
        "provider-status",
        help="Write persistent Granite/vLLM provider status without stopping it.",
    )
    _add_provider_args(provider)
    provider.add_argument("--output-root", type=Path, default=None)
    provider.add_argument("--fail-on-blocked", action="store_true")

    preflight = subparsers.add_parser(
        "hemma-preflight",
        help="Write Hemma GPU/cache/provider preflight evidence for Task 309.",
    )
    _add_provider_args(preflight)
    preflight.add_argument("--manifest-path", type=Path, default=DEFAULT_VALIDATION_CORPUS_MANIFEST)
    preflight.add_argument("--output-root", type=Path, default=None)
    preflight.add_argument(
        "--cache-path",
        action="append",
        help="Hemma cache path to require. Defaults to the runbook cache roots.",
    )
    preflight.add_argument("--fail-on-blocked", action="store_true")

    microprobes = subparsers.add_parser(
        "microprobes",
        help="Run Task 309 provider microprobes and retain redacted reports.",
    )
    _add_provider_args(microprobes)
    microprobes.add_argument("--model", default=None)
    _add_provider_runtime_arg(microprobes)
    microprobes.add_argument("--output-root", type=Path, default=None)
    microprobes.add_argument("--skip-provider-ready-check", action="store_true")
    microprobes.add_argument("--fail-on-blocked", action="store_true")

    corpus = subparsers.add_parser(
        "run-advisory-corpus",
        help="Run the in-process advisory path over the Task 309 DXE corpus.",
    )
    _add_provider_args(corpus)
    corpus.add_argument("--model", default=None)
    _add_provider_runtime_arg(corpus)
    corpus.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    corpus.add_argument("--output-root", type=Path, default=None)
    corpus.add_argument("--reports-root", type=Path, default=None)
    corpus.add_argument("--skip-provider-ready-check", action="store_true")
    corpus.add_argument("--fail-on-blocked", action="store_true")

    evaluate = subparsers.add_parser(
        "evaluate-advisory-corpus",
        help="Evaluate retained Task 309 advisory reports against teacher goldens.",
    )
    evaluate.add_argument(
        "--expected-answer-manifest",
        type=Path,
        default=DEFAULT_EXPECTED_ANSWER_MANIFEST,
    )
    _add_provider_profile_arg(evaluate)
    evaluate.add_argument("--output-root", type=Path, default=None)
    evaluate.add_argument("--reports-root", type=Path, default=None)
    evaluate.add_argument("--fail-on-blocked", action="store_true")

    return parser


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    _add_provider_profile_arg(parser)
    parser.add_argument("--provider-url", default=None)
    parser.add_argument("--container-name", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)


def _add_provider_runtime_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider-runtime",
        choices=task309_provider_runtime_values(),
        default=None,
        help=(
            "Structured provider runtime. llama.cpp runtimes are restricted to "
            "JSON Schema response_format or GBNF grammar-constrained JSON."
        ),
    )


def _add_provider_profile_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider-profile",
        choices=task309_provider_profile_values(),
        default=Task309ProviderProfileName.GRANITE_VLLM.value,
        help="Named provider defaults to apply before explicit CLI overrides.",
    )


def _apply_provider_defaults(args: argparse.Namespace) -> None:
    defaults = _provider_defaults(args)
    _set_default(args, "provider_url", defaults.provider_url)
    _set_default(args, "container_name", defaults.container_name)
    _set_default(args, "port", defaults.port)
    _set_default(args, "model", defaults.model)
    _set_default(args, "provider_runtime", defaults.provider_runtime.value)
    _set_default(args, "output_root", defaults.output_root)
    if hasattr(args, "reports_root") and args.reports_root is None:
        args.reports_root = defaults.reports_root


def _provider_defaults(args: argparse.Namespace) -> Task309ProviderDefaults:
    profile = getattr(args, "provider_profile", Task309ProviderProfileName.GRANITE_VLLM.value)
    return task309_defaults_for_provider_profile(profile)


def _set_default(args: argparse.Namespace, name: str, value: object) -> None:
    if hasattr(args, name) and getattr(args, name) is None:
        setattr(args, name, value)


def _expected_model_id(args: argparse.Namespace) -> str | None:
    defaults = _provider_defaults(args)
    return defaults.expected_model_id


def _required_process_args(args: argparse.Namespace) -> tuple[str, ...]:
    defaults = _provider_defaults(args)
    if defaults.profile_name == Task309ProviderProfileName.QWEN36_LLAMA_CPP:
        return qwen36_llama_required_process_args()
    return ()


def _supports_multimodal_vision(args: argparse.Namespace) -> bool:
    return _provider_defaults(args).permits_vision_assets


def _prepare_manifests(
    *,
    corpus_root: Path,
    output_root: Path,
    source_root_hint: str,
) -> None:
    manifest = build_task309_live_validation_manifest(
        corpus_root,
        source_root_hint=source_root_hint,
    )
    worklist = build_task309_expected_answer_worklist(manifest)
    manifest_path = output_root / "validation-corpus-manifest.json"
    worklist_path = output_root / "expected-answer-worklist.json"
    enforce_generated_output_path(manifest_path, label=manifest_path.name)
    enforce_generated_output_path(worklist_path, label=worklist_path.name)
    write_task309_json(manifest.to_payload(), manifest_path)
    write_task309_json(worklist.to_payload(), worklist_path)
    print(f"Wrote {manifest_path}")
    print(f"Wrote {worklist_path}")
    print(f"Eligible items: {manifest.summary.eligible_item_count}")


def _status(*, output_root: Path) -> None:
    manifest_path = output_root / "validation-corpus-manifest.json"
    worklist_path = output_root / "expected-answer-worklist.json"
    if not manifest_path.exists():
        raise SystemExit(f"Task 309 manifest is missing: {manifest_path}")
    manifest_payload = _load_object(manifest_path)
    summary = manifest_payload.get("summary")
    if not isinstance(summary, dict):
        raise SystemExit(f"Task 309 manifest summary is malformed: {manifest_path}")
    print(f"Manifest: {manifest_path}")
    print(f"Expected-answer worklist: {worklist_path}")
    print(f"Files: {summary.get('file_count')}")
    print(f"Items: {summary.get('item_count')}")
    print(f"Eligible items: {summary.get('eligible_item_count')}")
    expected_answer_manifest_path = output_root / "expected-answer-manifest.json"
    if expected_answer_manifest_path.exists():
        print(f"Expected-answer manifest: {expected_answer_manifest_path}")


def _validate_goldens(
    *,
    corpus_root: Path,
    expected_answer_manifest: Path,
    output_root: Path,
) -> Task309GoldenValidationReport:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    report = validate_task309_expected_answer_manifest(
        corpus_root=corpus_root,
        expected_answer_manifest_path=expected_answer_manifest,
    )
    json_path = output_root / "expected-answer-validation.json"
    markdown_path = output_root / "expected-answer-validation.md"
    write_task309_json(report.to_payload(), json_path)
    _write_markdown(markdown_path, _golden_validation_markdown(report))
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    print(f"Valid goldens: {report.summary.valid}")
    print(f"Validated items: {report.summary.validated_item_count}")
    print(f"Issues: {report.summary.issue_count}")
    return report


def _launch_provider(
    *,
    output_root: Path,
    container_name: str,
    image: str,
    model: str,
    port: int,
    host_cache_path: str,
    execute: bool,
) -> Task309ProviderLaunchResult:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    plan = build_task309_provider_launch_plan(
        container_name=container_name,
        image=image,
        model=model,
        host_port=port,
        host_cache_path=host_cache_path,
        dry_run=not execute,
    )
    result = launch_task309_provider(plan)
    json_path, markdown_path = write_task309_provider_launch_artifacts(
        output_root=output_root,
        result=result,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return result


def _launch_llama_provider(
    *,
    output_root: Path,
    provider_profile: str,
    provider_url: str,
    model: str,
    port: int,
    server_binary: str,
    hf_repo: str,
    hf_file: str,
    llama_cache_path: str,
    execute: bool,
) -> Task309LlamaProviderLaunchResult:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    plan = build_task309_llama_provider_launch_plan(
        provider_profile=Task309ProviderProfileName(provider_profile),
        provider_url=provider_url,
        model=model,
        port=port,
        output_root=output_root,
        server_binary=server_binary,
        hf_repo=hf_repo,
        hf_file=hf_file,
        llama_cache_path=llama_cache_path,
        dry_run=not execute,
    )
    result = launch_task309_llama_provider(plan)
    json_path, markdown_path = write_task309_llama_provider_launch_artifacts(
        output_root=output_root,
        result=result,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    return result


def _write_provider_status(*, output_root: Path, status: Task309ProviderStatus) -> None:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = write_task309_provider_status_artifacts(
        output_root=output_root,
        status=status,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _write_hemma_preflight(*, output_root: Path, preflight: Task309HemmaPreflight) -> None:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = write_task309_hemma_preflight_artifacts(
        output_root=output_root,
        preflight=preflight,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _write_microprobes(*, output_root: Path, report: Task309MicroprobeReport) -> None:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "provider-microprobes.json"
    markdown_path = output_root / "provider-microprobes.md"
    write_task309_json(report.to_payload(), json_path)
    _write_markdown(markdown_path, _microprobe_markdown(report))
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _write_advisory_corpus(
    *,
    output_root: Path,
    report: Task309AdvisoryCorpusRunReport,
) -> None:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "in-process-advisory-corpus-run.json"
    markdown_path = output_root / "in-process-advisory-corpus-run.md"
    write_task309_json(report.to_payload(), json_path)
    _write_markdown(markdown_path, _advisory_corpus_markdown(report))
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _write_request_shape_preview(
    *,
    output_root: Path,
    preview: Task309RequestShapePreview,
) -> None:
    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = write_task309_request_shape_preview(
        output_root=output_root,
        preview=preview,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


def _golden_validation_markdown(report: Task309GoldenValidationReport) -> str:
    lines = [
        "# Task 309 Expected-Answer Validation",
        "",
        f"- corpus_id: `{report.corpus_id}`",
        f"- expected_answer_manifest_path: `{report.expected_answer_manifest_path}`",
        f"- source_manifest_sha256: `{report.source_manifest_sha256}`",
        f"- expected_answer_manifest_sha256: `{report.expected_answer_manifest_sha256}`",
        f"- valid: `{report.summary.valid}`",
        f"- eligible_item_count: `{report.summary.eligible_item_count}`",
        f"- entry_count: `{report.summary.entry_count}`",
        f"- validated_item_count: `{report.summary.validated_item_count}`",
        f"- issue_count: `{report.summary.issue_count}`",
        f"- adjudication_required_count: `{report.summary.adjudication_required_count}`",
    ]
    if report.issues:
        lines.extend(["", "## Issues"])
        for issue in report.issues:
            lines.append(
                f"- `{issue.code}` {issue.source_filename or '-'} "
                f"{issue.item_id or '-'}: {issue.detail}"
            )
    return "\n".join(lines)


def _microprobe_markdown(report: Task309MicroprobeReport) -> str:
    lines = [
        "# Task 309 Provider Microprobes",
        "",
        f"- provider_url: `{report.provider_url}`",
        f"- model: `{report.model}`",
        f"- provider_runtime: `{report.provider_runtime}`",
        f"- provider_ready: `{report.provider_ready}`",
        f"- blocked: `{report.blocked}`",
        f"- result_count: `{len(report.results)}`",
    ]
    if report.results:
        lines.extend(["", "## Results"])
    for result in report.results:
        lines.append(
            f"- `{result.probe_id}` mode=`{result.output_mode}` ok=`{result.ok}` "
            f"latency_ms=`{result.latency_ms}` failure=`{result.failure_code}`"
        )
    return "\n".join(lines)


def _advisory_corpus_markdown(report: Task309AdvisoryCorpusRunReport) -> str:
    lines = [
        "# Task 309 In-Process Advisory Corpus Run",
        "",
        f"- provider_url: `{report.provider_url}`",
        f"- model: `{report.model}`",
        f"- provider_runtime: `{report.provider_runtime}`",
        f"- corpus_root: `{report.corpus_root}`",
        f"- provider_ready: `{report.provider_ready}`",
        f"- blocked: `{report.blocked}`",
        f"- file_count: `{report.file_count}`",
        f"- item_count: `{report.item_count}`",
        f"- eligible_item_count: `{report.eligible_item_count}`",
        f"- suggested_count: `{report.suggested_count}`",
        f"- manual_follow_up_count: `{report.manual_follow_up_count}`",
        f"- skipped_count: `{report.skipped_count}`",
        f"- asset_eligible_count: `{report.asset_eligible_count}`",
        f"- multimodal_request_count: `{report.multimodal_request_count}`",
        f"- total_latency_ms: `{report.total_latency_ms}`",
        f"- retained_report_count: `{len(report.report_paths)}`",
    ]
    if report.backend_failure_counts:
        lines.extend(["", "## Backend Failures"])
        for count in report.backend_failure_counts:
            lines.append(f"- `{count.get('key')}`: `{count.get('count')}`")
    return "\n".join(lines)


def _write_markdown(path: Path, markdown: str) -> None:
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _blocked_exit_code(ready: bool, *, fail_on_blocked: bool) -> int:
    if ready or not fail_on_blocked:
        return 0
    return 2


def _require_hemma_server(label: str) -> None:
    required_hostname = os.environ.get(
        "SIR_CONVERT_A_LOT_HEMMA_LOCAL_HOSTNAME", "paunchygent-server"
    )
    required_root = Path(
        os.environ.get(
            "SIR_CONVERT_A_LOT_HEMMA_ROOT",
            "/home/paunchygent/apps/sir-convert-a-lot",
        )
    ).resolve()
    required_skill_repository = Path(
        os.environ.get(
            "SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY",
            "/home/paunchygent/apps/skill-repository",
        )
    ).resolve()
    current_hostname = os.environ.get("SIR_CONVERT_A_LOT_CURRENT_HOSTNAME") or socket.gethostname()
    current_root = Path.cwd().resolve()
    current_skill_repository = _current_skill_repository()
    if (
        current_hostname == required_hostname
        and current_root == required_root
        and current_skill_repository == required_skill_repository
    ):
        return
    message = "\n".join(
        (
            f"{label}: this command is Hemma Server-only.",
            f"  hostname: {current_hostname}",
            f"  repo root: {current_root}",
            f"  skill repository: {current_skill_repository}",
            "",
            "Use: pdm run run-hemma -- <command> [args...]",
        )
    )
    raise SystemExit(message)


def _current_skill_repository() -> Path:
    override = os.environ.get("SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY")
    if override:
        return Path(override).resolve()
    return (Path.home() / ".codex" / "skill-repository").resolve()


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Task 309 JSON artifact must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


if __name__ == "__main__":
    raise SystemExit(main())
