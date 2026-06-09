---
id: 'task-349-probe-official-amd-paddlex-paddle-vllm-container-for-paddleocr-formula-recognition-on-hemma'
title: 'Probe official AMD PaddleX Paddle/vLLM container for PaddleOCR formula recognition on Hemma'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-06'
last_updated: '2026-06-06'
related:
  - docs/backlog/tasks/task-346-evaluate-specialist-formula-ocr-candidates-before-formula-lane-infrastructure.md
  - docs/backlog/tasks/task-347-enable-hemma-specialist-ocr-runtimes-for-task-346-candidate-replay.md
  - docs/backlog/tasks/task-348-probe-paddleocr-vl-and-paddlex-amd-gpu-container-support-for-formula-recognition-on-hemma.md
  - docs/runbooks/runbook-hemma-gpu-runtime.md
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

## Objective

Probe the official AMD/PaddleX Paddle/vLLM ROCm container documented in AMD's
2026 PaddleOCR-VL-1.5 ROCm guide before any PaddlePaddle source-build or image
remediation work:

`ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-paddle-vllm-amd-gpu:3.4.0-0.14.0rc2`.

The task must answer whether this official/native AMD container can execute
PaddleOCR formula-recognition inference on Hemma's AMD GPU for the Task 346
formula crop that failed in Task 348.

## PR Scope

- Use Hemma only for runtime execution.
- Use the existing Task 348 probe script with an image override unless the
  container requires a small committed wrapper adaptation.
- First run inventory-only:
  - container image digest and size,
  - `paddle`, `paddleocr`, and `paddlex` import/version status,
  - `paddle.device.get_device()`,
  - ROCm/CUDA compile truth,
  - presence/absence of `FormulaRecognition` and `FormulaRecognitionPipeline`.
- If and only if formula APIs are available, run direct
  `FormulaRecognition(model_name="PP-FormulaNet_plus-M", device="gpu")` on
  Task 346 crop `p14-texts-50.png`.
- If `PP-FormulaNet_plus-M` fails after model availability is proven, run
  `PP-FormulaNet_plus-S` only if the first failure is not an environmental
  import/runtime absence.
- Write evidence under
  `build/verification/task-349-paddlex-amd-container/`.
- Do not test ZLUDA, SCALE, CUDA shims, or other CUDA translation layers.
- Do not begin a PaddlePaddle source build in this task.

## Deliverables

- [x] Hemma runtime probe log for the official AMD/PaddleX container.
- [x] API/model inventory showing whether PaddleOCR formula recognition is
  available in the container.
- [x] Runtime truth payload showing ROCm/CUDA compile/device state from inside
  the container.
- [x] Formula-recognition smoke output or native failure trace on the existing
  Task 346 crop. Not attempted because the container lacks `paddleocr` and the
  formula APIs.
- [x] Recommendation: reject this container for Task 346 PaddleOCR formula
  recognition because formula recognition is absent, not merely failing at
  runtime.

## Acceptance Criteria

- [x] No CUDA shim/translation layer is installed, probed, or recommended.
- [x] The official AMD/PaddleX container path is checked before any source-build
  discussion.
- [x] Formula-recognition support is verified by import/API/model availability,
  not inferred from PaddleOCR-VL document-parsing support.
- [x] Any formula inference attempt uses Hemma GPU runtime and an existing Task
  346 crop/page input. No formula inference was attempted because the inventory
  showed formula recognition is absent.
- [x] If formula recognition is absent, the task stops after documenting the
  blocker and does not proceed to a ROCm source build.
- [x] If formula recognition is present but fails natively, the native trace is
  compared to the Task 348 `ConvCudnnKernel` / `PadFunction` HIP assertion
  before recommending next work. Formula recognition was absent, so this branch
  was not reached.
- [x] If a PaddlePaddle/PaddleX AMD GPU source build or image pin is needed, it
  is proposed as a separate governed task with heavy-load safety requirements.

## Source Notes

Current documentation checked 2026-06-06:

- Context7 PaddleOCR docs expose `FormulaRecognition` and
  `FormulaRecognitionPipeline`, including GPU device selection and
  `PP-FormulaNet_plus-M` usage.
- The PaddleOCR-VL docs say AMD GPU is a supported hardware guide for
  PaddlePaddle inference and warn that full PaddleOCR-VL pipeline behavior is
  not equivalent to using only an isolated VLM component.
- AMD's January 29, 2026 PaddleOCR-VL-1.5 ROCm article documents the
  official container
  `ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-paddle-vllm-amd-gpu:3.4.0-0.14.0rc2`,
  states that it includes PaddlePaddle compiled with ROCm support, vLLM,
  PaddleX, and PaddleOCR-VL dependencies, and shows native PaddlePaddle
  inference as one supported backend.

Interpretation:

- Task 348 exhausted the official `paddleocr-vl:latest-amd-gpu` image for
  direct PP-FormulaNet formula recognition and found native Paddle GPU aborts.
- Task 348 did not exhaust the separate official AMD/PaddleX container named
  in AMD's PaddleOCR-VL-1.5 ROCm guide.
- Therefore Task 349 must probe this official/native container before any
  source-build or compatibility-remediation task.

## Runtime Evidence

Evidence root:
`build/verification/task-349-paddlex-amd-container/`.

Official image:
`ccr-2vdh3abv-pub.cnc.bj.baidubce.com/paddlepaddle/paddlex-paddle-vllm-amd-gpu:3.4.0-0.14.0rc2`.
Hemma pulled image digest
`sha256:416a0aaf108688e9e1c000d2c238093aa194654d80df11b5c4d086d6f8db56d0`
with reported size `37.4GB`.

Initial probe:
`task349-paddlex-amd-inventory-20260606T2134`. This run proved an important
container-behavior detail: the image has a service-first entrypoint that
starts the OneClick Jupyter/vLLM flow and ignores the probe command unless the
entrypoint is overridden. The mislaunched container was stopped and the probe
script was extended with an explicit `--entrypoint-bash` option.

Corrected inventory probe:
`task349-paddlex-amd-inventory-entrypoint-20260606T2202/task348-paddleocr-amd-probe.json`.
The container imported `paddle` `3.4.0.dev20260123` and `paddlex` `3.3.0`.
It reported `paddle.device.get_device() == "gpu:0"`,
`is_compiled_with_rocm() == true`, and `is_compiled_with_cuda() == true`.
The container did not import `paddleocr`; import failed with
`ModuleNotFoundError: No module named 'paddleocr'`.

Formula API result:

- `FormulaRecognition`: `false`
- `FormulaRecognitionPipeline`: `false`
- `formula_smoke.status`: `not_attempted`

## Result

The official AMD/PaddleX Paddle/vLLM container is a valid ROCm-enabled
Paddle/PaddleX environment for PaddleOCR-VL workflows, but it is not currently
a PaddleOCR formula-recognition runtime. It does not contain the `paddleocr`
package or the `FormulaRecognition` / `FormulaRecognitionPipeline` APIs needed
to run PP-FormulaNet formula recognition on the Task 346 crops.

This is different from Task 348:

- Task 348's `paddleocr-vl:latest-amd-gpu` image exposed PaddleOCR formula
  APIs but failed in native Paddle GPU kernels for `PP-FormulaNet_plus-M` and
  `PP-FormulaNet_plus-S`.
- Task 349's `paddlex-paddle-vllm-amd-gpu:3.4.0-0.14.0rc2` image is
  ROCm-enabled but lacks PaddleOCR formula-recognition APIs entirely.

## Recommendation

Do not integrate this official AMD/PaddleX Paddle/vLLM container as a Task 346
formula-recognition candidate. Do not proceed to formula smoke from this image
unless a future governed task first installs or selects an official runtime
that exposes `paddleocr.FormulaRecognition`.

The remaining Paddle continuation is no longer "try another official container"
unless a new official image is identified. It should be a separate governed
compatibility/remediation task that starts from the combined Task 348 and Task
349 evidence:

- one official image exposes formula APIs but aborts in native Paddle HIP
  kernels,
- the other official AMD/PaddleX image has ROCm Paddle but lacks PaddleOCR
  formula APIs.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
