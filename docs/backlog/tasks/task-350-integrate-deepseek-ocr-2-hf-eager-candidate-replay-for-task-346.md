---
id: task-350-integrate-deepseek-ocr-2-hf-eager-candidate-replay-for-task-346
title: Integrate DeepSeek OCR 2 HF eager candidate replay for Task 346
type: task
status: completed
priority: high
created: '2026-06-06'
last_updated: '2026-06-06'
labels:
  - pdf
  - formula
  - ocr
  - deepseek-ocr
  - hemma
  - gpu
related:
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/backlog/tasks/task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - scripts/sir_convert_a_lot/devops/task346_formula_candidate_eval.py
  - scripts/sir_convert_a_lot/devops/task346_formula_candidate_eval_candidates.py
  - scripts/sir_convert_a_lot/devops/task347_deepseek_ocr2_hf_command.py
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Boundary

The user intent is to finish the DeepSeek-OCR-2 candidate evaluation direction
without rerouting around the core conversion problem or promoting unreviewed
model output into production.

Task 350 integrates the already-proven Hemma DeepSeek-OCR-2 Hugging Face eager
command lane into the Task 346 evaluation harness, then reruns the established
Task 346 page inputs with bounded runtime, output capture, and manual/visual
quality review.

This task does not change production conversion routing, public CLI behavior,
Docling policy, or Task 345 formula-authority decisions. It also does not
revive the current vLLM/ROCm DeepSeek lane: Task 347 observed that lane to be
quality-broken on the same inputs.

## Objective

Make DeepSeek-OCR-2 HF eager a governed Task 346 candidate and produce a fresh
Hemma evidence bundle that answers:

- whether the HF eager candidate runs on the established Task 344 incident page
  images under bounded execution;
- whether the candidate writes reviewable Markdown/Math artifacts, including
  the model's native `.mmd` result where available;
- whether known Granite/Docling malformed formula markers and Task 347 vLLM
  pathology markers are absent or present;
- whether the candidate's output is visually/source-faithful enough to justify
  a later integration design task.

## PR Scope

- Update the Task 346 candidate matrix so DeepSeek-OCR-2 defaults to the
  single-image HF eager command template lane for page-image inputs.
- Keep PaddleOCR candidates as evaluated/rejected or blocked evidence; do not
  add CUDA shims or CPU fallback.
- Update the Task 347 HF command adapter default to the proven Hemma setting:
  `attn_implementation="eager"`.
- Preserve the upstream DeepSeek inference shape:
  `AutoTokenizer`, `AutoModel`, `trust_remote_code=True`, `use_safetensors=True`,
  and `model.infer(..., base_size=1024, image_size=768, crop_mode=True, save_results=True)`.
- Capture command stdout/stderr, host/inner metadata, `result.md`, `result.mmd`,
  and visual artifacts under the Task 346 evidence tree.
- Run model inference only on Hemma hardware through governed command surfaces.
- Record results in Task 346, Task 350, and `.codex/handoff.md`.

## Deliverables

- [x] Task 346 harness uses a DeepSeek-OCR-2 HF eager candidate spec.
- [x] Focused behavioral tests cover default candidate wiring, HF eager default
  attention, and captured `.mmd` artifacts.
- [x] Hemma Task 346 replay evidence bundle is generated with the HF eager
  command template and bounded timeout.
- [x] Manual/visual quality review of the resulting page outputs is recorded.
- [x] Task 346/350/handoff docs are updated with sanitized evidence and the
  next product recommendation.

## Acceptance Criteria

- [x] No DeepSeek-OCR-2 inference is run on the local Mac.
- [x] The default DeepSeek candidate no longer points at the rejected vLLM batch
  lane.
- [x] The HF command records `attn_implementation="eager"` in host/inner
  metadata.
- [x] The Task 346 report contains per-input status, elapsed time, output path,
  return code, marker counts, and bounded stdout/stderr paths.
- [x] Generated output is inspected against source page images before any
  recommendation is made.
- [x] Any timeout or crash is recorded as observed evidence rather than inferred
  from upstream examples.
- [x] Docs and code validation gates pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes

Primary upstream DeepSeek docs consulted on 2026-06-06:

- GitHub README: official Transformers inference uses
  `AutoTokenizer.from_pretrained(..., trust_remote_code=True)`,
  `AutoModel.from_pretrained(..., trust_remote_code=True, use_safetensors=True)`, the document-to-Markdown prompt, and
  `model.infer(..., base_size=1024, image_size=768, crop_mode=True, save_results=True)`.
- Hugging Face model card: the model is published as an
  Image-Text-to-Text/Transformers/custom-code model under
  `deepseek-ai/DeepSeek-OCR-2`.

Task 347 already proved that `attn_implementation="sdpa"` fails before
generation for this model on the Hemma HF lane, while
`attn_implementation="eager"` produced coherent page-14 Markdown/Math output
on the same rendered PNG in `159262 ms`.

## Implementation and Run Results

Implemented 2026-06-06:

- `task346_formula_candidate_eval_candidates.py` now declares
  `deepseek_ocr2_hf_eager` as the default DeepSeek page-image candidate using
  the single-image command template lane.
- `task347_deepseek_ocr2_hf_command.py` now defaults
  `--attn-implementation` to `eager`, matching the Task 347 Hemma control
  evidence.
- `test_task346_formula_candidate_eval.py` proves native `.mmd` artifact
  capture and default candidate wiring.
- `test_task347_deepseek_ocr2_hf_command.py` proves the HF command parser and
  Docker command forward eager attention without local model inference.

Hemma replay command:

```bash
pdm run hemma-command-start task350-deepseek-hf-eager-task346-replay -- /bin/bash -lc 'set -euo pipefail; cd /home/paunchygent/apps/sir-convert-a-lot; /home/paunchygent/.local/bin/pdm run task346-formula-candidate-eval --output-dir build/verification/task-350-deepseek-hf-eager-task346-replay --candidate-timeout-seconds 1200 --deepseek-ocr2-command "/home/paunchygent/.local/bin/pdm run task347-deepseek-ocr2-hf-command --input {input} --output-dir {output_dir} --model {model} --inner-timeout-seconds 1000 --host-timeout-seconds 1100"'
```

Generated evidence:

```text
build/verification/task-350-deepseek-hf-eager-task346-replay/task346-formula-candidate-eval-20260606T201448Z/report.json
build/verification/task-350-deepseek-hf-eager-task346-replay/task346-formula-candidate-eval-20260606T201448Z/report.md
build/verification/task-350-deepseek-hf-eager-task346-replay/task346-formula-candidate-eval-20260606T201448Z/visual-review.html
```

Summary:

| Candidate | Status | Inputs | Elapsed ms | Known markers |
| --- | ---: | ---: | ---: | --- |
| `granite_docling_baseline` | `succeeded` | `1` | `249740` | `</formula=36`, `\mathbmath=59`, `\mathbf=304`, `l o o l y=1` |
| `source_layer_pymupdf` | `succeeded` | `40` | `88` | all known markers `0` |
| `unimernet_paddleocr` | `blocked` | `36` | n/a | `candidate_executable_not_found` |
| `pp_formulanet_plus_s_paddleocr` | `blocked` | `36` | n/a | `candidate_executable_not_found` |
| `deepseek_ocr2_hf_eager` | `succeeded` | `4` | `676555` | `</formula=0`, `\mathbmath=0`, `\mathbf=130`, `l o o l y=0` |

DeepSeek-OCR-2 HF eager per-page results:

| Input | Status | Elapsed ms | Return code | Output chars | Native `.mmd` bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `page-13` | `succeeded` | `211817` | `0` | `6218` | `6212` |
| `page-14` | `succeeded` | `183691` | `0` | `5291` | `5285` |
| `page-15` | `succeeded` | `140573` | `0` | `3151` | `3147` |
| `page-16` | `succeeded` | `140461` | `0` | `3920` | `3974` |

Host and inner metadata recorded `attn_implementation="eager"` for all four
pages. The model's Python return value is not the usable artifact (`result.md`
contains `None`); the faithful output surface is the model-saved `result.mmd`
plus `result_with_boxes.jpg`.

Pathology scan:

- No observed vLLM repetition markers in any `result.mmd`: `arodarod`,
  `manship`, `十条`, `她们`, or `<｜begin`.
- No observed Task 344 malformed markers in any `result.mmd`: `</formula`,
  `\mathbmath`, or `l o o l y`.
- `\mathbf` appears in pages 13 and 14 because it is legitimate source math,
  so it is not by itself a failure marker for this candidate.

Manual/visual review:

- Page 14 source image and DeepSeek box overlay aligned well on text and
  equation regions, and the Markdown/Math output is coherent.
- Page 14 still contains at least one malformed inline math/prose segment around
  the sentence beginning "Updating ... is trivial" where a math delimiter is
  not faithfully closed.
- Page 13 ends mid-equation in the source page; DeepSeek emits an incomplete or
  odd continuation shape at that boundary.
- Page 15 is mostly coherent but contains OCR-like prose/entity errors such as
  model-name spacing mistakes.
- Page 16 table output preserves broad structure with HTML tables but includes
  entity escaping, spacing, and table-transcription artifacts.

Recommendation: promote DeepSeek-OCR-2 HF eager to a later governed integration
design/evaluation task, but only behind source-backed authority,
page-window/cross-page reconciliation, and best-effort representation policy.
Do not use it as a blind overwrite path for born-digital formula regions.

## Validation

- Red-first local focused test failed as expected before implementation:
  default DeepSeek candidate was still the vLLM batch lane and HF default
  attention was still `sdpa`.
- Local focused tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_task346_formula_candidate_eval.py tests/sir_convert_a_lot/test_task347_deepseek_ocr2_hf_command.py`
  -> `9 passed`.
- Hemma focused tests:
  `/home/paunchygent/.local/bin/pdm run pytest-root tests/sir_convert_a_lot/test_task346_formula_candidate_eval.py tests/sir_convert_a_lot/test_task347_deepseek_ocr2_hf_command.py`
  -> `9 passed`.
- Close-out gates:
  focused `ruff format`, focused `ruff check --fix`, focused mypy, focused
  `pytest-root`, diagnostics-focused `pytest-root`,
  `pdm run typecheck-all`, `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.
