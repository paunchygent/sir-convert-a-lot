---
name: sir-convert-a-lot-devops-hemma
description: >-
  Repo-specific router for Sir Convert-a-Lot Hemma operations, GPU runtime
  checks, client access lanes, and cross-repo coexistence.
---

# Sir Convert-a-Lot DevOps (Hemma + GPU)

## Use When

- Operating or troubleshooting Sir Convert-a-Lot on Hemma.
- Verifying GPU, ROCm, vLLM, llama.cpp, or model-cache runtime behavior.
- Running tunnel, deploy, smoke, or live verification work.
- Checking coexistence with HuleEdu or Skriptoteket on the same host.

## Read Order

1. `docs/runbooks/run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md`
1. Route from that doorway to the focused runbook:
   - `docs/runbooks/run-sircon-hemma-service-operations-runbook-for-sir-convert-a-lot-hemma-service-operations-runbook-for-sir-convert-a-lot.md`
   - `docs/runbooks/run-sircon-hemma-gpu-runtime-runbook-for-sir-convert-a-lot-hemma-gpu-runtime-runbook-for-sir-convert-a-lot.md`
   - `docs/runbooks/run-sircon-hemma-conversion-benchmark-runbook-for-sir-convert-a-lot-hemma-conversion-benchmark-runbook-for-sir-convert-a-lot.md`
   - `docs/runbooks/run-sircon-hemma-tts-sidecar-benchmark-runbook-for-sir-convert-a-lot-hemma-tts-sidecar-benchmark-runbook-for-sir-convert-a-lot.md`
1. For STT proof lanes, audio admission timing, or formatter replay failures
   observed during downstream proof, read:
   - `docs/reference/ref-sircon-general-stt-proof-lanes-and-admission-operations-stt-proof-lanes-and-admission-operations.md`
1. For public contracts, read:
   - `docs/reference/ref-sircon-general-sir-convert-a-lot-cli-and-service-usage-sir-convert-a-lot-cli-and-service-usage.md`
   - `docs/reference/ref-sircon-general-multi-format-conversion-service-api-v2-multi-format-conversion-service-api-v2.md`
   - `docs/decisions/adr-sircon-0011-service-api-v2-current-state-authority-and-extension-boundary.md`

## Workflow

1. Confirm the governed task/reference/ADR surface before changing runtime behavior.
1. Use `pdm run run-hemma -- ...` from the local repo root for remote commands.
1. Use committed detached runners for long Hemma jobs.
1. Record durable findings in the governing task, reference, ADR, or runbook.
1. Keep this `SKILL.md` as a router; do not add task logs or command dumps here.

## Global Invariants

- Canonical remote repo root: `/home/paunchygent/apps/sir-convert-a-lot`.
- Canonical client tunnel lane: `http://127.0.0.1:28085`.
- GPU/offload work is GPU-first; no silent CPU fallback.
- STT proof work runs local/downstream proof before native Hemma production
  proof, and review starts only after both live proofs pass.
- Formatter replay export failures during STT/downstream proof are not the
  same as slow audio admission unless container evidence shows slow admission;
  check the proof-lanes reference for the shared API/worker recovery invariant.
- Do not change public proxy timeout, body-size, trust/key, or ingress knobs to
  mask STT failures before the upstream root cause is pinned and explicitly
  approved.
- Docker work uses BuildKit and Docker Compose v2.
- Long-lived Docker state, model caches, and generated working artifacts stay off
  the Hemma OS disk.
- Public ports, secrets, student PII, and generated benchmark artifacts need
  explicit governing authority before promotion.
