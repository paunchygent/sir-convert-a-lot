---
id: task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c
title: Establish Sir Convert-a-Lot Hemma deployment readiness and tunnel smoke evidence for Story 003c
type: task
status: completed
priority: critical
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md
  - docs/backlog/tasks/task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c.md
  - docs/converters/internal_adapter_contract_v1.md
  - docs/reference/ref-story-003c-consumer-integration-handoff.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - .agents/skills/sir-convert-a-lot-devops-hemma/SKILL.md
  - .agents/rules/030-conversion-workflows.md
labels:
  - ops
  - hemma
  - tunnel
  - story-003c
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Establish deployable Sir Convert-a-Lot service presence on Hemma and capture
successful tunnel smoke evidence on the expected service port.

## Baseline Context

Known from previous smoke attempts (recorded in Task 06):

- `run-hemma` resolved to `/home/paunchygent`.
- No `sir-convert-a-lot` repo path was found under expected remote paths.
- Tunnel to `127.0.0.1:28085` failed.
- `127.0.0.1:8085/healthz` returned `language-tool-service`, not Sir Convert-a-Lot.

## PR Scope

- Verify/repair canonical Hemma repo root for Sir Convert-a-Lot.
- Ensure canonical repo placement under `~/apps/sir-convert-a-lot` (no home-root drift).
- Deploy or start Sir Convert-a-Lot service on expected local-only port.
- Execute tunnel smoke from local machine and capture health/submit evidence.
- Update Story 003c reference docs with successful operational evidence.

## Deliverables

- [x] Confirmed remote repo path and service startup command evidence.
- [x] Successful `curl` health response through local tunnel endpoint.
- [x] One adapter submit/poll/result smoke transcript through tunnel.
- [x] Updated Story 003c handoff/reference docs with success outputs.

## Acceptance Criteria

- [x] Hemma service is reachable on agreed Sir Convert-a-Lot port.
- [x] Local tunnel flow (`ssh -L ...`) works with deterministic command evidence.
- [x] Adapter smoke (`submit -> poll -> result`) succeeds against Hemma-hosted service.
- [x] Story 003c docs no longer have operational readiness caveat for Hemma smoke.

## Execution Plan

1. Discover canonical remote path and branch state

- Confirm actual repo location on Hemma host.
- Confirm remote checkout includes commit `8c5bd46` (or later).
- Set `SIR_CONVERT_A_LOT_HEMMA_ROOT` in local invocation context if needed.

2. Start/verify service process on Hemma

- Start service with canonical command surface.
- Confirm service health endpoint responds with Sir Convert-a-Lot payload.
- Capture process and listening-port evidence.

3. Validate tunnel path locally

- Open local tunnel on agreed port (`28085`).
- Verify `curl http://127.0.0.1:28085/healthz` returns expected service response.

4. Execute adapter smoke through tunnel

- Run one deterministic `submit -> poll -> result` smoke using adapter helper path.
- Capture job id, terminal status, and result payload excerpt.

5. Close docs-as-code loop

- Update Task 07 with command outputs and completion checklist.
- Remove operational caveat in Story 003c handoff reference once smoke succeeds.
- Re-run docs validation gates.

## Command Plan (Expected)

- `pdm run run-local-pdm run-hemma -- pwd`
- `pdm run run-local-pdm run-hemma --shell 'find /home/paunchygent -maxdepth 5 -type d -name "sir-convert-a-lot" 2>/dev/null'`
- `pdm run run-local-pdm run-hemma --shell 'cd <resolved_root> && git rev-parse --short HEAD'`
- `pdm run run-local-pdm run-hemma --shell 'cd <resolved_root> && pdm run serve:sir-convert-a-lot'`
- `ssh hemma -L 28085:127.0.0.1:28085 -N`
- `curl -i http://127.0.0.1:28085/healthz`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

## Risks and Mitigations

- Risk: service port conflict on Hemma.
  - Mitigation: capture active listeners and adjust tunnel/serve port consistently in docs.
- Risk: remote repo path drift.
  - Mitigation: lock discovered path in env and runbook references.
- Risk: missing runtime dependencies on Hemma.
  - Mitigation: record bootstrap commands in task evidence before retrying smoke.

## Implementation Evidence

Remote path and checkout:

- `ssh hemma "/bin/bash -lc 'ls -la /home/paunchygent/apps'"`
  - Confirmed `/home/paunchygent/apps/sir-convert-a-lot` exists.
- `ssh hemma "/bin/bash -lc 'find /home/paunchygent -maxdepth 4 -type d -name sir-convert-a-lot 2>/dev/null | sort'"`
  - Confirmed repo location is under `/home/paunchygent/apps/` (no alternate path detected).
- `ssh hemma "/bin/bash -lc 'cd /home/paunchygent/apps/sir-convert-a-lot && git rev-parse --short HEAD'"`
  - Confirmed commit `8c5bd46` on `main`.

Remote runtime bootstrap (PEP 668-safe):

- `ssh hemma "/bin/bash -lc 'cd /home/paunchygent/apps/sir-convert-a-lot && python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -e .'"`
- `ssh hemma "/bin/bash -lc 'cd /home/paunchygent/apps/sir-convert-a-lot && nohup .venv/bin/python -m uvicorn scripts.sir_convert_a_lot.service:app --host 127.0.0.1 --port 28085 > /home/paunchygent/logs/sir-convert-a-lot-28085.log 2>&1 < /dev/null &'"`

Remote service readiness:

- `ssh hemma "/bin/bash -lc 'ss -ltnp | rg 28085'"`
  - Listener observed on `127.0.0.1:28085`.
- `ssh hemma "/bin/bash -lc 'curl -sS -o /tmp/sir_health_28085.out -w \"%{http_code}\" http://127.0.0.1:28085/healthz; echo; cat /tmp/sir_health_28085.out'"`
  - Status `200`, body `{"status":"ok"}`.

Local tunnel + adapter smoke:

- `ssh -M -S /tmp/sir003c_tunnel.sock -fnNT -o ExitOnForwardFailure=yes -L 28085:127.0.0.1:28085 hemma`
- `curl -i --max-time 10 http://127.0.0.1:28085/healthz`
  - Status `200 OK`, body `{"status":"ok"}`.
- Adapter smoke via `scripts.sir_convert_a_lot.integrations.adapter_profiles`:
  - `job_id`: `job_0b5fa957472441f597883644d3`
  - `status`: `succeeded`
  - `correlation_id`: `corr_story003c_task07_smoke`
  - markdown preview returned expected converted content.
- Tunnel teardown:
  - `ssh -S /tmp/sir003c_tunnel.sock -O exit hemma`
  - `rm -f /tmp/sir003c_tunnel.sock`

Cleanup:

- Remote temporary service process terminated after evidence capture.

## Lessons Learned

- Always verify service identity from health payload, not just HTTP `200` on a known port.
- Hemma may not have `pdm` preinstalled; keep `.venv + pip install -e .` fallback path documented.
- Explicitly record remote repo discovery/creation as first operational step to avoid path drift.
- Enforce `~/apps/sir-convert-a-lot` as canonical location and reject running from ad hoc home-root clones.
- Capture local tunnel lifecycle commands (open + verify + close) in evidence for repeatability.

## Validation Results

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run run-local-pdm typecheck-all --no-incremental` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Validation

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all --no-incremental`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Planning complete
- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
