---
name: sir-convert-a-lot-pdf-to-md
description: >-
  Run Sir Convert-a-Lot PDF-to-Markdown conversions through local or Hemma
  tunnel service endpoints, including readiness checks, CLI submission,
  manifest review, and failed-job triage. Use when asked to convert PDFs to
  Markdown, run batch PDF-to-MD conversions, use Sir Convert-a-Lot/convert-a-lot,
  or debug conversion job outcomes.
---

# Sir Convert-a-Lot PDF to MD

## Sources of Truth

- `docs/converters/sir_convert_a_lot.md`
- `docs/converters/pdf_to_md_service_api_v1.md`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Workflow

1. Confirm the execution lane.

- Local service: `http://127.0.0.1:8085`
- Hemma tunnel: `http://127.0.0.1:28085` after `ssh hemma -L 28085:127.0.0.1:28085 -N`

2. Run preflight checks before conversion.

- `curl -fsS "$SERVICE_URL/readyz"`
- Resolve API key for authenticated service calls:
  - Preferred: `SIR_CONVERT_A_LOT_API_KEY`
  - Dev fallback (when env var is unset): `dev-only-key`

3. Submit conversion with production defaults.

- From repo root:

    ```bash
    pdm run convert-a-lot convert ./pdfs \
      --output-dir ./research \
      --service-url "$SERVICE_URL" \
      --api-key "${SIR_CONVERT_A_LOT_API_KEY:-dev-only-key}"
    ```

- From any other repo, route through this repo script surface:

    ```bash
    pdm run run-local-pdm convert-a-lot convert ./pdfs \
      --output-dir ./research \
      --service-url "$SERVICE_URL" \
      --api-key "${SIR_CONVERT_A_LOT_API_KEY:-dev-only-key}"
    ```

4. Inspect `sir_convert_a_lot_manifest.json` in `--output-dir`.

- Success entries include `status: completed` and an `output_path`.
- Timeout entries can remain `status: running` with `job_id` and `error_code: job_timeout`.

5. Triage non-complete jobs deterministically.

- Query status: `GET /v1/convert/jobs/{job_id}`
- Fetch result: `GET /v1/convert/jobs/{job_id}/result`
- Report per-file outcomes with `source_file_path`, `status`, `output_path`, and `error_code`.

## Guardrails

- Keep GPU-first defaults unless the user explicitly requests another mode.
- Do not silently fall back to CPU when a GPU-required lane fails.
- Use `backend_strategy=auto` unless the user explicitly asks for `pymupdf`.
- If using `pymupdf`, enforce compatibility:
  - `--ocr-mode off`
  - `--acceleration-policy cpu_only`

## Response Contract

- Return:
  - command(s) executed,
  - manifest summary counts (`completed`, `failed`, `running`),
  - output directory path,
  - explicit list of failures/timeouts with next action.
