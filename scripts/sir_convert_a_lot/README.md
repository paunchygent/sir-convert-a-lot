# Sir Convert-a-Lot

LLM-friendly CLI and HTTP service for deterministic document conversion through one v2 API surface.

## Why

Conversion logic historically drifted across tools and repos. Sir Convert-a-Lot provides one
contracted runtime with stable idempotency, job lifecycle semantics, and machine-readable manifests.

## Current Capabilities (v2)

- `pdf -> md` (Docling/PyMuPDF policy-governed PDF stage)
- `docx -> md`
- `html -> md`
- `html -> pdf`
- `html -> docx`
- `md -> pdf`
- `md -> docx`
- `pdf -> docx`
- GPU-first policy for PDF processing
- Async job model with bounded wait + polling
- Idempotent create-job behavior
- Deterministic batch manifest output

## Usage

### Service readiness (Hemma tunnel lane)

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/readyz
```

### Convert files

```bash
pdm run convert-a-lot convert ./inputs --output-dir ./output --to md
```

Explicit remote submission:

```bash
pdm run convert-a-lot convert ./inputs \
  --output-dir ./output \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY"
```

## CLI Options

| Flag | Default | Description |
| --- | --- | --- |
| `--to` | `md` | Target format (`md`, `pdf`, `docx`) |
| `--from` | auto | Source format override (`pdf`, `docx`, `md`, `html`) |
| `--dry-run` | `false` | Print selected route and discovered files |
| `--service-url` | `http://127.0.0.1:28085` | Service base URL |
| `--api-key` | `$SIR_CONVERT_A_LOT_API_KEY` | API key |
| `--wait-seconds` | `5` | Bounded wait on create-job (`0..20`) |
| `--max-poll-seconds` | `120` | Poll timeout per job |
| `--recursive` / `--no-recursive` | `--recursive` | Directory traversal mode |
| `--resources` | none | Optional resource directory/zip upload |
| `--css` | none | CSS list for PDF outputs |
| `--reference-docx` | none | Reference DOCX for DOCX outputs |
| `--acceleration-policy` | `gpu_required` | PDF-stage acceleration policy |
| `--backend-strategy` | `auto` | PDF-stage backend strategy |
| `--ocr-mode` | `auto` | PDF-stage OCR mode |
| `--table-mode` | `accurate` | PDF-stage table mode |
| `--normalize` | `strict` | Markdown normalization mode |
| `--manifest-name` | `sir_convert_a_lot_manifest.json` | Manifest filename |

## Manifest

Each run writes a deterministic JSON manifest in `--output-dir` with one entry per input source.

- Success: `status="succeeded"` and `output_path` present.
- Timeout while still running: `status="running"` with `error_code="job_timeout"` and `job_id`.
- Failure: `status="failed"` with `error_code`.

## Architecture

```text
scripts/sir_convert_a_lot/
├── domain/          # Core job models and invariants
├── application/     # Response and manifest contracts
├── infrastructure/  # Runtime engine and persistence
├── interfaces/      # HTTP/CLI adapters and clients
├── cli.py           # Compatibility facade
├── service.py       # Service entrypoint facade
├── client.py        # Client export facade
└── models.py        # Model export facade
```

## API Reference

- Normative API contract:
  `docs/converters/multi_format_conversion_service_api_v2.md`
- Downstream integration contract:
  `docs/converters/downstream_integration_contract_v2.md`

## LLM Convention

Assistants should use natural-language invocation:

- "Tell Sir Convert-a-Lot to convert x to y."
- "Tell convert-a-lot to convert x to y."
