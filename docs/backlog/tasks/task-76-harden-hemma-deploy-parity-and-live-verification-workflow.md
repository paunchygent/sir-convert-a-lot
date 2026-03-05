---
id: task-76-harden-hemma-deploy-parity-and-live-verification-workflow
title: Harden Hemma deploy parity and live verification workflow
type: task
status: completed
priority: high
created: '2026-03-05'
last_updated: '2026-03-05'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - scripts/devops/verify-hemma-gpu-runtime.sh
  - scripts/devops/verify-hemma-v2-conversions.sh
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - hemma
  - devops
  - verification
  - deployment
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Eliminate deploy/verification drift and shell-fragile checks so Hemma live verification is a stable
pre-slice gate for Story 20 execution (`T72`, `T74`).

## Definitions

- `expected_revision`: local Git SHA you intend to deploy and verify.
- `remote_revision`: Hemma repo `HEAD` SHA after pull/update.
- `service_revision`: service SHA reported by `/readyz`.
- `lane`: verification access lane.
  - `host` (`28085`) is the canonical verification lane.
  - `docker` (`8085`) is internal-only container validation and must not be advertised as a
    client lane.

## Command Surface

- Required entrypoint:
  - `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>`
- Required arguments:
  - `--expected-revision` (required, explicit deploy target SHA),
  - `--lane` (`host` default/canonical, `docker` internal-only),
  - `--api-key` (or `SIR_CONVERT_A_LOT_API_KEY` via precedence policy below),
  - `--allow-dev-key` (explicit opt-in only for local/dev scenarios).
- Required evidence path:
  - `build/verification/task-76-hemma-deploy-verify/`
- Required evidence files:
  - `report.json`
  - `report.md`
  - `readyz.json`
  - `metrics.prom`
  - `remote_head.txt`

## PR Scope

- Refactor `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/devops/verify-hemma-gpu-runtime.sh`
  to the `--remote` pattern used by
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/devops/verify-hemma-v2-conversions.sh`,
  backed by committed Python module
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/devops/verify_hemma_gpu_runtime.py`.
- Add committed deploy orchestrator command surface for `hemma-deploy-and-verify` via canonical
  wrappers (no ad hoc multiline `run-hemma --shell` payloads for routine verification).
- Add explicit deploy-parity preflight gates:
  - `expected_revision == remote_revision`,
  - service `/readyz.service_revision` equals remote repo HEAD,
  - host lane (`28085`) is canonical for verification; docker lane (`8085`) is allowed only for
    internal container validation and must not be advertised as a client lane.
- Normalize verification auth/key resolution for Hemma:
  - precedence: `--api-key` > `SIR_CONVERT_A_LOT_API_KEY` > error,
  - `dev-only-key` is forbidden unless explicitly passed or `--allow-dev-key` is set,
  - API keys must never be written to artifacts or logs.
- Add canonical one-command deploy+verify workflow:
  - push -> remote pull -> rebuild/recreate -> readiness parity -> live conversion smoke ->
    metrics safety assertions.
- Update runbook guidance and task/docs references with the hardened verification contract.

## Deliverables

- [x] `verify-hemma-gpu-runtime` is migrated to `--remote` + committed Python module flow.
- [x] `pdm run hemma-deploy-and-verify --expected-revision <sha> --lane host --api-key <key>` is
  implemented with deterministic artifact output under
  `build/verification/task-76-hemma-deploy-verify/`.
- [x] Deploy-parity and readiness preflight checks are enforced with actionable failure messages.
- [x] Live verification command enforces strict key-resolution policy and forbids implicit
  `dev-only-key` on Hemma.
- [x] Canonical deploy-and-verify command/workflow is documented and executable.
- [x] Regression tests added for:
  - `test_expected_revision_mismatch_prints_remediation`,
  - `test_service_revision_mismatch_prints_remediation`,
  - `test_key_resolution_missing_key_fails`,
  - `test_dev_only_key_refused_without_allow_flag`,
  - `test_lane_port_mapping_host_and_docker`,
  - `test_metrics_scan_rejects_forbidden_job_id_substrings`.
- [x] GPU busy sampling false-negative in live verifier fixed and regression-tested.

## Acceptance Criteria

- [x] Live verification fails immediately with remediation steps when:
  - `expected_revision != remote_revision`,
  - `service_revision != remote_revision`.
- [x] Verification no longer fails due to shell quoting issues in remote wrapper execution.
- [x] Host lane (`28085`) is canonical for verification; docker lane (`8085`) is internal-only and
  never documented as a client lane.
- [x] Key resolution policy is enforced exactly:
  - `--api-key` > `SIR_CONVERT_A_LOT_API_KEY` > error,
  - implicit `dev-only-key` is rejected unless explicitly allowed with `--allow-dev-key`,
  - API keys are not persisted in artifacts/logs.
- [x] Metrics safety scan rejects forbidden substrings such as `job_id=` and `jobv2_`.
- [x] Runbook includes the hardened sequence and error-decision tree for drift/auth/lane failures.
- [x] Host-lane GPU live verification now records non-zero GPU busy evidence and passes on the
  deployed revision.
- [x] Validation includes:
  - `pdm run pytest-root tests/sir_convert_a_lot -q`

## Follow-ups

- `T77` extends the live v2 conversion smoke (`verify_hemma_v2_conversions.py`) with a Swedish OCR
  diacritics guard (`åäö`) and OCR engine/language preflight to prevent multi-hour wrong-output
  runs.

## Post-Deploy RCA and Remediation (2026-03-05)

- Symptom:
  - live verifier failed with `rocm-smi never observed non-zero GPU busy during conversion`
    despite successful GPU-required conversions (`acceleration_used="cuda"`).
- Root cause:
  - `scripts/sir_convert_a_lot/devops/verify_hemma_gpu_runtime.py` used an over-escaped regex in
    `_extract_gpu_busy_peak`:
    - before: `r"GPU use \\(%\\):\\s*([0-9]+)"` (never matched),
    - after: `r"GPU use \(%\):\s*([0-9]+)"`.
- Remediation:
  - fixed parser and added regression tests:
    - `tests/sir_convert_a_lot/test_verify_hemma_gpu_runtime.py`,
  - committed and pushed hotfix (`886aeb04ea184e977594c8ff0b4c482682535df2`),
  - pulled and redeployed on Hemma (`dev-recreate`),
  - re-ran live verification on host lane and confirmed non-zero GPU busy peak.
- Long-term stability guard:
  - parser-level regression tests now block future false negatives in deploy-time GPU verification.

## Live Evidence Addendum (2026-03-05)

- Deploy parity (pass):
  - `/readyz` reports:
    - `service_revision=886aeb04ea184e977594c8ff0b4c482682535df2`,
    - `expected_revision=886aeb04ea184e977594c8ff0b4c482682535df2`.
- GPU runtime verifier (pass):
  - `build/verification/task-76-hemma-deploy-verify/gpu-runtime-live-large2/gpu_runtime_report.json`
  - key fields:
    - `runtime_probe.runtime_kind="rocm"`,
    - `smoke.acceleration_used="cuda"`,
    - `smoke.gpu_busy_peak=99`,
    - `smoke.status="succeeded"`.
- Full v2 host-lane conversion smoke (pass):
  - `build/verification/task-39-v2-smoke-host-live-2/report.md`
  - routes succeeded:
    - `html->pdf`, `md->pdf`, `md->docx`, `pdf->docx`, `pdf->md`,
  - PDF routes report `acceleration_used="cuda"`.
- Metrics safety (pass):
  - `build/verification/task-76-hemma-deploy-verify/live-checks/metrics-after-hotfix.prom`
  - no `job_id=` and no `jobv2_` label leakage.

## Validation Evidence

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot -q` (pass: `467 passed, 5 skipped`)
- `pdm run validate-tasks` (pass: `Validated 109 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=136 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)
- Live command (pass):
  - `pdm run run-local-pdm hemma-deploy-and-verify --expected-revision "$(git rev-parse HEAD)" --lane host`
  - artifacts:
    - `build/verification/task-76-hemma-deploy-verify/report.json`
    - `build/verification/task-76-hemma-deploy-verify/report.md`
    - `build/verification/task-76-hemma-deploy-verify/readyz.json`
    - `build/verification/task-76-hemma-deploy-verify/metrics.prom`
    - `build/verification/task-76-hemma-deploy-verify/remote_head.txt`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
