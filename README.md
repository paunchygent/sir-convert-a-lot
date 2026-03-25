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

Start the explicit CPU-only local debug service as a Docker container:

```bash
pdm install
pdm run dev-start
pdm run dev-logs
```

This local `:8085` lane is for laptop debugging only. Default downstream app
integration should still target Hemma through the tunnel lane
(`127.0.0.1:28085`) or the public lane
([convert.hule.education](https://convert.hule.education)).

In another terminal, convert documents via the CLI:

```bash
pdm run convert-a-lot convert ./pdfs --to md --output-dir ./research

# Check supported routes and implementation status
pdm run convert-a-lot routes
```

## Core Commands

**Service & Conversion:**

- `docker compose up -d sir_convert_a_lot_prod`
- `docker compose logs -f sir_convert_a_lot_prod`
- `pdm run convert-a-lot convert <path> --output-dir <dir>`
- `pdm run convert-a-lot jobs [cancel|resume|partial|checkpoint]`

Local-runtime rule:

- Do not run `pdm run serve:sir-convert-a-lot` for local app integration.
- Do not start `uvicorn scripts.sir_convert_a_lot.service:app` directly on `:8085`.
- The supported local service lane is the CPU-only Docker dev service driven by
  `pdm run dev-start` / `compose.local.yaml`.
- The Hemma GPU/prod lane remains the canonical real integration surface.

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
