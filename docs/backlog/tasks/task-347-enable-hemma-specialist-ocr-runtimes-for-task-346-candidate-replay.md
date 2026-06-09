---
id: task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay
title: Enable Hemma specialist OCR runtimes for Task 346 candidate replay
type: task
status: completed
priority: high
created: '2026-06-06'
last_updated: '2026-06-06'
related:
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/backlog/tasks/task-345-make-source-layer-formula-evidence-authoritative-for-born-digital-pdfs.md
  - docs/backlog/tasks/task-343-investigate-pdf-conversion-decision-logic-and-gpu-cpu-performance-attribution.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - scripts/sir_convert_a_lot/devops/formula_candidate_eval.py
  - scripts/sir_convert_a_lot/devops/deepseek_ocr2_vllm_batch.py
  - scripts/sir_convert_a_lot/devops/deepseek_ocr2_hf_command.py
  - scripts/sir_convert_a_lot/devops/paddle_formula_command.py
labels:
  - pdf
  - formula
  - ocr
  - gpu
  - hemma
  - paddleocr
  - deepseek-ocr
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Boundary

The user intent is to finish the runtime-enablement slice that unblocks Task
346, then rerun the Task 346 harness with specialist candidates on Hemma
hardware.

PaddleOCR and DeepSeek-OCR-2 inference must run on Hemma only. The local Mac
may be used for docs-as-code, code scaffolding, static validation, and unit
tests that do not exercise model inference. Candidate runtime compatibility,
quality, and performance evidence must come from the canonical Hemma checkout
and Hemma GPU/runtime surfaces.

This task does not promote PaddleOCR or DeepSeek-OCR-2 into production
conversion routing. It enables and exercises the candidate replay lane so Task
346 can move from runtime blockers to observed candidate evidence.

## Objective

Enable governed Hemma command surfaces for the Task 346 specialist OCR
candidates, then rerun the Task 346 harness on the established pages `13-16`
incident inputs with:

- UniMERNet through PaddleOCR formula recognition,
- PP-FormulaNet through PaddleOCR formula recognition,
- DeepSeek-OCR-2 through a project-owned command adapter,
- the existing Granite/Docling and PyMuPDF evidence baselines.

The result must be a refreshed Task 346 evidence bundle with actual candidate
outputs, timings, device/runtime facts where available, and concrete blockers
for any runtime that cannot execute on Hemma GPU.

## PR Scope

- Keep the candidate harness adapter-based; do not add production formula
  routing or public user-facing conversion flags in this task.
- Add a project-owned DeepSeek-OCR-2 single-image command adapter that Task 346
  can invoke through `--deepseek-ocr2-command`.
- Ensure the Task 346 harness reads candidate text artifacts written by external
  commands, not only stdout or JSON fields.
- Use PaddleOCR's official formula-recognition command shape:
  `paddleocr formula_recognition_pipeline -i <image> --device gpu`.
- Use DeepSeek-OCR-2 official inference shape as the model API source:
  `AutoTokenizer`, `AutoModel`, `trust_remote_code=True`, and
  `model.infer(...)` with the document-to-Markdown prompt.
- Store Hugging Face caches under the Hemma scratch cache contract:
  `/srv/scratch/sir-convert-a-lot/cache/huggingface`.
- Install or probe candidate runtime dependencies only on Hemma. Do not perform
  local PaddleOCR or DeepSeek-OCR-2 inference.
- Rerun Task 346 from the canonical Hemma repo root. If local uncommitted
  harness changes are not present on Hemma, stage only the task-scoped files
  needed to run the governed replay.
- Record every runtime blocker as observed command output, not inferred
  compatibility.

## Deliverables

- [x] Governed Task 347 document with Hemma-only runtime boundary.
- [x] Task 346 harness patch so external text/Markdown artifacts are evaluated.
- [x] DeepSeek-OCR-2 vLLM command adapter for Task 346.
- [x] Minimal DeepSeek-OCR-2 HF eager control adapter for root-cause isolation.
- [x] PaddleOCR Hemma runtime probe/install attempt with GPU execution request.
- [x] DeepSeek-OCR-2 Hemma runtime/output probes against the established
  page-14/page-13-16 PNG inputs.
- [x] Task 346 and Task 347 updated with observed runtime/output results.

## Acceptance Criteria

- [x] No PaddleOCR or DeepSeek-OCR-2 candidate inference is run on the local Mac.
- [x] Hemma runtime facts show the active Torch/GPU state before DeepSeek replay.
- [x] PaddleOCR candidates either run with `--device gpu` on Hemma or produce a
  precise observed blocker.
- [x] DeepSeek-OCR-2 either runs on Hemma GPU through the task-owned command
  adapter or produces a precise observed blocker.
- [x] DeepSeek-OCR-2 output quality is inspected before promoting it as a
  usable Task 346 candidate.
- [x] Known bad marker counts are reported for successful DeepSeek probes.
- [x] Generated artifacts stay under `build/verification/` or Hemma scratch
  roots; no model cache or large generated working tree is created on `/`.
- [x] Focused tests pass; docs validation remains a close-out gate after index
  sync.

## Implementation Notes

Primary docs consulted before implementation:

- PaddleOCR formula-recognition pipeline docs: the official CLI accepts
  `paddleocr formula_recognition_pipeline -i <image> --device gpu`; the Python
  pipeline also accepts `FormulaRecognitionPipeline(device="gpu")`.
- PaddleOCR module docs: formula recognition can be invoked with
  `FormulaRecognition(model_name="PP-FormulaNet_plus-M")` and
  `model.predict(..., batch_size=1)`.
- PaddlePaddle install docs: current pip GPU examples are CUDA-indexed
  `paddlepaddle-gpu` wheels. This is not treated as a conclusion about Hemma;
  the task must still probe the official runtime on Hemma and record the real
  outcome.
- DeepSeek-OCR-2 docs: official Transformers inference uses
  `AutoTokenizer.from_pretrained(..., trust_remote_code=True)`,
  `AutoModel.from_pretrained(..., trust_remote_code=True, use_safetensors=True)`, prompt
  `<image>\n<|grounding|>Convert the document to markdown.`, and
  `model.infer(..., base_size=1024, image_size=768, crop_mode=True)`.

DeepSeek-OCR-2 current vLLM documentation was also checked. The current vLLM
recipe imports `vllm.model_executor.models.deepseek_ocr`, but the AMD image
available for the requested `0.8.5` compatibility lane
(`rocm/vllm:rocm6.3.1_vllm_0.8.5_20250521`) actually reports
`vllm 0.8.6.dev315+...rocm631` and does not contain that built-in module.
The only runnable vLLM path on this image is therefore the DeepSeek repository
`DeepSeek-OCR2-vllm` script shape with model registration, repository
processor, and repository n-gram logits processor.

## Runtime Results

PaddleOCR:

- Hemma isolated runtime install used `paddleocr 3.6.0` plus the official
  `paddlepaddle-gpu==3.3.0` wheel index published for CUDA.
- Import failed on Hemma ROCm with `ImportError: libcuda.so.1: cannot open shared object file`.
- This proves only that the tested pip CUDA wheel path is blocked on Hemma
  ROCm. It does not prove that PaddleOCR formula recognition cannot run through
  a native AMD/ROCm PaddleOCR/PaddleX runtime.
- CUDA shim or translation approaches are explicitly not a continuation
  candidate. The next valid Paddle lane is Task 348: probe the official/native
  PaddleOCR-VL or PaddleX AMD GPU container and verify whether it exposes the
  formula-recognition APIs/models needed by Task 346. Only after that container
  lane is exhausted should a separate governed ROCm PaddlePaddle build task be
  considered.

DeepSeek-OCR-2 vLLM compatibility probes:

- The DXE-proven newer vLLM image failed import compatibility:
  `ImportError: cannot import name 'SamplingMetadata' from 'vllm.model_executor'`.
- The AMD `vllm-dev` tag advertised as `0.8.5` reported a `0.7.4.dev` vLLM and
  failed the DeepSeek processor hash-contract call.
- The AMD `rocm/vllm:rocm6.3.1_vllm_0.8.5_20250521` image reported
  `vllm 0.8.6.dev315+...rocm631`; it required:
  - a processor adapter for vLLM 0.8's `return_mm_hashes` contract,
  - `block_size=16` because ROCm custom paged attention rejects the upstream
    `block_size=256`,
  - `gpu_memory_utilization=0.45` on the shared Hemma host to avoid HIP OOM
    beside the production service,
  - the official `<image>\n<|grounding|>Convert the document to markdown.`
    prompt placeholder.
- With those runtime fixes and the GitHub script-aligned settings
  (`disable_mm_preprocessor_cache=True`, repo
  `NoRepeatNGramLogitsProcessor(ngram_size=20, window_size=50)`,
  `include_stop_str_in_output=True`), four page PNG inputs completed in
  `179673 ms`, but all four outputs ended with `finish_reason="length"` and
  repeated impossible token strings.

DeepSeek-OCR-2 vLLM output evidence:

```text
build/verification/task-347-deepseek-vllm-github-script-aligned-probe-20260606T1918/
```

Observed markers:

| Input | Finish | Output chars | Observed pathology markers |
| --- | --- | ---: | --- |
| `page-13.png` | `length` | `32860` | `arodarod=1545`, `manship=1161` |
| `page-14.png` | `length` | `26174` | `arodarod=1393`, `manship=991`, `十条=1038`, `她们=935`, `ntent=95`, `escalation=7` |
| `page-15.png` | `length` | `25258` | `arodarod=1353`, `manship=839`, `十条=1163`, `她们=861`, `ntent=11`, `escalation=4` |
| `page-16.png` | `length` | `26295` | `arodarod=1593`, `manship=618`, `十条=919`, `她们=688`, `ntent=221`, `escalation=49` |

DeepSeek-OCR-2 vLLM eager control:

```text
build/verification/task-347-deepseek-page14-eager-probe-20260606T1928/
```

- Same page-14 PNG, same DeepSeek repository processor, `enforce_eager=True`.
- Completed one page in `179259 ms`, with generation progress `136.74s/it`.
- Output still ended with `finish_reason="length"` and repeated
  `<｜begin▁of▁sentence｜>`.
- This rules out CUDA graph capture as the only cause. Graph mode is faster;
  eager mode changes the bad token loop but does not fix it.

DeepSeek-OCR-2 HF eager control:

```text
build/verification/task-347-deepseek-page14-hf-eager-control-20260606T1945/
```

- Same page-14 PNG on Hemma, same DeepSeek-OCR-2 model, non-vLLM
  `AutoModel.infer(...)`, `attn_implementation="eager"`.
- Completed in `159262 ms`.
- Wrote coherent Markdown/Math output to `result.mmd` (`5285` bytes), plus
  `result_with_boxes.jpg`.
- The observed vLLM pathology markers were absent from `result.mmd`.
- `attn_implementation="sdpa"` failed before generation with the explicit
  Transformers error that `DeepseekOCR2ForCausalLM` does not support SDPA and
  should be loaded with `attn_implementation="eager"`.

Root-cause conclusion from this task:

- The rendered PNG inputs are valid for DeepSeek-OCR-2: HF eager transcribes
  page 14 coherently from the exact same image.
- The DeepSeek-OCR-2 model itself is not the cause of the observed gibberish.
- The current Hemma DeepSeek vLLM lane is the failing layer. The failure is in
  the vLLM/ROCm DeepSeek-MoE decode path, consistent with upstream vLLM issue
  reports for DeepSeek-VL2/DeepSeekMoE gibberish/repetition traced to attention
  decode behavior.
- The current vLLM lane must not be promoted as a Task 346 quality candidate.
  The next governed integration direction is either the HF eager path, with
  explicit performance/memory controls, or a different vLLM runtime where the
  built-in DeepSeek-OCR module and ROCm decode path are proven on Hemma.

## Recommendation

- Do not use the current DeepSeek-OCR-2 vLLM ROCm path for production formula
  or page OCR integration.
- Keep the vLLM adapter as a diagnostic artifact only until a fixed/runtime
  image is proven.
- Promote a follow-up integration task around the HF eager path if DeepSeek is
  still desired as the specialist OCR candidate. That task must add bounded
  page/crop execution, memory controls, output artifact capture from `.mmd`,
  and Task 346 harness integration before any production routing decision.
- Keep the pip CUDA-wheel PaddleOCR path blocked. Continue PaddleOCR only
  through Task 348's official/native AMD GPU container probe. If that lane does
  not expose formula recognition, stop and decide whether to create a separate
  governed ROCm PaddlePaddle build task.

## Validation Evidence

- Local focused gates:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_deepseek_ocr2_vllm_batch.py`
    -> `3 passed`.
  - `pdm run ruff check scripts/sir_convert_a_lot/devops/deepseek_ocr2_vllm_batch.py tests/sir_convert_a_lot/test_deepseek_ocr2_vllm_batch.py`
    -> passed.
  - `pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/devops/deepseek_ocr2_vllm_batch.py tests/sir_convert_a_lot/test_deepseek_ocr2_vllm_batch.py`
    -> no issues.
  - `pdm run ruff check scripts/sir_convert_a_lot/devops/deepseek_ocr2_hf_command.py`
    -> passed.
  - `pdm run mypy --no-incremental --config-file pyproject.toml scripts/sir_convert_a_lot/devops/deepseek_ocr2_hf_command.py`
    -> no issues.
- Hemma focused gates after sync:
  - `pdm run run-hemma --shell '/home/paunchygent/.local/bin/pdm run pytest-root tests/sir_convert_a_lot/test_deepseek_ocr2_vllm_batch.py'`
    -> `3 passed`.
  - `pdm run run-hemma --shell '/home/paunchygent/.local/bin/pdm run ruff check scripts/sir_convert_a_lot/devops/deepseek_ocr2_vllm_batch.py tests/sir_convert_a_lot/test_deepseek_ocr2_vllm_batch.py'`
    -> passed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
