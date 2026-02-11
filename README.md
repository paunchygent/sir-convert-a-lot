# Sir Convert-a-Lot

Standalone conversion platform for LLM-friendly document conversion workflows.

Canonical intent:
- one stable CLI/API surface,
- deterministic and auditable output,
- GPU-first remote execution path,
- docs-as-code governance built into the repo.

## Quickstart

```bash
pdm install
pdm run serve:sir-convert-a-lot
```

In another terminal:

```bash
pdm run convert-a-lot convert ./pdfs --output-dir ./research
```

## Commands

- `pdm run serve:sir-convert-a-lot`
- `pdm run convert-a-lot`
- `pdm run sir-convert-a-lot`
- `pdm run run-local-pdm <script> [args]`
- `pdm run run-hemma -- <command> [args]`
- `pdm run new-task`
- `pdm run new-doc`
- `pdm run new-rule`
- `pdm run validate-tasks`
- `pdm run validate-docs`
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Architecture

See:
- `scripts/sir_convert_a_lot/README.md`
- `docs/converters/pdf_to_md_service_api_v1.md`
- `docs/converters/sir_convert_a_lot.md`
- `docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md`

## Governance

- Agent rules: `.agents/rules/`
- Session state: `.agents/work/session/`
- Skills: `.agents/skills/`
- Active planning/tasks: `docs/backlog/`
- Docs contract: `docs/_meta/docs-contract.yaml`
