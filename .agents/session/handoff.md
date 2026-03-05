# Session Handoff

## Current Session Summary (2026-03-05)

- Completed `T76` (`docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md`).
- Implemented one-command deploy parity + live verification surface:
  - `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`
- Refactored GPU verifier to committed Python module + `--remote` wrapper flow:
  - `scripts/devops/verify-hemma-gpu-runtime.sh`
  - `scripts/sir_convert_a_lot/devops/verify_hemma_gpu_runtime.py`
- Added strict verification contracts + regression tests:
  - `scripts/sir_convert_a_lot/devops/hemma_deploy_verification_contracts.py`
  - `tests/sir_convert_a_lot/test_hemma_deploy_verification_contracts.py`
  - `tests/sir_convert_a_lot/test_hemma_deploy_and_verify.py`
- Updated runbook and skill guidance:
  - `docs/runbooks/runbook-hemma-devops-and-gpu.md`
  - `.agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- Added OCR hardening follow-up planning:
  - `docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md`
  - `docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`

- Started `T77` (`docs/backlog/tasks/task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke.md`).
- Added OCR engine + language selection for v2 PDF conversions:
  - v2 JobSpec: `pdf_options.ocr_engine` and `pdf_options.ocr_languages`,
  - CLI: `--ocr-engine` and repeatable `--ocr-language`,
  - preflight gates to fail-fast on missing OCR engines or language packs.
- Updated Hemma defaults for Swedish OCR correctness:
  - default engine: EasyOCR with `sv,en`,
  - optional engine: Tesseract CLI with `swe,eng` packs installed in the image.
- Extended Hemma v2 live verifier with a Swedish OCR smoke step that asserts `åäö` and captures
  OCR metadata + throughput evidence fields.

Live evidence (pass):

- `build/verification/task-76-hemma-deploy-verify/report.json` (`status=passed`)
- `build/verification/task-76-hemma-deploy-verify/report.md`
- `build/verification/task-76-hemma-deploy-verify/readyz.json`
- `build/verification/task-76-hemma-deploy-verify/metrics.prom`
- `build/verification/task-76-hemma-deploy-verify/remote_head.txt`

Validation evidence:

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot -q` (pass: `449 passed, 5 skipped`)
- `pdm run validate-tasks` (pass: `Validated 109 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=136 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

Validation evidence (local, T77):

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot -q` (pass: `458 passed, 5 skipped`)
- `pdm run coverage-gate` (pass: total coverage `95.71%`)
- `pdm run validate-tasks` (pass: `Validated 109 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=136 rules=9`)

Live evidence (pending, T77):

- Merge to main worktree, then run:
  - `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision "$(git rev-parse HEAD)" --lane host --api-key <key>`
  - ensure evidence includes the Swedish OCR excerpt under `build/verification/...`.

Cross-repo skill audit:

- Updated `/Users/olofs_mba/Documents/Repos/huledu-reboot/.agents/skills/huledu-devops-hemma/SKILL.md`
  with Sir Convert-a-Lot lane/deploy coexistence guidance.
- `windsurf-project` skill audit found no Sir Convert-a-Lot/Hemma skill references to update.

## Next Session Goals (2026-03-05)

- Merge `codex/task-77-ocr-engine-sv` into `main` and run Hemma live verification to produce T77
  evidence before publishing the `T74` throughput benchmark report.
- Execute `T72` (parallel worker pools) and then `T74` (throughput benchmark/report).
- Keep `T76` evidence command as pre-slice gate before throughput-tuning changes.
- Preserve strict metric label safety (`job_id=`/`jobv2_` forbidden) and host-lane verification policy.
