---
type: runbook
id: RUN-hemma-devops-and-gpu
title: Hemma DevOps and GPU Runbook for Sir Convert-a-Lot
status: active
created: '2026-02-11'
updated: '2026-03-08'
owners:
  - platform
system: hemma.hule.education
tags:
  - devops
  - hemma
  - gpu
  - sir-convert-a-lot
links:
  - .codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md
  - .codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md
  - docs/runbooks/runbook-v2-async-push-delivery.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
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

## Detached Execution Policy

For Hemma, execution mode matters as much as the command surface.

- Use attached `pdm run run-hemma -- ...` only for short probes, inspections,
  validation commands, and fast deterministic checks.
- Any long-running remote workload must be detached from the local client
  session before it is treated as canonical evidence.
- This applies to:
  - ML preprocessing
  - model training
  - large corpus acquisition
  - long benchmark sweeps
  - any GPU job that may outlive the local tunnel or client session

Approved long-run posture:

- committed detached runner surface
- named background Docker container plus separate inspection commands
- remote `tmux`/supervised execution when a committed detached runner does not
  yet exist

## Hemma Storage Tiers

Treat Hemma storage as three different contracts:

- Fast SSD work tier:
  - `/srv/scratch`
  - Docker root and BuildKit cache
  - HF/model caches
  - active generated artifacts under repo `build/` trees
- Large HDD bulk-data tier:
  - `/srv/storage`
  - raw corpora
  - cold retained datasets
  - cold retained proof/run artifacts that no longer need SSD residency
- OS disk:
  - `/`
  - not the long-term home for Docker persistent state or large ML artifact
    trees

Recurring scratch-governance rule for high-churn Qwen lanes:

- audit scratch before long detached proof/training launches:
  `pdm run run-hemma -- pdm run qwen-scratch-policy audit`
- prefer the recurring idle-safe maintenance pass for routine headroom
  recovery:
  `pdm run run-hemma -- pdm run qwen-scratch-policy maintain --prune-docker-state`
- archive explicit cold scratch roots onto storage with symlink-back path
  stability instead of deleting referenced evidence blindly:
  `pdm run run-hemma -- pdm run qwen-scratch-policy remediate --source-path <scratch-path> ...`
- use `--prune-docker-state` only for non-active Docker cleanup when reclaiming
  additional headroom
- install the lightweight recurring user-level timer when the host should keep
  itself healthy between proof runs:
  `pdm run run-hemma -- pdm run qwen-scratch-policy install-timer --enable-linger --prune-docker-state`
- inspect timer state with:
  `pdm run run-hemma -- pdm run qwen-scratch-policy status-timer`
- the recurring pass is scratch-first and idle-safe by contract:
  - active `qwen-*` containers block maintenance
  - the explicit scratch-maintenance block file blocks maintenance
  - cold roots are archived onto `/srv/storage`, not written there directly by
    active training jobs

Persistent Docker-visible bind-root rule for scratch-backed Qwen runtimes:

- keep `/srv/scratch/sir-convert-a-lot/build` and
  `/srv/scratch/sir-convert-a-lot/cache` as the canonical SSD-backed storage
  roots
- expose those roots to snap-Docker through the persistent home-visible bind
  roots under `/home/paunchygent/.data/sir-convert-a-lot/`
- install the committed service once per host:
  `pdm run run-hemma -- pdm run qwen-docker-bind-roots install`
- verify service state before new Qwen training/proof work:
  `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
- verify Docker can bind-mount the effective home roots:
  `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`
- after Task 242, ad hoc runtime bind fallback is compatibility-only; the
  normal Hemma contract is the installed persistent home-backed bind roots
- expected live truth on Hemma after install:
  - `status` should show `service_enabled=true`, `service_active=true`, and
    `mounted_expected_source=true` for both build and cache
  - `probe` should show `canonical_probe_ok=false`,
    `home_probe_ok=true`, and the preferred effective roots under
    `/home/paunchygent/.data/sir-convert-a-lot/`
  - interpret that as: `/srv/scratch/...` remains canonical storage, while the
    home-backed mirrors are the Docker-visible bind roots

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
- API key precedence is strict: `--api-key` > `SIR_CONVERT_A_LOT_V2_API_KEY` > error.
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
   - provide `--api-key` or set `SIR_CONVERT_A_LOT_V2_API_KEY`; avoid implicit `dev-only-key`.
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
- When Docker on Hemma cannot bind `/srv/*` directly, the harness bind-mounts that canonical
  data-disk cache into
  `${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT:-/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface}`
  and uses the home-visible path without creating a second long-lived cache tree.
- Inside the sidecar container the cache mount is standardized as:
  - `HF_HOME=/cache/huggingface`
  - `HF_HUB_CACHE=/cache/huggingface/hub`
  - `TRANSFORMERS_CACHE=/cache/huggingface`
- The harness now keeps `VLLM_USE_TRITON_FLASH_ATTN=1` as the canonical Qwen ROCm container
  default on Hemma.
- Use the explicit Task 79 fallback flag only when triaging a concrete regression; do not treat
  "flash attention disabled" as the normal steady state.
- The current stage config is pinned in
  `scripts/sir_convert_a_lot/devops/task79_qwen3_tts_stage_config.yaml` and tracks the
  current upstream `qwen3_tts.yaml` schema.
- Before the sidecar starts, the harness prefetched both:
  - `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
  - `Qwen/Qwen3-TTS-Tokenizer-12Hz`
- The tokenizer files are mirrored into the model snapshot `speech_tokenizer/` path expected by
  the live `vllm-omni` stage-1 loader.
- The benchmark proves both:
  - host-lane reachability on `127.0.0.1:<task79-port>`
  - internal Docker-network reachability from `sir_convert_a_lot_prod`
- For full `Qwen3-TTS-1.7B` Swedish fine-tuning planning and Hemma/Colab runtime strategy, use:
  - `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
- Treat `wav` success as mandatory acceptance evidence.
- Treat compressed-format output as capability evidence, not phase-1 contract acceptance.
- Use the emitted Python recommendation from `report.json` to lock the sidecar runtime floor;
  do not assume Python `3.14` support without live proof.

Official Qwen Base clone lane:

- The same Task 79 harness now supports the official Qwen3-TTS Base cloning
  path through `/v1/audio/speech`.
- Use:
  - `task_type=Base`
  - model `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
  - `--reference-audio`
  - `--reference-transcript` or `--reference-transcript-file`
  - optional bounded `--instructions` or `--instructions-file`
- The benchmark writes deterministic input evidence under `inputs/` so the
  exact clone prompt can be audited after the Hemma run.

Example:

```bash
pdm run run-hemma -- pdm run benchmark:task-79 \
  --output-root build/verification/task-98-qwen-english-reference-clone \
  --task-type Base \
  --language English \
  --model Qwen/Qwen3-TTS-12Hz-0.6B-Base \
  --reference-audio build/verification/task-98-qwen-english-reference-clone/inputs/reference_audio.wav \
  --reference-transcript-file build/verification/task-98-qwen-english-reference-clone/inputs/reference_transcript.txt \
  --probe-text-file build/verification/task-98-qwen-english-reference-clone/inputs/probe_text.txt \
  --instructions-file build/verification/task-98-qwen-english-reference-clone/inputs/instructions.txt
```

## OpenVoice V2 Swedish Cloning Benchmark (Task 81)

Run the first normalized ADR-0007 sidecar benchmark for the OpenVoice V2
candidate with a Swedish base speaker and an approved teacher reference clip.

Canonical command:

```bash
pdm run run-hemma -- pdm run benchmark:task-81 \
  --reference-audio <remote-path-to-approved-reference-audio>
```

Evidence path:

- `build/verification/task-81-openvoice-v2-hemma/`
  - `report.json`
  - `report.md`
  - `docker_logs.txt`
  - `artifacts/sample_sv.wav`
  - `failure.txt` on non-acceptance failures

Usage notes:

- The harness builds and launches the dedicated `containers/tts-sidecar-openvoice/Dockerfile`
  image instead of reusing the main service image.
- The sidecar exposes the normalized internal-only endpoints from ADR-0007:
  - `GET /health`
  - `GET /capabilities`
  - `GET /voices`
  - `POST /synthesize`
- OpenVoice checkpoints are cached under the canonical persistent host root
  `${SIR_CONVERT_A_LOT_HEMMA_OPENVOICE_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/openvoice}`.
- The Swedish base model cache reuses the canonical shared HF cache root
  `${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/huggingface}`.
- When Docker cannot bind `/srv/*` directly, the harness bind-mounts the canonical cache roots
  through the approved home-visible compatibility paths without creating a second long-lived
  cache tree.
- The benchmark requires one approved teacher reference clip used strictly as the cloning input.
- The Swedish sample is generated through:
  - `facebook/mms-tts-swe` as the Swedish base speaker
  - OpenVoice V2 tone-color conversion to the teacher reference voice
- The corrected rerun path must use OpenVoice's intended reference-speaker preprocessing flow
  (`se_extractor.get_se(..., vad=True)`) rather than extracting directly from the raw reference
  clip.
- Corrected reruns preserve:
  - the processed reference artifact directory,
  - the Swedish base artifact before cloning,
  - the final cloned Swedish artifact,
    so setup defects can be judged without guesswork.
- Treat the Task 81 result as credibility evidence for OpenVoice's cross-lingual claim on Hemma,
  not as a blanket guarantee of Swedish production quality.

## F5-TTS Swedish Cloning Benchmark (Task 85)

Run the active F5-TTS comparison benchmark against the normalized ADR-0007 sidecar contract using
the prepared Swedish teacher reference clip plus exact transcript evidence.

Canonical command:

```bash
pdm run run-hemma -- pdm run benchmark:task-85 \
  --reference-audio build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.wav \
  --reference-transcript-file build/verification/task-85-f5-tts-hemma/inputs/reference_10s_sv.txt
```

Evidence path:

- `build/verification/task-85-f5-tts-hemma/`
  - `report.json`
  - `report.md`
  - `docker_logs.txt`
  - `f5_help.txt`
  - `reference_transcript.txt`
  - `artifacts/sample_sv.wav`

Usage notes:

- The harness builds and launches the dedicated `containers/tts-sidecar-f5/Dockerfile` image.
- The current Task 85 image source is `ChiliOlavi/F5-TTS@swedish-tts`.
- The sidecar stays internal-network only and exposes the normalized ADR-0007 endpoints:
  - `GET /health`
  - `GET /capabilities`
  - `GET /voices`
  - `POST /synthesize`
- The Swedish model snapshot is cached under the canonical persistent host root
  `${SIR_CONVERT_A_LOT_HEMMA_F5_MODEL_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/f5-tts-swedish}`.
- Shared Hugging Face assets reuse the canonical persistent host root
  `${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/huggingface}`.
- The benchmark accepts transcript input either:
  - directly via `--reference-transcript`
  - or via deterministic file input with `--reference-transcript-file`
- The current successful model inventory on Hemma is:
  - `model_last.pt`
  - `setting.json`
  - `vocab.txt`
- Treat the current Task 85 result as technical feasibility evidence first; the quality
  recommendation remains open until listening review is recorded against the Task 81 baseline.

## Chatterbox Multilingual Swedish Cloning Benchmark (Task 86)

Run the official Chatterbox Multilingual benchmark against the normalized ADR-0007 sidecar
contract on Hemma.

Canonical command:

```bash
pdm run run-hemma -- pdm run benchmark:task-86
```

Evidence path:

- `build/verification/task-86-chatterbox-hemma/`
  - `report.json`
  - `report.md`
  - `capabilities.json`
  - `voices.json`
  - `package_versions.json`
  - `gpu-before.txt`
  - `gpu-after.txt`
  - `docker_logs.txt`
  - `artifacts/smoke-test-en.wav`
  - `artifacts/scenario-a-sv-ref-sv-out.wav`

Usage notes:

- The harness builds and launches the dedicated `containers/tts-sidecar-chatterbox/Dockerfile`
  image via BuildKit.
- This is the current Hemma production-candidate TTS sidecar image in this repo.
- The sidecar stays internal-network only and exposes the normalized ADR-0007 endpoints:
  - `GET /health`
  - `GET /capabilities`
  - `GET /voices`
  - `POST /synthesize`
- The runtime uses the official multilingual surface:
  - package `chatterbox-tts`
  - class `chatterbox.mtl_tts.ChatterboxMultilingualTTS`
- The benchmark records the contract difference versus F5-TTS:
  - Chatterbox cloning does not require `ref_text`.
- Shared Hugging Face assets reuse the canonical persistent host root
  `${SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH:-/srv/scratch/sir-convert-a-lot/cache/huggingface}`.
- The first successful Hemma run reused an existing cached model snapshot and recorded:
  - startup `33.207` seconds,
  - warm restart `21.065` seconds,
  - Swedish clone peak VRAM `8982421504` bytes on `AMD Radeon AI PRO R9700`.
- Treat the current Task 86 result as technical feasibility evidence first; the quality
  recommendation remains open until listening review is recorded against the Task 81 and Task 85
  baselines.

TTS container lifecycle policy:

- deployable Hemma production candidate:
  - `containers/tts-sidecar-chatterbox/Dockerfile`
- experiment-only, do not deploy as Hemma production services:
  - `containers/tts-sidecar-openvoice/Dockerfile`
  - `containers/tts-sidecar-f5/Dockerfile`
  - `containers/textprep-espeak-phonemizer/Dockerfile`

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
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
```

Internet lane equivalent:

```bash
pdm run convert-a-lot convert ./pdfs \
  --output-dir ./research \
  --service-url https://convert.hule.education \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY"
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

- `SIR_CONVERT_A_LOT_V2_API_KEY` must be present and synchronized in Sir/HuleEdu/Skriptoteket env files.
- `PVP_SIR_CONVERT_A_LOT_V2_API_KEY` in Projektveckor must use the same secret value.

Canonical execution command from laptop:

```bash
pdm run run-local-pdm run-hemma -- pdm run hemma-sync-prod-env-mirror
```

## Canonical Live Docling GPU Validation

Run the committed live-runner surface (argv mode, no inline shell payloads):

```bash
pdm run run-hemma -- pdm run validate:docling-gpu-live \
  --service-url http://127.0.0.1:28085 \
  --api-key "$SIR_CONVERT_A_LOT_V2_API_KEY" \
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
