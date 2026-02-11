# Sir Convert-a-Lot

LLM-friendly CLI and HTTP service for document format conversion. Designed so coding assistants and batch scripts can convert between popular formats through a single interface with deterministic, auditable output.

## Why

Scattered converter scripts accumulate across projects. Each has its own invocation style, error handling, and output conventions. Sir Convert-a-Lot consolidates these into one CLI/API surface with consistent job semantics, idempotency, and machine-readable manifests — so both humans and LLMs can drive conversions without format-specific glue code.

## Current Capabilities (v1)

- **PDF → Markdown** via Docling or PyMuPDF backends
- GPU-first execution policy (rollout lock by default)
- Async job API with polling and bounded wait
- Idempotent job creation (SHA256-based fingerprinting)
- Deterministic JSON manifest per batch run

Planned: HTML, DOCX, XLSX, CSV conversion routes (see [Story 003d](../../docs/backlog/stories/story-03-04-consolidate-html-pdf-md-docx-xlsx-csv.md)).

## Usage

### Start the service

```bash
pdm run serve:sir-convert-a-lot
```

### Convert PDFs

```bash
pdm run convert-a-lot convert ./pdfs --output-dir ./output
```

With explicit service URL and API key (tunnel to GPU host):

```bash
pdm run convert-a-lot convert ./pdfs \
  --output-dir ./output \
  --service-url http://127.0.0.1:18085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY"
```

### Run Story 003b benchmark

```bash
pdm run benchmark:story-003b \
  --fixtures-dir tests/fixtures/benchmark_pdfs \
  --output-json docs/reference/benchmark-story-003b-gpu-governance-local.json
```

### CLI Options

| Flag | Default | Description |
| --- | --- | --- |
| `--to` | `md` | Target format (v1: `md` only) |
| `--service-url` | `http://127.0.0.1:18085` | Service base URL |
| `--api-key` | `$SIR_CONVERT_A_LOT_API_KEY` | API key |
| `--wait-seconds` | `5` | Bounded wait on job creation (0–20) |
| `--max-poll-seconds` | `120` | Max polling time per job |
| `--recursive` / `--no-recursive` | `--recursive` | Recurse into subdirectories |
| `--acceleration-policy` | `gpu_required` | `gpu_required`, `gpu_prefer`, or `cpu_only` |
| `--manifest-name` | `sir_convert_a_lot_manifest.json` | Output manifest filename |

## Manifest

Each batch writes a JSON manifest to `--output-dir`:

```json
{
  "generated_at": "2026-02-11T17:00:00Z",
  "source_root": "./pdfs",
  "output_root": "./output",
  "entries": [
    {
      "source_file_path": "paper.pdf",
      "job_id": "job_01K2S8CXH3BWV7S6E5B7P4Y2ZR",
      "status": "succeeded",
      "output_path": "./output/paper.md",
      "error_code": null
    }
  ]
}
```

Long-running behavior:

- If a job exceeds `--max-poll-seconds`, CLI now records `status: "running"` with `job_id` and
  `error_code: "job_timeout"` in the manifest, and exits non-error unless there are terminal
  failures.
- This supports background completion flows where conversion continues server-side and result
  retrieval can happen later via status/result endpoints.

## Architecture

```text
scripts/sir_convert_a_lot/
├── domain/          # Core job specs and invariants
├── application/     # Response/manifest contracts
├── infrastructure/  # Filesystem-backed runtime engine
├── interfaces/      # CLI, HTTP API, HTTP client adapters
├── cli.py           # Compatibility facade
├── service.py       # Compatibility facade
├── client.py        # Compatibility facade
└── models.py        # Compatibility facade
```

DDD-oriented package layout. Compatibility facades at the root preserve stable imports during internal restructuring.

## Configuration (Environment Variables)

| Variable | Default | Description |
| --- | --- | --- |
| `SIR_CONVERT_A_LOT_API_KEY` | `dev-only-key` | Service API key |
| `SIR_CONVERT_A_LOT_DATA_DIR` | `build/sir_convert_a_lot` | Storage root for uploads and artifacts |
| `SIR_CONVERT_A_LOT_GPU_AVAILABLE` | `1` | GPU availability flag |

Rollout lock note:

- CPU unlock env vars (`SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY`, `SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK`)
  are disabled in normal startup paths during Story 003b governance lock.
- CPU unlock behavior is available only through explicit test configuration in `ServiceConfig`.

## API Reference

See [PDF to Markdown Service API v1](../../docs/converters/pdf_to_md_service_api_v1.md) for the full HTTP contract.

## LLM Convention

Assistants should use natural-language invocation:

- *"Tell Sir Convert-a-Lot to convert x to y."*
- *"Tell convert-a-lot to convert x to y."*
