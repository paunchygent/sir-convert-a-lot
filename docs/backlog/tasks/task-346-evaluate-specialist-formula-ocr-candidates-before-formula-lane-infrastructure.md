---
id: task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure
title: Evaluate specialist formula OCR candidates before formula-lane infrastructure
type: task
status: completed
priority: high
created: '2026-06-06'
last_updated: '2026-06-06'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md
  - docs/backlog/tasks/task-344-diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - docs/backlog/tasks/task-272-add-formula-aware-final-pass-and-linked-pdf-image-artifacts-for-dirty-pdf-ocr-outputs.md
  - docs/runbooks/runbook-hemma-conversion-benchmarks.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - scripts/sir_convert_a_lot/devops/docling_page_window_replay.py
  - scripts/sir_convert_a_lot/devops/render_pdf_bbox_crop.py
  - scripts/sir_convert_a_lot/devops/formula_candidate_eval.py
  - scripts/sir_convert_a_lot/devops/formula_candidate_eval_inputs.py
  - scripts/sir_convert_a_lot/devops/formula_candidate_eval_candidates.py
  - scripts/sir_convert_a_lot/devops/formula_candidate_eval_reporting.py
  - tests/sir_convert_a_lot/test_formula_candidate_eval.py
  - docs/backlog/tasks/task-350-integrate-deepseek-ocr-2-hf-eager-candidate-replay-for-task-346.md
labels:
  - pdf
  - formula
  - latex
  - ocr
  - evaluation
  - gpu
  - deepseek-ocr
  - unimer
  - pp-formulanet
  - best-effort
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Boundary

The user intent is to evaluate better formula/OCR candidates before building
formula-lane infrastructure or changing production policy.

This is a no-fuss pre-infrastructure evaluation task. It must build one simple
script that routes the already-established Task 344 incident pages and formula
regions through specialist candidates, records output quality and performance,
and produces a visual review bundle comparing candidate output against the PDF
source.

This task does not change the public CLI, production service routing, Docling
authority policy, or long-lived model infrastructure. It is the evidence slice
that decides whether any specialist formula/document OCR candidate deserves a
later governed integration task.

Runtime handling follows the Sir Convert-a-Lot Hemma/GPU wrappers and runbooks.
Upstream examples that mention CUDA are not a blocker or product conclusion by
themselves; Hemma runtime compatibility must be proven or disproven through the
repo's sanctioned GPU command surfaces.

## Objective

Build and run a small evaluation harness for candidate formula/OCR approaches
on the known pages `13-16` from the Task 344 incident replay.

The harness must compare:

- the current Task 344/Docling/Granite incident output as the regression
  baseline,
- source-layer extraction evidence as a non-generative reference baseline,
- UniMERNet,
- PP-FormulaNet family candidates exposed by PaddleOCR,
- DeepSeek-OCR-2 as the stronger document/OCR VLM candidate.

The result must be a local evidence bundle and concise task update that answer:

- which candidates run successfully on the established incident inputs,
- how long each candidate takes per page/region,
- whether candidate output removes or repeats the known formula hallucinations,
- whether the output visually matches the PDF source closely enough to justify
  a later integration task,
- whether any runtime blocker is proven rather than assumed.

## PR Scope

- Add `scripts/sir_convert_a_lot/devops/formula_candidate_eval.py` as a
  simple devops/evaluation script.
- Reuse the established Task 344 input pages and replay artifacts. The default
  input must be the pages `13-16` incident source used by
  `build/verification/task-344-md-review-20260605T112725Z/report.json` when
  present.
- Reuse existing rendering/cropping helpers such as
  `scripts/sir_convert_a_lot/devops/render_pdf_bbox_crop.py` where practical.
- Prefer already-captured formula crops or replay diagnostics when available.
  If crop metadata is absent, render deterministic page images and require a
  clearly recorded crop source. Do not introduce a new corpus or manual
  cherry-picked examples in this task.
- Add lightweight candidate adapters that can invoke local or Hemma-installed
  model commands and record stdout/stderr/log paths. Adapter configuration may
  be script arguments or environment variables because this is not a public CLI
  contract.
- Write all generated evidence under
  `build/verification/task-346-formula-candidate-eval/<timestamp>/`.
- Produce:
  - `report.json` with machine-readable inputs, candidates, commands, timings,
    runtime facts, output paths, and failure reasons,
  - `report.md` with a concise human summary,
  - source page/crop images,
  - candidate text/LaTeX/Markdown outputs,
  - a side-by-side HTML or Markdown visual review index linking source images
    beside each candidate output.
- Record a sanitized summary in this task after the run. Generated private
  PDFs, page images, crops, raw model outputs, and large logs remain local
  evidence unless a later task explicitly promotes a sanitized artifact.

## Candidate Sources

Use primary or official sources before implementing candidate adapters:

- PaddleOCR formula recognition documentation:
  `https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/formula_recognition.html`
- PaddleOCR formula recognition module documentation:
  `https://www.paddleocr.ai/main/en/version3.x/module_usage/formula_recognition.html`
- PaddlePaddle UniMERNet model card:
  `https://huggingface.co/PaddlePaddle/UniMERNet`
- PaddlePaddle PP-FormulaNet_plus-S model card:
  `https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-S`
- DeepSeek-OCR-2 model card:
  `https://huggingface.co/deepseek-ai/DeepSeek-OCR-2`
- DeepSeek-OCR-2 paper:
  `https://arxiv.org/abs/2601.20552`

If a candidate's current docs require a runtime installation or backend that is
not already available on Hemma, prove that with the sanctioned wrappers and
record it as a candidate blocker. Do not infer incompatibility from an upstream
CUDA-oriented example alone.

## Metrics and Review

The evaluation script must measure enough to support a product decision without
turning into lab infrastructure:

- wall-clock time per page/crop/candidate,
- process return code and bounded stderr/stdout excerpts,
- backend/runtime facts available from the invoked command,
- GPU runtime facts when available through Hemma-safe probes,
- peak output length and token/character counts when exposed by the candidate,
- known bad marker counts from Task 344, including leaked `</formula`,
  `\mathbmath`, repeated `\mathbf`, and `looly`,
- cheap structural checks for candidate LaTeX where a real parser or renderer
  is already available,
- source-layer comparison evidence using Task 345's established extraction
  direction when available, reported as evidence only.

The task must include human visual inspection of the generated review bundle.
The visual review asks whether each candidate's formula output matches the
source crop/page well enough to justify a later integration task. It is not a
production acceptance heuristic.

## Product Alignment

- Task 346 owns only the pre-infrastructure candidate evaluation script and
  evidence bundle.
- Task 345 remains the owner of the formula evidence data model, authority
  policy, and best-effort representation ladder.
- Task 343 remains the owner of later conversion-decision and performance
  attribution policy.
- Task 342 remains the owner of user-facing CLI/manifest presentation.
- No later task may copy Task 346's throwaway adapter logic into production
  without a governed integration design.
- No formula lane may be promoted merely because a candidate is faster. Quality
  and visual/source faithfulness decide whether a candidate deserves the next
  task.

## Deliverables

- [x] A simple `formula_candidate_eval.py` evaluation script.
- [x] Candidate adapters for current baseline evidence, source-layer baseline,
  UniMERNet, PP-FormulaNet family, and DeepSeek-OCR-2.
- [x] Local generated evidence bundle under
  `build/verification/task-346-formula-candidate-eval/<timestamp>/`.
- [x] `report.json` and `report.md` with timings, output paths, failure
  reasons, and candidate comparison.
- [x] Visual review index comparing source page/crop images with candidate
  output.
- [x] Sanitized task update with results and a recommendation:
  promote one or more candidates to a later integration task, reject them for
  the incident class, or record a concrete runtime blocker.

## Implementation and Run Results

Implemented 2026-06-06:

- `scripts/sir_convert_a_lot/devops/formula_candidate_eval.py`
  provides the thin Task 346 command surface.
- `formula_candidate_eval_inputs.py` harvests Task 344 formula crop
  metadata and renders page/crop source images.
- `formula_candidate_eval_candidates.py` records the current
  Granite/Docling baseline, PyMuPDF source-layer baseline, PaddleOCR formula
  candidates, and DeepSeek-OCR-2 configured-command candidate.
- `formula_candidate_eval_reporting.py` writes `report.json`,
  `report.md`, and `visual-review.html`.
- `tests/sir_convert_a_lot/test_formula_candidate_eval.py` proves crop
  harvesting, known-marker counting, blocker recording, and visual-review
  output.

Run command:

```bash
pdm run run-local-pdm python -m scripts.sir_convert_a_lot.devops.formula_candidate_eval
```

Generated evidence:

```text
build/verification/task-346-formula-candidate-eval/formula-candidate-eval-20260606T160734Z/report.json
build/verification/task-346-formula-candidate-eval/formula-candidate-eval-20260606T160734Z/report.md
build/verification/task-346-formula-candidate-eval/formula-candidate-eval-20260606T160734Z/visual-review.html
```

Result summary:

| Candidate | Status | Inputs | Elapsed ms | Known markers |
| --- | ---: | ---: | ---: | --- |
| `granite_docling_baseline` | `succeeded` | `1` | `249740` | `</formula=36`, `\mathbmath=59`, `\mathbf=304`, `l o o l y=1` |
| `source_layer_pymupdf` | `succeeded` | `40` | `45` | all known markers `0` |
| `unimernet_paddleocr` | `blocked` | `36` | n/a | `candidate_executable_not_found` |
| `pp_formulanet_plus_s_paddleocr` | `blocked` | `36` | n/a | `candidate_executable_not_found` |
| `deepseek_ocr2_command` | `blocked` | `4` | n/a | `candidate_command_not_configured` |

Visual spot-check:

- `p13-texts-5.png` and `p14-texts-51.png` render the expected formula-heavy
  crops from the incident source pages.
- `page-14.png` renders the expected appendix page with equations `33-47`.
- PyMuPDF source-layer crop text is imperfect plain-text math. This is evidence
  against using PyMuPDF text extraction as the final formula/LaTeX conversion
  method: it does not preserve enough formula structure to restore faithful
  semantic LaTeX deterministically. Its role is source-backed evidence,
  localization, contradiction checking, and fallback substrate, not final
  formula transcription authority.

Runtime blocker proof:

```bash
pdm run run-hemma -- /bin/bash -lc 'echo PADDLEOCR_PATH=$(command -v paddleocr || true); /home/paunchygent/apps/sir-convert-a-lot/.venv/bin/python -m pip show paddleocr || true; echo VLLM_PATH=$(command -v vllm || true); /home/paunchygent/apps/sir-convert-a-lot/.venv/bin/python -m pip show vllm || true; echo TRANSFORMERS; /home/paunchygent/apps/sir-convert-a-lot/.venv/bin/python -m pip show transformers | sed -n "1,4p"'
```

Observed Hemma output:

```text
PADDLEOCR_PATH=
WARNING: Package(s) not found: paddleocr
VLLM_PATH=
WARNING: Package(s) not found: vllm
TRANSFORMERS
Name: transformers
Version: 4.57.3
```

Gate result: **blocked after implementation**, not by CUDA/ROCm assumptions.
The evaluation harness is implemented and has run against the established
incident pages/crops. Actual UniMERNet, PP-FormulaNet, and DeepSeek-OCR-2
quality/performance measurement is blocked because the required candidate
runtimes are not installed or configured in the sanctioned local/Hemma command
surfaces. Installing or promoting those dependencies would exceed this
pre-infrastructure evaluation task's stop conditions and needs a governed
runtime-enablement follow-up.

Task 347 follow-up result, 2026-06-06:

- The tested PaddleOCR pip CUDA-wheel path remains blocked on Hemma ROCm
  because `paddlepaddle-gpu==3.3.0` imports CUDA and fails with `libcuda.so.1`.
  This is not a conclusion against native PaddleOCR/PaddleX AMD runtimes.
  Task 348 owns the only valid Paddle continuation: probe the official/native
  AMD GPU container and verify formula-recognition API/model support. CUDA
  shims are out of scope.
- DeepSeek-OCR-2 vLLM can be made to load and run on Hemma only after
  processor-contract, ROCm block-size, prompt, and memory fixes, but it fails
  the quality gate: pages `13-16` all finish by `length` with repeated
  impossible tokens (`arodarod`, `manship`, `十条`, `她们`, etc.).
- A one-page page-14 vLLM eager control also finishes by `length` and repeats
  `<｜begin▁of▁sentence｜>`, so CUDA graph capture is not the sole cause.
- A one-page page-14 DeepSeek-OCR-2 Hugging Face eager control on the exact
  same PNG completes coherently and writes `result.mmd` without the vLLM
  pathology markers.

Updated recommendation: do not promote the current DeepSeek-OCR-2 vLLM ROCm
lane as a Task 346 candidate. If DeepSeek remains the desired specialist OCR
direction, create a later governed integration task for the HF eager path or a
different proven vLLM runtime, then wire that candidate into this harness.

Task 350 follow-up result, 2026-06-06:

- The Task 346 harness now wires DeepSeek-OCR-2 as
  `deepseek_ocr2_hf_eager`, a page-image, single-command-template candidate
  that invokes the proven Hugging Face eager adapter.
- Hemma replay evidence:
  `build/verification/task-350-deepseek-hf-eager-task346-replay/formula-candidate-eval-20260606T201448Z/report.json`.
- The DeepSeek-OCR-2 HF eager candidate succeeded on pages `13-16` in
  `676555 ms` total. Per-page elapsed times were `211817 ms`, `183691 ms`,
  `140573 ms`, and `140461 ms`.
- Host and inner metadata recorded `attn_implementation="eager"` for all four
  pages. The model-saved `result.mmd` files are the useful output artifacts;
  the direct Python return is not useful (`result.md` contains `None`).
- The `result.mmd` outputs had no observed vLLM pathology markers
  (`arodarod`, `manship`, `十条`, `她们`, `<｜begin`) and no observed Task 344
  malformed markers (`</formula`, `\mathbmath`, `l o o l y`).
- Visual review found coherent, broadly source-faithful Markdown/Math output
  compared with the page images and DeepSeek box overlays, but also found
  residual transcription defects: malformed inline math/prose on page `14`, an
  incomplete/odd equation-boundary continuation on page `13`, model-name text
  errors on page `15`, and HTML table/entity artifacts on page `16`.
- This completes Task 346's pre-infrastructure evaluation evidence: Paddle
  lanes are observed/rejected or blocked by concrete Hemma runtime evidence
  from Tasks 347-349, current vLLM DeepSeek is rejected for quality, and HF
  eager DeepSeek is the only successful specialist candidate observed so far.

Final recommendation:

- Do not promote any specialist formula/OCR candidate directly into production
  conversion routing from Task 346 alone.
- Promote DeepSeek-OCR-2 HF eager to a later governed integration design task
  because it is the only specialist candidate that produced coherent Hemma
  output on the incident pages.
- That later integration must be behind Task 345 source-backed authority,
  page-window/cross-page reconciliation, and explicit best-effort artifact
  representation policy. HF eager output must not blindly overwrite
  source-backed born-digital formula evidence.
- Use the Task 346 harness as the fixed replay/evaluation surface for the next
  DeepSeek integration design/evaluation task.
- Continue Task 345 source-layer authority work with the current evidence:
  source-layer extraction is dramatically faster and avoids the Granite
  malformed-marker failure class, but it is evidence/guardrail material only.
  It must not be used as a final formula/LaTeX transcription method because it
  is not semantic LaTeX recognition and cannot deterministically reconstruct
  the lost formula structure.

Validation evidence:

- Red-first focused test before implementation failed with
  `ModuleNotFoundError` for
  `scripts.sir_convert_a_lot.devops.formula_candidate_eval`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_formula_candidate_eval.py`
  -> `4 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_formula_candidate_eval.py tests/sir_convert_a_lot/test_deepseek_ocr2_hf_command.py`
  -> `9 passed` after Task 350.
- Hemma focused Task 350 tests:
  `/home/paunchygent/.local/bin/pdm run pytest-root tests/sir_convert_a_lot/test_formula_candidate_eval.py tests/sir_convert_a_lot/test_deepseek_ocr2_hf_command.py`
  -> `9 passed`.
- `pdm run ruff check scripts/sir_convert_a_lot/devops/render_pdf_bbox_crop.py scripts/sir_convert_a_lot/devops/formula_candidate_eval.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_inputs.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_candidates.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_reporting.py tests/sir_convert_a_lot/test_formula_candidate_eval.py`
  -> passed.
- `pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/devops/formula_candidate_eval.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_inputs.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_candidates.py scripts/sir_convert_a_lot/devops/formula_candidate_eval_reporting.py tests/sir_convert_a_lot/test_formula_candidate_eval.py`
  -> no issues.
- `pdm run docs-sync` regenerated docs indexes.
- `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check` passed.

## Out of Scope

- Production service integration.
- Public CLI flags or user-facing profile changes.
- Replacing Task 345's source-layer formula authority model.
- Replacing Task 343's performance attribution model.
- Full corpus benchmarking.
- Long-lived model server/provider infrastructure.
- Docker image or dependency promotion, unless a separate governed task is
  created after the evaluation proves the need.
- Quality-reducing shortcuts, scrape-style output, or toy heuristics as a
  product solution.

## Acceptance Criteria

- [x] The script runs against the established pages `13-16` inputs or records a
  precise missing-artifact precondition.
- [x] At least the current Granite/Docling baseline, source-layer baseline, one
  UniMERNet or PP-FormulaNet candidate, and DeepSeek-OCR-2 are attempted and
  recorded as success or blocked with evidence.
- [x] Each successful candidate records output paths, elapsed time, return
  status, and known bad marker counts.
- [x] The generated review bundle lets a reviewer inspect source page/crop
  images beside each candidate output.
- [x] The recommendation is based on observed output and timing evidence, not
  guessed model behavior or guessed runtime compatibility.
- [x] Any CUDA/ROCm/runtime conclusion is tied to a sanctioned Hemma wrapper
  run or official repo/runbook evidence.
- [x] No service behavior, public CLI behavior, or production conversion path
  changes in this task.
- [x] Docs index and validation gates pass.

## Checklist

- [x] Candidate docs reviewed
- [x] Implementation complete
- [x] Evaluation run complete
- [x] Visual review complete
- [x] Recommendation recorded
- [x] Docs updated
- [x] Validation complete
