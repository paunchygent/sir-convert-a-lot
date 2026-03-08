# Sir Convert-a-Lot

Standalone platform for LLM-friendly document conversion.

Canonical intent:

- One stable CLI/API surface (v2).
- Deterministic, auditable outputs.
- GPU-first remote execution path (Hemma).
- Docs-as-code governance built into the repo.

## Capabilities & Routes

The v2 service executes the following conversion routes natively:

- **To Markdown:** `pdf -> md`, `docx -> md`, `html -> md`
- **To PDF:** `docx -> pdf`, `html -> pdf`, `md -> pdf`
- **To DOCX:** `pdf -> docx`, `html -> docx`, `md -> docx`

Future approved routes include `md -> wav` (sidecar-backed TTS).

## API & CLI Surface

- **REST API (v2):** Asynchronous, idempotent job submission with correlation tracking. Supports long-running job checkpoints, partial artifact retrieval, cancel/resume operations, resource bundles (CSS/images), and DOCX templates.
- **CLI (`convert-a-lot`):** Client application that submits files and directories to the v2 service. Includes flags for acceleration policies, OCR configuration, and long-job management.

## Quickstart

Start the local v2 API service:

```bash
pdm install
pdm run serve:sir-convert-a-lot
```

In another terminal, convert documents via the CLI:

```bash
pdm run convert-a-lot convert ./pdfs --to md --output-dir ./research

# Check supported routes and implementation status
pdm run convert-a-lot routes
```

## Core Commands

**Service & Conversion:**

- `pdm run serve:sir-convert-a-lot`
- `pdm run convert-a-lot convert <path> --output-dir <dir>`
- `pdm run convert-a-lot jobs [cancel|resume|partial|checkpoint]`

**Hemma (Remote) Execution:**

- `pdm run run-hemma -- <command> [args]`
- `pdm run run-local-pdm <script> [args]`

**Docs-as-code Governance:**

- `pdm run new-[task|epic|story|doc|rule]`
- `pdm run validate-tasks`
- `pdm run validate-docs`

## Documentation & Contracts

**Architecture:**

- [Service API v2](docs/converters/multi_format_conversion_service_api_v2.md)
- [Downstream Integration Contract](docs/converters/downstream_integration_contract_v2.md)
- [Async Push Extension](docs/converters/multi_format_conversion_service_api_v2_async_push.md)

**Governance:**

- System rules: `.agents/rules/`
- Active backlog: `docs/backlog/`
- Docs contract: `docs/_meta/docs-contract.yaml`

Before operating, consult [`AGENTS.md`](AGENTS.md) and execute quality gates.
