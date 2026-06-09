---
id: task-348-probe-paddleocr-vl-and-paddlex-amd-gpu-container-support-for-formula-recognition-on-hemma
title: Probe PaddleOCR-VL and PaddleX AMD GPU container support for formula recognition on Hemma
type: task
status: completed
priority: high
created: '2026-06-06'
last_updated: '2026-06-06'
related:
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/backlog/tasks/task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
  - scripts/sir_convert_a_lot/devops/paddle_formula_command.py
labels:
  - pdf
  - formula
  - ocr
  - paddleocr
  - paddlex
  - rocm
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## User Intent and Boundary

The user intent is to continue PaddleOCR runtime investigation only through
native AMD/ROCm-compatible lanes. CUDA shim or CUDA translation approaches are
not viable candidates for this product direction and must not be explored in
this task.

This task is a bounded Hemma-only runtime probe. It must first exhaust the
official PaddleOCR-VL/PaddleX AMD GPU container path and verify whether that
runtime can execute the formula-recognition models needed by Task 346. If that
path does not support formula recognition, stop and record evidence. A governed
ROCm PaddlePaddle build path is a separate follow-up decision, not work to
start inside this task.

## Objective

Probe whether the official/native PaddleOCR-VL or PaddleX AMD GPU container
can run PaddleOCR formula-recognition inference on Hemma's AMD GPU and support
the model family needed by Task 346:

- `FormulaRecognitionPipeline(..., device="gpu")`,
- `FormulaRecognition(model_name="PP-FormulaNet_plus-M", device="gpu")`,
- `FormulaRecognition(model_name="PP-FormulaNet_plus-S", device="gpu")` when
  available,
- UniMERNet support only if exposed by the same official/native runtime.

The result must answer whether PaddleOCR can become a Task 346 candidate
through an official/native AMD container lane, without any CUDA shim.

## PR Scope

- Use Hemma only for runtime execution.
- Use the repo's sanctioned Hemma wrappers and detached-run standard for any
  long container probe.
- Probe the official PaddleOCR-VL AMD GPU Docker image documented by PaddleOCR:
  `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-amd-gpu`.
- Check whether the container includes PaddleOCR/PaddleX APIs for formula
  recognition, not only OCR-VL.
- Check the effective PaddlePaddle runtime from inside the container:
  `paddle.device.is_compiled_with_rocm()`, `paddle.device.is_compiled_with_cuda()`,
  visible devices, and package versions.
- Run one small formula crop from the existing Task 346 inputs if and only if
  the formula-recognition API and model are available.
- Write evidence under `build/verification/task-348-paddleocr-amd-container/`.
- Do not test ZLUDA, SCALE, CUDA shims, or other CUDA translation layers.
- Do not begin a source build of PaddlePaddle in this task.

## Deliverables

- [x] Hemma runtime probe log for the official/native AMD GPU container.
- [x] API/model inventory showing whether formula recognition is available.
- [x] Runtime truth payload showing ROCm/CUDA compile/device state from inside
  the container.
- [x] Formula-recognition smoke attempt on an existing Task 346 crop if
  supported.
- [x] Precise blocker when the AMD container exposes formula recognition but
  cannot execute it on Hemma.
- [x] Recommendation: reject the current official AMD container for Task 346
  formula recognition on Hemma unless a separate governed PaddlePaddle/PaddleX
  AMD GPU compatibility/build task proves the native kernel failure is fixed.

## Acceptance Criteria

- [x] No CUDA shim/translation layer is installed, probed, or recommended.
- [x] The official/native AMD GPU container path is checked before any build
  discussion.
- [x] Formula-recognition support is verified by import/API/model availability,
  not inferred from OCR-VL support.
- [x] Any formula inference attempt uses Hemma GPU runtime and an existing Task
  346 crop/page input. No successful inference artifact was produced because
  the native GPU process aborted.
- [x] If formula recognition is absent, the task stops after documenting the
  blocker and does not proceed to a ROCm source build. In this run, formula
  APIs and model downloads were present, but execution failed natively.
- [x] If a ROCm PaddlePaddle source build is needed, it is proposed as a
  separate governed task with build/load safety requirements.

## Source Notes

Current documentation checked 2026-06-06:

- PaddleOCR FormulaRecognition docs expose `FormulaRecognition` and
  `FormulaRecognitionPipeline`, with `device` values including `gpu`,
  `gpu:0`, and multi-GPU forms.
- Formula recognition defaults to `PP-FormulaNet_plus-M` when no model name is
  supplied and returns `rec_formula` LaTeX output.
- PaddleOCR formula-recognition CLI supports
  `paddleocr formula_recognition_pipeline -i <image> --device gpu`.
- PaddleOCR-VL AMD GPU docs expose a native AMD GPU container:
  `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-amd-gpu`.

Interpretation:

- The previous Task 347 blocker only proves the pip CUDA wheel path fails on
  Hemma ROCm via `libcuda.so.1`.
- It does not prove PaddleOCR formula recognition cannot run on ROCm.
- The next valid probe is the official/native AMD container plus formula API
  support, not a CUDA compatibility adapter.

## Runtime Evidence

Evidence root:
`build/verification/task-348-paddleocr-amd-container/`.

Official image:
`ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddleocr-vl:latest-amd-gpu`.
Hemma pulled image digest
`sha256:8c9b37594a10d9eb48d0cb37acf07933eb352bcbbc44f703641a1592b9f9382b`
with reported size `15.6GB`.

Inventory-only probe:
`task348-paddleocr-amd-inventory-20260606T2015/task348-paddleocr-amd-probe.json`.
The container imported `paddle` `3.4.0.dev20260123`, `paddleocr` `3.6.0`,
and `paddlex` `3.6.1`. Runtime truth from inside the container reported
`paddle.device.get_device() == "gpu:0"`,
`is_compiled_with_rocm() == true`, and `is_compiled_with_cuda() == true`.
PaddleOCR exposed both `FormulaRecognition` and
`FormulaRecognitionPipeline`; the probe recorded candidate model names
`PP-FormulaNet_plus-M`, `PP-FormulaNet_plus-S`, and `UniMERNet`.

Pipeline smoke:
`task348-paddleocr-amd-smoke-20260606T2017` used the existing Task 346 crop
`p14-texts-50.png`. It entered `FormulaRecognitionPipeline`, downloaded
pipeline dependencies including `PP-LCNet_x1_0_doc_ori`, `UVDoc`, and
`PP-DocLayout_plus-L`, then aborted in native Paddle GPU execution before
formula output. The failing trace hit an Eigen GPU slice assertion:
`hipGetLastError() == hipSuccess`, followed by `SIGABRT`.

Direct `PP-FormulaNet_plus-M` smoke:
`task348-paddleocr-amd-direct-formula-smoke-20260606T2048` used
`FormulaRecognition(model_name="PP-FormulaNet_plus-M", device="gpu")` on the
same Task 346 crop. The official model files downloaded successfully, then
the native process aborted in `AnalysisPredictor::ZeroCopyRun` through
`ConvCudnnKernel` and `PadFunction`, ending at the Eigen GPU padding assertion
`hipGetLastError() == hipSuccess` and `SIGABRT`. The pre-smoke inventory JSON
was preserved, but no formula result JSON was produced because the Python
process was terminated by the native runtime.

Direct `PP-FormulaNet_plus-S` smoke:
`task348-paddleocr-amd-direct-formula-s-smoke-20260606T2110` repeated the
direct `FormulaRecognition` probe with `PP-FormulaNet_plus-S`. The official
model files downloaded successfully, then failed in the same native
`ConvCudnnKernel` / `PadFunction` / Eigen GPU padding assertion path with
`hipGetLastError() == hipSuccess` and `SIGABRT`.

## Result

The official/native PaddleOCR-VL AMD GPU container is real, pulls on Hemma,
imports PaddleOCR/PaddleX, reports ROCm-enabled GPU runtime, and exposes the
formula-recognition APIs and official PP-FormulaNet models. It is therefore
not merely an OCR-VL-only container.

The container is not currently usable as a Task 346 formula-recognition lane
on Hemma because both direct formula models tested (`PP-FormulaNet_plus-M` and
`PP-FormulaNet_plus-S`) abort in the same native Paddle GPU convolution/padding
path before producing any formula output. This is an operational native
Paddle/HIP kernel compatibility failure, not a CUDA-shim issue and not absence
of formula-recognition APIs.

## Recommendation

Do not integrate the current official PaddleOCR-VL AMD GPU container into the
conversion pipeline for Task 346. Do not test CUDA shims or translation
layers.

If PaddleOCR remains a desired candidate, create a separate governed task for
PaddlePaddle/PaddleX AMD GPU compatibility remediation. That follow-up should
start from the recorded native `ConvCudnnKernel` / `PadFunction` HIP assertion,
use the same Task 346 crop and model names, and only proceed to a ROCm
PaddlePaddle build or image pin if it can prove the direct `FormulaRecognition`
smoke succeeds on Hemma.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
