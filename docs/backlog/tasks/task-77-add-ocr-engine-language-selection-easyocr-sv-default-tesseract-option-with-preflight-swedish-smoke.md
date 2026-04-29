---
id: task-77-add-ocr-engine-language-selection-easyocr-sv-default-tesseract-option-with-preflight-swedish-smoke
title: Add OCR engine + language selection (EasyOCR sv default, Tesseract option) with preflight + Swedish smoke
type: task
status: completed
priority: high
created: '2026-03-05'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-21-gpu-accelerated-multilingual-ocr-engine-selection-and-swedish-diacritics-correctness.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/sir_convert_a_lot.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - Dockerfile
  - pyproject.toml
  - scripts/sir_convert_a_lot/domain/specs_v2.py
  - scripts/sir_convert_a_lot/application/contracts_v2.py
  - scripts/sir_convert_a_lot/infrastructure/conversion_backend.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
labels:
  - ocr
  - easyocr
  - tesseract
  - swedish
  - gpu
  - performance
  - hemma
  - verification
  - worktree
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Provide a robust, fail-fast multilingual OCR configuration for long PDF conversions:

- default OCR engine on Hemma: EasyOCR with GPU enabled and `sv` + `en`,
- optional OCR engine: Tesseract (CLI) with `swe` + `eng` language data,
- explicit engine/language selection in v2 JobSpec and CLI,
- deploy-time Swedish OCR smoke that asserts `åäö` are preserved,
- preflight gates to prevent multi-hour “wrong engine / wrong language” runs.

## PR Scope

- Contract + CLI:
  - Extend v2 `pdf_options` with:
    - `ocr_engine` (enum; at minimum `auto|easyocr|tesseract_cli`),
    - `ocr_languages` (list of BCP47/ISO639-1 language tags like `sv`, `en`).
  - Note (Docling constraint): `OcrAutoOptions` uses engine defaults; language selection requires
    selecting an explicit engine (`EasyOcrOptions`, `TesseractCliOcrOptions`, etc).
  - Map `ocr_languages` to engine-specific codes:
    - EasyOCR: keep ISO639-1 (`sv`, `en`),
    - Tesseract: map to ISO639-2 (`sv` -> `swe`, `en` -> `eng`).
  - Expose CLI flags (proposed):
    - `--ocr-engine <auto|easyocr|tesseract_cli>`
    - `--ocr-language <tag>` (repeatable)
  - Emit audit metadata:
    - `result.conversion_metadata.ocr_enabled`
    - `result.conversion_metadata.ocr_engine_used`
    - `result.conversion_metadata.ocr_languages_used`
  - Task 269 supersedes the earlier proposed result fields
    `ocr_languages_requested` and `ocr_acceleration_used`. Requested languages
    stay in `pdf_options.ocr_languages`; observed OCR-stage acceleration is
    deferred until a future task defines runtime evidence separate from backend
    `acceleration_used`.
- Runtime:
  - In Docling backend converter build, set `pipeline_options.ocr_options` explicitly when OCR is
    enabled and `ocr_engine != auto`.
  - Default for Hemma deployment when OCR is enabled: `easyocr` + `sv,en` (GPU enabled).
  - Optional selection: `tesseract_cli` + `swe,eng`.
- Dependencies / image:
  - Add `easyocr` dependency and ensure model downloads are deterministic (prefer build-time cache
    warmup; avoid first-request model download).
  - Add system packages to runtime image for Tesseract + Swedish language data
    (Debian: `tesseract-ocr`, `tesseract-ocr-eng`, `tesseract-ocr-swe`).
- Preflight fail-fast:
  - If `ocr_engine=tesseract_cli`, assert:
    - `tesseract` exists,
    - `tesseract --list-langs` includes requested languages (`swe` when requested).
  - If `ocr_engine=easyocr`, assert:
    - EasyOCR import succeeds,
    - requested language tags are supported,
    - when `acceleration_policy=gpu_required`, EasyOCR is configured to use GPU (no silent CPU).
- Deploy-time smoke (lightweight, runs in current live verification flow):
  - Extend Hemma v2 smoke verifier to include a Swedish OCR fixture conversion and assert output
    contains `åäö`.
  - Capture `/readyz` + `/metrics` snapshots and enforce label safety (`job_id` etc not present).

## Worktree (Mandatory)

Work on this task in a dedicated git worktree to avoid conflicts with ongoing Epic 06 lanes.

```bash
mkdir -p ../sir-worktrees
git worktree add -b codex/task-77-ocr-engine-sv ../sir-worktrees/task-77-ocr-engine-sv
cd ../sir-worktrees/task-77-ocr-engine-sv
```

## Deliverables

- [x] v2 JobSpec supports `pdf_options.ocr_engine` + `pdf_options.ocr_languages` (docs + validators updated).
- [x] CLI supports selecting OCR engine/languages for PDF routes (docs updated).
- [x] Docling backend uses EasyOCR GPU for OCR by default on Hemma; Tesseract CLI is selectable.
- [x] Preflight rejects missing engine/language with actionable error before starting long runs.
- [x] Swedish OCR deploy-smoke exists and is integrated into the current Hemma verification workflow.
- [x] Evidence artifacts are deterministic (report JSON/MD, readyz, metrics, sample OCR output excerpt).

## Acceptance Criteria

- [x] Swedish diacritics preserved:
  - the Swedish OCR smoke output contains `å`, `ä`, `ö`,
  - `conversion_metadata.ocr_enabled=true`.
- [x] Engine/language are explicit and observable:
  - `conversion_metadata.ocr_engine_used` and `ocr_languages_used` are populated.
- [x] GPU-first policy holds for OCR:
  - `conversion_metadata.acceleration_used="cuda"` for Docling execution,
  - no silent CPU fallback when EasyOCR is requested with GPU-required policy,
  - the old `conversion_metadata.ocr_acceleration_used` claim is superseded by
    Task 269 and is not part of the active v2 result contract.
- [x] Preflight gate is fail-fast:
  - missing `swe` for Tesseract fails job creation with remediation instructions.
- [x] Deploy-time smoke stays lightweight:
  - adds \<= 1 extra OCR job (small fixture),
  - smoke completes within 5 minutes on Hemma and writes deterministic evidence under `build/verification/`.
- [x] Metrics safety asserted during verification:
  - `/metrics` does not contain `job_id=` and does not include job ids as label values.
- [x] Performance evidence captured (live check + targets):
  - record median `pages_per_minute` and stage timing keys for the smoke OCR job(s),
  - document a baseline vs new default comparison (tie into `T74` throughput benchmark report),
  - explicit operator benchmark target for the “300 PDFs” corpus:
    - wall-clock \<= 60 minutes on Hemma tuned defaults, with report artifact.

## Validation Evidence (Local)

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot -q` (pass: `476 passed, 5 skipped`)
- `pdm run coverage-gate` (pass: total coverage `95.76%`)
- `pdm run validate-tasks` (pass: `Validated 109 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=136 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- Live command (pass):
  - `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision "$(git rev-parse HEAD)" --lane host`
  - local artifacts:
    - `build/verification/task-76-hemma-deploy-verify/report.json`
    - `build/verification/task-76-hemma-deploy-verify/report.md`
  - remote smoke artifacts (Hemma):
    - `build/verification/task-76-hemma-deploy-verify/v2-smoke/report.json`
    - `build/verification/task-76-hemma-deploy-verify/v2-smoke/swedish_ocr_excerpt.txt`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
