---
id: task-06-define-thin-adapter-contract-and-conformance-harness-for-story-003c
title: Define thin adapter contract and conformance harness for Story 003c
type: task
status: completed
priority: critical
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-03-03-internal-backend-integration-huledu-skriptoteket.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/converters/internal_adapter_contract_v1.md
  - docs/reference/ref-story-003c-consumer-integration-handoff.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md
  - scripts/sir_convert_a_lot/integrations/adapter_profiles.py
  - tests/sir_convert_a_lot/test_integration_adapter_conformance.py
labels:
  - integration
  - adapter
  - conformance
  - story-003c
---

PR-sized Story 003c execution slice for this repository only.

## Objective

Codify thin adapter requirements for internal consumers and enforce them with an
automated conformance harness, while keeping HTTP v1 contract behavior unchanged.

## PR Scope

- Add normative internal adapter contract documentation.
- Provide a reusable, typed reference adapter module for HuleEdu and Skriptoteket profiles.
- Add conformance tests as the primary acceptance gate.
- Publish consumer handoff documentation with explicit adoption checklist.
- Keep public API endpoint surface unchanged.

## Deliverables

- [x] `docs/converters/internal_adapter_contract_v1.md` with normative requirements.
- [x] `scripts/sir_convert_a_lot/integrations/adapter_profiles.py` thin adapter helpers.
- [x] `tests/sir_convert_a_lot/test_integration_adapter_conformance.py` conformance harness.
- [x] `docs/reference/ref-story-003c-consumer-integration-handoff.md` consumer handoff guidance.
- [x] Stage smoke evidence from tunnel/Hemma flow captured with execution notes.

## Acceptance Criteria

- [x] Both profiles build identical canonical `JobSpec` shape.
- [x] Correlation ID pass-through and deterministic fallback are enforced.
- [x] Idempotency key generation is deterministic and payload-sensitive.
- [x] Adapter forwards service errors without remapping consumer-specific codes.
- [x] Adapter smoke path (`submit -> poll -> result`) is covered through canonical API app.
- [x] Tunnel/Hemma smoke evidence is captured as supporting operational proof.

## Validation

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run mypy --config-file pyproject.toml --no-incremental`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Validation Results

- All commands above executed successfully on 2026-02-11 in local repo context.
- Conformance harness coverage is active in:
  - `tests/sir_convert_a_lot/test_integration_adapter_conformance.py`

## Stage Smoke Evidence (Hemma/Tunnel)

Executed on 2026-02-11:

- `pdm run run-local-pdm run-hemma -- pwd`
  - Output: `/home/paunchygent`
- `pdm run run-local-pdm run-hemma --shell 'find /home/paunchygent -maxdepth 4 -type d -name "sir-convert-a-lot" 2>/dev/null | head -n 20'`
  - Output: no matching repo path found.
- `ssh -M -S /tmp/sir003c_tunnel.sock -fnNT -o ExitOnForwardFailure=yes -L 28085:127.0.0.1:28085 hemma && curl -i --max-time 8 http://127.0.0.1:28085/healthz`
  - Output: `curl: (56) Recv failure: Connection reset by peer`
- `pdm run run-local-pdm run-hemma --shell 'curl -sS -o /tmp/sir_health.out -w "%{http_code}" http://127.0.0.1:28085/healthz || true; echo'`
  - Output: `000` (service unavailable on expected Sir Convert-a-Lot port).
- `pdm run run-local-pdm run-hemma --shell 'curl -sS -o /tmp/sir_health_8085.out -w "%{http_code}" http://127.0.0.1:8085/healthz || true; echo'`
  - Output: `200`, but health payload identifies `language-tool-service`, not Sir Convert-a-Lot.

Conclusion:

- Story 003c slice in this repo is complete.
- Hemma deployment readiness and successful tunnel smoke completion are external operational follow-up items.
- Follow-up task created:
  - `docs/backlog/tasks/task-07-establish-sir-convert-a-lot-hemma-deployment-readiness-and-tunnel-smoke-evidence-for-story-003c.md`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [x] Stage smoke evidence captured
