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
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_CACHE_PATHS,
    DEFAULT_PROVIDER_CONTAINER_NAME,
    DEFAULT_PROVIDER_HOST_CACHE,
    DEFAULT_PROVIDER_IMAGE,
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_PORT,
    DEFAULT_PROVIDER_URL,
    Task309HemmaPreflight,
    Task309ProviderLaunchResult,
    Task309ProviderStatus,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_launch import (
    build_task309_provider_launch_plan,
    launch_task309_provider,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_reporting import (
    write_task309_hemma_preflight_artifacts,
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
from scripts.sir_convert_a_lot.devops.task309_request_shape_preview import (
    Task309RequestShapePreview,
    build_task309_request_shape_preview,
    write_task309_request_shape_preview,
)
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    DEFAULT_TASK309_PROVIDER_RUNTIME,
    parse_task309_provider_runtime,
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
        )
        _write_request_shape_preview(output_root=args.output_root, preview=preview)
        return _blocked_exit_code(preview.ok, fail_on_blocked=args.fail_on_blocked)
    if args.command == "launch-provider":
        result = _launch_provider(
            output_root=args.output_root,
            container_name=args.container_name,
            image=args.image,
            model=args.model,
            port=args.port,
            host_cache_path=args.host_cache_path,
            execute=args.execute,
        )
        return _blocked_exit_code(result.ok, fail_on_blocked=args.fail_on_blocked)
    if args.command == "provider-status":
        status = build_task309_provider_status(
            provider_url=args.provider_url,
            container_name=args.container_name,
            port=args.port,
            timeout_seconds=args.timeout_seconds,
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
        )
        _write_hemma_preflight(output_root=args.output_root, preflight=preflight)
        return _blocked_exit_code(preflight.ready, fail_on_blocked=args.fail_on_blocked)
    if args.command == "microprobes":
        microprobe_report = run_task309_microprobes(
            provider_url=args.provider_url,
            model=args.model,
            provider_runtime=parse_task309_provider_runtime(args.provider_runtime),
            require_provider_ready=not args.skip_provider_ready_check,
            timeout_seconds=args.timeout_seconds,
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
    goldens.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    goldens.add_argument("--fail-on-blocked", action="store_true")

    preview = subparsers.add_parser(
        "preview-request-shape",
        help="Preview model-facing request shape without calling the provider.",
    )
    _add_provider_args(preview)
    preview.add_argument("--model", default=DEFAULT_PROVIDER_MODEL)
    _add_provider_runtime_arg(preview)
    preview.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    preview.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
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

    provider = subparsers.add_parser(
        "provider-status",
        help="Write persistent Granite/vLLM provider status without stopping it.",
    )
    _add_provider_args(provider)
    provider.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    provider.add_argument("--fail-on-blocked", action="store_true")

    preflight = subparsers.add_parser(
        "hemma-preflight",
        help="Write Hemma GPU/cache/provider preflight evidence for Task 309.",
    )
    _add_provider_args(preflight)
    preflight.add_argument("--manifest-path", type=Path, default=DEFAULT_VALIDATION_CORPUS_MANIFEST)
    preflight.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
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
    microprobes.add_argument("--model", default=DEFAULT_PROVIDER_MODEL)
    _add_provider_runtime_arg(microprobes)
    microprobes.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    microprobes.add_argument("--skip-provider-ready-check", action="store_true")
    microprobes.add_argument("--fail-on-blocked", action="store_true")

    corpus = subparsers.add_parser(
        "run-advisory-corpus",
        help="Run the in-process advisory path over the Task 309 DXE corpus.",
    )
    _add_provider_args(corpus)
    corpus.add_argument("--model", default=DEFAULT_PROVIDER_MODEL)
    _add_provider_runtime_arg(corpus)
    corpus.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    corpus.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
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
    evaluate.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    evaluate.add_argument("--reports-root", type=Path, default=None)
    evaluate.add_argument("--fail-on-blocked", action="store_true")

    return parser


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider-url", default=DEFAULT_PROVIDER_URL)
    parser.add_argument("--container-name", default=DEFAULT_PROVIDER_CONTAINER_NAME)
    parser.add_argument("--port", type=int, default=DEFAULT_PROVIDER_PORT)
    parser.add_argument("--timeout-seconds", type=float, default=2.0)


def _add_provider_runtime_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider-runtime",
        choices=task309_provider_runtime_values(),
        default=DEFAULT_TASK309_PROVIDER_RUNTIME.value,
        help=(
            "Structured provider runtime. llama.cpp runtimes are restricted to "
            "JSON Schema response_format or GBNF grammar-constrained JSON."
        ),
    )


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


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Task 309 JSON artifact must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


if __name__ == "__main__":
    raise SystemExit(main())
