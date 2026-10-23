# Sir Convert-a-Lot

## Identity

Sir Convert-a-Lot is the document-conversion platform for PDF, DOCX, Markdown,
HTML and audio-to-text workflows. It is a Python/PDM repository with Hemma
offload and GPU-first runtime governance. Docs-as-code under `docs/` is the
planning and contract truth.

## Commands

Run from the repository root; the full list is in `pyproject.toml` and `README.md`.

- Local: `pdm run run-local-pdm ...`, `dev-start`, `dev-logs`.
- Hemma: `pdm run run-hemma -- ...` or a committed command surface.
- Docs and governance close-out: `pdm run docs-validate`, `skills-validate`,
  `handoff-validate`, then `git diff --check`.
- Python close-out: `pdm run check --plan <scope>`, then `pdm run check <scope>`.

## Product Facts

- Hemma's GPU is reserved for the private Qwen CJ experiment. Sir GPU worker,
  STT, Qwen sidecars, training and benchmark profiles stay stopped.
- Local integration uses the CPU-only Docker dev service on `:8085`; never run
  `serve:sir-convert-a-lot` or `uvicorn` there directly.
- The direct public hostname is retired (ADR-SIRCON-0014); there is no public lane.
- `build/`, `data/` and generated artifact trees are evidence, not scratch.

## Local Routes

- Active state: `handoff.md`; docs: `docs/index.md`; session history:
  `.codex/long-term-memory/index.md`; local skills: `.codex/skills/README.md`.
- Repository topology and layer boundaries: `repo-code-map`.
- Any Hemma runtime action: `hemma-devops`, then `sir-convert-a-lot-devops-hemma`.
- Qwen3-TTS fine-tuning: `sir-convert-a-lot-qwen-finetuning`; other speech-model
  fine-tuning: `speech-model-finetuning-on-hemma`.
- Colab and Hemma notebook orchestration: `sir-convert-a-lot-colab-hemma`.
