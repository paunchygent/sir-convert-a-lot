---
name: sir-convert-a-lot-client
description: >-
  Client-side skill for using Sir Convert-a-Lot / convert-a-lot against the Hemma
  conversion service (API v2). Covers all implemented routes (pdf/docx/md/html to
  md/pdf/docx), lane selection (tunnel vs internet), CSS/resources/reference-docx
  uploads, and manifest-based triage.
---

# Sir Convert-a-Lot Client (service v2)

## Sources of truth

- `docs/converters/sir_convert_a_lot.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`
- CLI flags (source of truth): `scripts/sir_convert_a_lot/interfaces/cli_app.py`

## Canonical lanes (only these)

- Tunnel lane: `http://127.0.0.1:28085`
  - after `ssh hemma -L 28085:127.0.0.1:28085 -N`
- Internet lane: `https://convert.hule.education`

## Preflight (always)

- `curl -fsS "$SERVICE_URL/readyz"`
- Provide API key:
  - set `SIR_CONVERT_A_LOT_API_KEY`, or
  - pass `--api-key "$SIR_CONVERT_A_LOT_API_KEY"`

## Canonical invocation (works from any repo)

Run the CLI from the canonical repo so the command surface and wrappers exist:

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot routes
```

Then convert using absolute paths (so you can target files in other repos):

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert <ABS_SOURCE> \
  --to <md|pdf|docx> \
  --output-dir <ABS_OUT_DIR> \
  --service-url "$SERVICE_URL"
```

Notes:

- The CLI default `--service-url` is the tunnel lane; pass `--service-url` explicitly for the
  internet lane.
- The CLI writes `sir_convert_a_lot_manifest.json` into `--output-dir` (override via
  `--manifest-name`).
- Use `--dry-run` when unsure: it prints the selected route + pipeline steps without executing.

## Recipes (implemented routes)

### HTML -> PDF (with CSS + resources)

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/handout.html \
  --to pdf \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --css /abs/path/to/style.css \
  --resources /abs/path/to/resources_dir \
  --wait-seconds 20
```

- Use `--resources` when the HTML references local files (images, fonts, linked CSS). Pass the
  directory root that contains the referenced files.
- Use `--css` to apply/force PDF styling (HTML->PDF and MD->PDF). Can be passed multiple times.

### HTML -> DOCX

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/handout.html \
  --to docx \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --resources /abs/path/to/resources_dir
```

### HTML -> Markdown (`--resources` supported)

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/handout.html \
  --to md \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --resources /abs/path/to/resources_dir
```

### Markdown -> PDF

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/notes.md \
  --to pdf \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --css /abs/path/to/print.css \
  --resources /abs/path/to/assets
```

### Markdown -> DOCX (optional reference DOCX)

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/notes.md \
  --to docx \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --reference-docx /abs/path/to/reference.docx
```

### DOCX -> Markdown

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/input.docx \
  --to md \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL"
```

### DOCX -> PDF

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/input.docx \
  --to pdf \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL"
```

### PDF -> Markdown (GPU-first defaults)

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/input.pdf \
  --to md \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL" \
  --acceleration-policy gpu_required \
  --backend-strategy auto \
  --ocr-mode auto \
  --table-mode accurate \
  --normalize strict
```

### PDF -> DOCX

```bash
cd ~/Documents/Repos/sir-convert-a-lot
pdm run run-local-pdm convert-a-lot convert /abs/path/to/input.pdf \
  --to docx \
  --output-dir /abs/path/to/out \
  --service-url "$SERVICE_URL"
```

## Manifest + triage

- The CLI writes `sir_convert_a_lot_manifest.json` in `--output-dir`.
- Each entry includes:
  - `source_file_path`
  - `job_id`
  - `status` (`succeeded|failed|running`)
  - `output_path`
  - `error_code`

For failures, use `job_id` to query:

- `GET $SERVICE_URL/v2/convert/jobs/{job_id}`
- `GET $SERVICE_URL/v2/convert/jobs/{job_id}/result`
- `GET $SERVICE_URL/v2/convert/jobs/{job_id}/artifact`

## Guardrails

- Only use canonical lanes: `127.0.0.1:28085` or `https://convert.hule.education`.
- Keep GPU-first policy for PDF inputs unless the user explicitly requests CPU-only.
- Prefer `--backend-strategy auto` unless the user explicitly asks for PyMuPDF.
- `--backend-strategy pymupdf` requires:
  - `--ocr-mode off`
  - `--acceleration-policy cpu_only`
- Do not use superseded lanes such as `127.0.0.1:8085` or `127.0.0.1:18085`.

## Response contract

Return:

- command(s) executed,
- output dir + artifact path(s),
- manifest summary counts (`succeeded`, `failed`, `running`),
- explicit list of failures/timeouts with the next action.

