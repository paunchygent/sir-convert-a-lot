---
type: runbook
id: RUN-hemma-devops-and-gpu
title: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
status: active
created: '2026-02-11'
updated: '2026-03-05'
owners:
  - platform
system: hemma.hule.education
tags:
  - devops
  - hemma
  - gpu
  - sir-convert-a-lot
links:
  - .agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md
  - docs/runbooks/runbook-v2-async-push-delivery.md
  - docs/converters/downstream_integration_contract_v2.md
  - /Users/olofs_mba/Documents/Repos/huledu-reboot/docs/runbooks/hemma-server-operations-huleedu.md
  - /Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/docs/runbooks/runbook-home-server.md
---

## Purpose

Standardize how `sir-convert-a-lot` is operated on Hemma with GPU-first behavior, while
remaining aligned with existing HuleEdu and Skriptoteket server patterns.

## Canonical Hemma Repo Map

- `~/apps/sir-convert-a-lot`: canonical repo path for this service.
- `~/apps/huleedu`: HuleEdu stack + ML offload services.
- `~/apps/skriptoteket`: Skriptoteket stack.
- `~/infrastructure`: nginx-proxy/certbot and shared edge infra.
- `~/apps/shared-postgres` (container-level service): shared DB host via Docker network.
- `/home/paunchygent/llama.cpp-rocm`: ROCm llama.cpp build context (shared GPU tooling).

## Canonical Client Access Policy

Only these client lanes are canonical for conversion calls:

- Tunnel lane: `http://127.0.0.1:28085`
- Internet lane: `https://convert.hule.education`

Do not use superseded client lanes such as `127.0.0.1:8085` or `127.0.0.1:18085`.

## Repo Placement Policy (`~/apps`)

- Sir Convert-a-Lot must be hosted at:
  - `/home/paunchygent/apps/sir-convert-a-lot`
- Do not run production/devops commands from ad hoc copies in `/home/paunchygent` root.
- If the repo is missing from `~/apps`, create/repair it first:

```bash
ssh hemma "/bin/bash -lc 'mkdir -p /home/paunchygent/apps && cd /home/paunchygent/apps && git clone git@github.com:paunchygent/sir-convert-a-lot.git'"
```

- If a misplaced copy exists outside `~/apps`, prefer reclone or clean move to `~/apps` and
  then set:

```bash
export SIR_CONVERT_A_LOT_HEMMA_ROOT=/home/paunchygent/apps/sir-convert-a-lot
```

- Verification command:

```bash
ssh hemma "/bin/bash -lc 'find /home/paunchygent -maxdepth 4 -type d -name sir-convert-a-lot 2>/dev/null | sort'"
```

## Command Context Rules

- Local PDM wrappers:
  - `pdm run run-local-pdm <script> [args]`
- Remote Hemma commands:
  - `pdm run run-hemma -- <command> [args]`
  - `pdm run run-hemma --shell "<command with operators>"`

Default remote context is:

- host: `hemma`
- repo root: `/home/paunchygent/apps/sir-convert-a-lot`

Overrides:

- `SIR_CONVERT_A_LOT_HEMMA_HOST`
- `SIR_CONVERT_A_LOT_HEMMA_ROOT`

Wrapper guarantees:

- Remote root is validated before execution (directory exists and is a git repo).
- Effective remote cwd is asserted to match the configured root.
- Wrapper fails fast on context mismatch:
  - `66`: remote root missing
  - `67`: remote root is not a git repo
  - `68`: remote cwd mismatch
- Commands run in deterministic shell mode (`bash --noprofile --norc`).
- Remote script is streamed over stdin to avoid quoting drift across SSH command parsing.

## SSH and Service Health

```bash
pdm run run-hemma -- pwd
pdm run run-hemma --shell 'command -v docker && docker --version'
pdm run run-hemma --shell 'sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'
```

## Containerized Runtime (Task 22 Command Surface)

Local canonical compose commands (repo root):

```bash
pdm run dev-build
pdm run dev-start
pdm run dev-check
pdm run dev-ps
pdm run dev-logs sir_convert_a_lot_prod
pdm run dev-config
pdm run dev-stop
```

Command-surface guarantees:

- `docker compose` v2 only (never `docker-compose`).
- Compose builds one shared runtime image (`sir-convert-a-lot-runtime:*`) and
  runs one canonical conversion service (`sir_convert_a_lot_prod`).
- Wrapper auto-derives `SIR_CONVERT_A_LOT_SERVICE_REVISION` from `git rev-parse HEAD`
  when unset, and defaults `SIR_CONVERT_A_LOT_EXPECTED_REVISION` to the same value.
- Health remains `/readyz`-gated, so stale/mismatched revision/profile/data-root
  configurations stay non-ready by contract.

Remote Hemma execution stays wrapper-driven (`run-hemma` argv mode):

```bash
pdm run run-hemma -- pdm run dev-build
pdm run run-hemma -- pdm run dev-start
pdm run run-hemma -- pdm run dev-check
pdm run run-hemma -- pdm run dev-logs sir_convert_a_lot_prod
pdm run run-hemma -- pdm run dev-stop
```

## GPU Verification (ROCm/HIP)

```bash
pdm run run-hemma -- rocminfo
pdm run run-hemma -- rocm-smi
pdm run run-hemma --shell 'sudo docker exec -it <container_name> python -c "import torch; print(torch.cuda.is_available()); print(getattr(torch.version, \"hip\", None))"'
```

## GPU Runtime Compliance Gate (Task 12+)

Use deterministic compliance checks before GPU-governed conversion workloads:

```bash
pdm run run-local-pdm hemma-verify-gpu-runtime
```

For internal container validation only (`8085`) with compose services:

```bash
SIR_CONVERT_A_LOT_VERIFY_LANE=docker \
  pdm run run-local-pdm hemma-verify-gpu-runtime
```

Verification lane policy for this command:

- host lane (`28085`) is canonical for deploy/live verification.
- docker lane (`8085`) is internal-only container validation and must not be advertised as a
  client access lane.

ROCm torch pin source of truth remains:

- `pyproject.toml` `tool.sir_convert_a_lot.rocm_runtime`
  - `torch==2.10.0+rocm7.1`
  - `torchvision==0.25.0+rocm7.1`
  - `torchaudio==2.10.0+rocm7.1`

If verification fails due a non-ROCm torch runtime in the project environment:

```bash
pdm run run-local-pdm hemma-repair-rocm-runtime
pdm run run-local-pdm hemma-verify-gpu-runtime
```

Compliance pass conditions:

- `/readyz` passes with deterministic service invariants:
  - `service_revision` equals Hemma repo `HEAD`,
  - `service_profile` matches entrypoint profile,
  - `data_root` matches canonical configured runtime root.
- `/healthz` remains liveness-only and should return `{"status":"ok",...}` when process is alive.
- `/metrics` is available for Prometheus scraping on the service listener.
- Metrics label safety policy:
  - do not use `job_id`, correlation id, filename, or dynamic endpoint values as metric labels,
  - use bounded labels only (status/source/output/backend/policy),
  - correlate per-job diagnostics through `X-Correlation-ID` + lifecycle events/webhook payloads.
- `rocm-smi` detects the GPU.
- `probe_torch_gpu_runtime()` reports `runtime_kind="rocm"` and `is_available=true`.
- Live `gpu_required` conversion succeeds with `conversion_metadata.acceleration_used="cuda"`.
- No `docling_cuda_unavailable_fallback_cpu` warning.
- `rocm-smi` observes non-zero GPU busy during conversion.

## Deploy Parity and Live Verification Gate (Task 76)

Use one command to enforce deploy parity before Story 20 throughput slices.

Canonical command:

```bash
pdm run hemma-deploy-and-verify \
  --expected-revision <sha> \
  --lane host \
  --api-key <key>
```

Arguments and policy:

- `--expected-revision` is required and must match remote `HEAD` after pull.
- `--lane` defaults to `host`; `docker` is internal-only validation.
- API key precedence is strict: `--api-key` > `SIR_CONVERT_A_LOT_API_KEY` > error.
- `dev-only-key` is forbidden unless explicitly passed via `--api-key dev-only-key` or
  `--allow-dev-key` is set.
- API keys must never be persisted in logs/artifacts.

Deterministic evidence path:

- `build/verification/task-76-hemma-deploy-verify/`
  - `report.json`
  - `report.md`
  - `readyz.json`
  - `metrics.prom`
  - `remote_head.txt`

Decision tree (fail-closed):

1. `expected_revision != remote_revision`:
   - push the intended commit, rerun with the pushed SHA.
1. `service_revision != remote_revision`:
   - recreate service (`pdm run dev-recreate` on Hemma), verify `/readyz`, rerun gate.
1. key resolution fails:
   - provide `--api-key` or set `SIR_CONVERT_A_LOT_API_KEY`; avoid implicit `dev-only-key`.
1. metrics safety scan fails (`job_id=`, `jobv2_`):
   - remove forbidden high-cardinality labels and rerun verification.

## Bottleneck Triage Workflow (Task 73)

Use this flow to identify slowdown source without high-cardinality metric labels.

1. Capture a metrics snapshot:

```bash
curl -fsS http://127.0.0.1:28085/metrics > /tmp/sir_metrics.prom
```

1. Check queue pressure and worker cap:

   - `sir_convert_a_lot_v2_jobs_queued`
   - `sir_convert_a_lot_v2_jobs_active`
   - `sir_convert_a_lot_v2_workers_max`
   - `sir_convert_a_lot_v2_worker_saturation_ratio`
   - `sir_convert_a_lot_v2_gpu_concurrency_cap`

1. Check stage timing concentration:

   - `sir_convert_a_lot_v2_stage_duration_seconds_count`
   - `sir_convert_a_lot_v2_stage_duration_seconds_sum`
   - canonical stage labels are:
     - `ocr_layout_extract_ms`
     - `markdown_normalize_ms`
     - `formula_enrichment_ms`
     - `checkpoint_persist_ms`
     - `final_artifact_persist_ms`
     - `chunk_total_ms`
     - `conversion_total_ms`

1. Check terminal/retry trend by bounded dimensions:

   - `sir_convert_a_lot_v2_jobs_terminal_total`
   - `sir_convert_a_lot_v2_job_retries_total`

1. Correlate one problematic job via job payload and logs/events (not metric labels):

   - inspect `result.conversion_metadata`:
     - `acceleration_policy_requested`
     - `acceleration_used`
     - `gpu_runtime_kind`
     - `gpu_device_count`
     - `gpu_busy_percent`
     - `gpu_memory_used_percent`
   - join with request/response `X-Correlation-ID` and lifecycle events.

Local synthetic overhead evidence command (generated artifact under `build/`):

```bash
pdm run benchmark:task-73-telemetry \
  --total-jobs 40 \
  --max-workers 8 \
  --stub-work-seconds 0.2 \
  --output-json build/benchmarks/story-20/task-73-telemetry-overhead-local.json \
  --data-root build/benchmarks/story-20/task-73-telemetry-runtime
```

Benchmark payload variants:

- `telemetry_full`: runtime telemetry calls enabled with Prometheus sink attached.
- `telemetry_sink_disabled`: runtime telemetry calls enabled with no sink attached.
- `telemetry_calls_bypassed`: runtime telemetry calls bypassed in hot paths.

Overhead deltas:

- `overhead_percent.full_vs_sink_disabled`
- `overhead_percent.full_vs_bypassed`

## Local Parallel Throughput Fixture (Task 72)

Use this deterministic local benchmark to confirm the Task 72 worker-pool implementation before
moving to Hemma production-profile tuning in Task 74.

Command:

```bash
pdm run benchmark:task-72 \
  --total-pages 8 \
  --repeats 5 \
  --chunk-size-pages 1 \
  --max-chunk-workers 4 \
  --stub-work-seconds 0.03 \
  --output-json build/benchmarks/story-20/task-72-parallel-throughput-local.json \
  --data-root build/benchmarks/story-20/task-72-parallel-throughput-runtime
```

Interpretation rules:

- `comparison.p50_wall_clock_improvement_percent` should stay at or above the Task 72 floor
  (`>= 10%`) for the deterministic fixture.
- `comparison.byte_identical_to_serial` must remain `true`.
- `serial.result_metadata.parallel_enabled` must be `false`.
- `parallel.result_metadata.parallel_enabled` must be `true`.
- `parallel.result_metadata.scheduling_mode` must remain `parallel_ordered_commit`.

Rollout guardrails:

- Treat this command as implementation evidence only; do not use it to set Hemma production
  defaults.
- Keep `SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS=0` by default until Task 74 publishes tuned
  Hemma guidance and rollback criteria.
- Do not reintroduce the removed 4-worker OCR benchmark profile without new written evidence; the
  2026-03-06 Hemma run showed ROCm HIP OOM under that setting.
- Run the Task 76 deploy-and-verify gate before any Hemma tuning/profile runs.

## Throughput Benchmark Harness (Task 74)

Use the committed Task 74 harness to compare baseline and tuned long-PDF profiles and publish
machine-readable plus markdown evidence.

Local command surface:

```bash
pdm run benchmark:task-74 \
  --output-json build/benchmarks/story-20/task-74-throughput-benchmark-local.json \
  --output-report build/benchmarks/story-20/task-74-throughput-report-local.md \
  --corpus-root build/benchmarks/story-20/task-74-corpus \
  --data-root build/benchmarks/story-20/task-74-runtime \
  --page-counts 120,180,240 \
  --gpu-available
```

Bounded 2-worker tuning sweep:

```bash
pdm run benchmark:task-74-two-worker-sweep \
  --output-json build/benchmarks/story-20/task-74-two-worker-sweep-local.json \
  --output-report build/benchmarks/story-20/task-74-two-worker-sweep-report-local.md \
  --corpus-root build/benchmarks/story-20/task-74-two-worker-sweep-corpus \
  --data-root build/benchmarks/story-20/task-74-two-worker-sweep-runtime \
  --page-counts 120,180,240 \
  --two-worker-chunk-sizes 2,3,4,6,8 \
  --two-worker-gpu-stage-caps 1,2 \
  --gpu-available
```

Remote Hemma execution path after push/deploy parity:

```bash
pdm run run-hemma -- pdm run benchmark:task-74-hemma \
  --expected-revision <sha>
```

Bounded 2-worker Hemma sweep:

```bash
pdm run run-hemma -- pdm run benchmark:task-74-two-worker-sweep-hemma \
  --expected-revision <sha>
```

Usage notes:

- The canonical Hemma runner now performs the required preflight before invoking `benchmark:task-74`:
  - runs `pdm run hemma-sync-prod-env-mirror`,
  - verifies `~/apps/sir-convert-a-lot/.env` resolves to the canonical prod env file,
  - requires the canonical env to contain the Task 74 OCR defaults,
  - runs `pdm sync --prod --no-editable --no-self` on the Hemma host runtime,
  - warms a host EasyOCR cache under `~/.cache/sir-convert-a-lot/easyocr-models`,
  - reruns the live host-lane smoke on the expected revision before benchmarking.
- The harness records p50/p90 wall-clock latency, success/error rate, queue depth, worker
  saturation, chunk-worker saturation, and GPU busy/memory gauges.
- The committed benchmark matrix is intentionally restricted to:
  - `serial_baseline` (`max_chunk_workers=1`, `chunk_size_pages=8`, `gpu_stage_max_concurrency=1`)
  - `parallel_conservative` (`max_chunk_workers=2`, `chunk_size_pages=4`,
    `gpu_stage_max_concurrency=2`)
- Use the bounded 2-worker sweep when exploring alternatives; it keeps `max_chunk_workers=2` and
  varies only chunk size plus bounded GPU stage cap so candidate profiles stay within the reviewed
  safety envelope.
- The generated Task 74 JSON/markdown artifacts now include runtime-surface and runtime-parity
  sections; treat `runtime_parity.parity_proven=true` as mandatory for final closeout evidence.
- Use `pdm run benchmark:task-74` directly only for local command-surface smoke checks. The Hemma
  evidence path must use `benchmark:task-74-hemma` so host env/runtime drift is repaired before
  long-running OCR jobs start.
- Treat the generated markdown report as the source for recommended defaults and rollback criteria
  once the Hemma run is complete.
- If safe 2-worker tuning still cannot prove the Task 74 `>= 40%` target, keep serial service
  defaults and expose parallel OCR only through explicit `.env` override.

## TTS Sidecar Benchmark Harness (Task 79)

Use the committed Task 79 harness to prove the sidecar-only TTS path on the live Hemma
R9700/gfx1201 host before the `md -> wav` contract is implemented.

Canonical command:

```bash
pdm run run-hemma -- pdm run benchmark:task-79
```

Evidence path:

- `build/verification/task-79-hemma-tts-sidecar/`
  - `report.json`
  - `report.md`
  - `docker_logs.txt`
  - `artifacts/sample.wav`
  - `artifacts/sample.mp3` when compressed output succeeds
  - `failure.txt` on non-acceptance failures

Usage notes:

- The harness launches an isolated `vllm/vllm-omni-rocm:v0.16.0` container on `hule-network`.
- The harness uses the canonical persistent HF cache path
  `${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/huggingface}`
  so repeated Task 79 runs reuse downloaded model weights instead of redownloading them.
- Inside the sidecar container the cache mount is standardized as:
  - `HF_HOME=/cache/huggingface`
  - `HF_HUB_CACHE=/cache/huggingface/hub`
  - `TRANSFORMERS_CACHE=/cache/huggingface`
- The current stage config is pinned in
  `scripts/sir_convert_a_lot/devops/task79_qwen3_tts_stage_config.yaml` and tracks the
  current upstream `qwen3_tts.yaml` schema.
- The benchmark proves both:
  - host-lane reachability on `127.0.0.1:<task79-port>`
  - internal Docker-network reachability from `sir_convert_a_lot_prod`
- Treat `wav` success as mandatory acceptance evidence.
- Treat compressed-format output as capability evidence, not phase-1 contract acceptance.
- Use the emitted Python recommendation from `report.json` to lock the sidecar runtime floor;
  do not assume Python `3.14` support without live proof.

## V2 Conversion Smoke Verification (Task 39)

Produce deterministic, written evidence that the Hemma **docker lane** can execute the
service API v2 critical routes end-to-end (`html -> pdf`, `md -> pdf`, `md -> docx`,
`pdf -> docx`, `pdf -> md`).

This route is internal container validation only and must not be documented as a client lane.

Run from laptop (wrapper executes the verification remotely in `~/apps/sir-convert-a-lot`):

```bash
pdm run run-local-pdm hemma-verify-v2-conversions
```

Evidence is written on Hemma under:

- `build/verification/task-39-v2-smoke/` (`report.md`, `report.json`, `artifacts/`, `responses/`)

This smoke includes a Swedish OCR regression guard:

- runs `swedish_ocr_pdf_to_md` with forced OCR and asserts output contains `å`, `ä`, `ö`,
- records `ocr_*` metadata plus `pages_per_minute` and `phase_timings_ms` evidence fields.

View the markdown report:

```bash
pdm run run-local-pdm run-hemma -- cat build/verification/task-39-v2-smoke/report.md
```

If Hemma is disk-full (for example `OSError: [Errno 28] No space left on device`), capture state and
reclaim Docker build cache:

```bash
pdm run run-local-pdm run-hemma -- df -h
pdm run run-local-pdm run-hemma --shell 'sudo -n docker system df'
pdm run run-local-pdm run-hemma --shell 'sudo -n docker builder prune -af'
```

For downstream GUI/backend integrations (Skriptoteket, HuleEdu, Projektveckor), use:

- `docs/converters/downstream_integration_contract_v2.md`

## Tunnel Workflow (Local Dev from Any Repo)

Use the canonical tunnel mapping (`28085`) for laptop access to the Hemma prod listener.

```bash
ssh hemma -L 28085:127.0.0.1:28085 -N
curl -fsS http://127.0.0.1:28085/readyz
curl -fsS http://127.0.0.1:28085/metrics >/dev/null
```

Then run conversion from any repository:

```bash
pdm run convert-a-lot convert ./pdfs \
  --output-dir ./research \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY"
```

Internet lane equivalent:

```bash
pdm run convert-a-lot convert ./pdfs \
  --output-dir ./research \
  --service-url https://convert.hule.education \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY"
```

## Production Env Mirroring Policy (Cross-Repo)

Canonical secret root on Hemma:

- `~/infrastructure/env/prod/`

Required project symlink pattern:

- `~/apps/sir-convert-a-lot/.env -> ~/infrastructure/env/prod/sir-convert-a-lot.env`
- `~/apps/huleedu/.env -> ~/infrastructure/env/prod/huleedu.env`
- `~/apps/skriptoteket/.env -> ~/infrastructure/env/prod/skriptoteket.env`
- `~/apps/projektveckor-portal/.env -> ~/infrastructure/env/prod/projektveckor-portal.env`

Key synchronization invariant:

- `SIR_CONVERT_A_LOT_API_KEY` must be present and synchronized in Sir/HuleEdu/Skriptoteket env files.
- `PVP_SIR_CONVERT_A_LOT_API_KEY` in Projektveckor must use the same secret value.

Canonical execution command from laptop:

```bash
pdm run run-local-pdm run-hemma -- pdm run hemma-sync-prod-env-mirror
```

## Canonical Live Docling GPU Validation

Run the committed live-runner surface (argv mode, no inline shell payloads):

```bash
pdm run run-hemma -- pdm run validate:docling-gpu-live \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_API_KEY" \
  --output-root build/manual-validation-quality-control
```

## Deployment Pattern

- Pull tracked changes on Hemma with `git pull`.
- Do not use `scp` for tracked repository files.
- Keep client call guidance restricted to tunnel (`28085`) or internet (`https://convert.hule.education`).
- Do not introduce new direct local client lanes in docs, skills, or runbooks.
- Keep GPU as default execution policy; CPU fallback requires documented decision update.

## Cross-Repo Coexistence Notes

- Reserve unique service ports per app to avoid collisions:
  - Skriptoteket web/proxy stack (existing compose)
  - HuleEdu LanguageTool/offload stack (existing compose)
  - Sir Convert-a-Lot conversion service (new compose)
- Keep this service on shared operational conventions (SSH alias, Docker commands, logs, health checks)
  so assistants can execute the same mental model across repos.
