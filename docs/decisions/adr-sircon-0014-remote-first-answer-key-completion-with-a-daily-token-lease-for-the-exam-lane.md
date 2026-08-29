---
type: adr
id: ADR-SIRCON-0014
title: Remote-first answer-key completion with a daily token lease for the exam lane
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-29'
status: accepted
deciders:
  - user-lead
links:
  governing:
    - TASK-SIRCON-08-01-07
    - ADR-SIRCON-0009
---

## Context

ADR-SIRCON-0009 made remote answer-key providers forbidden by default,
keeping completion on Hemma-local model sidecars. Since then the model
landscape changed: the user holds a 10M-tokens-per-day OpenAI research
retainer, and `gpt-5.6-luna` at low reasoning effort is both stronger and
cheaper than the previously evaluated mini-tier remote profiles, while the
local Qwen sidecar occupies Hemma GPU capacity. The user decided on
2026-08-28 (GrillMe rounds recorded in retained planning session
`01a048d5-69f7-7394-93dd-8ff91af608cd`) to make the exam lane
remote-API-first under a hard daily budget. TASK-SIRCON-08-01-07 carries the
implementation contract.

## Decision

For the exam lane's answer-key completion only:

- The default remote profile is OpenAI `gpt-5.6-luna` at low reasoning
  effort. The remote-forbidden default from ADR-SIRCON-0009 no longer
  applies to this lane; other lanes keep their existing policy.
- OpenRouter `z-ai/glm-5.3-flash` is the pinned failover-only backup: used
  on provider transport errors, timeouts, or server-side failures, never on
  budget exhaustion, and it draws from the same lease pool.
- Spending is governed by a lease-based daily token budget of 5,000,000
  tokens (input plus output combined, configurable), a fixed sub-allocation
  inside the account-wide 10M-per-day retainer. Leases are reserved before
  each call and never refunded on failure; the ledger is partitioned by UTC
  day, so the budget resets structurally at 00:00 UTC. On exhaustion,
  answer-key completion fails closed with an operator-visible status until
  reset; deterministic conversion and all non-LLM artifacts are unaffected.
  The lease semantics port the HuleEdu `openai_allowance` pattern onto Sir
  Convert's atomic-filesystem storage; no Redis or shared cross-repo counter
  is introduced.
- Data boundary: this lane sends teacher exam content and proposed answer
  keys only. No student data flows through answer-key completion.
- The default completion mode stays `source_evidence_only`; this decision
  changes which provider serves LLM completion modes when a job requests
  them, not whether LLM completion runs.

## Non-Decisions

- No change to completion modes, teacher-review provenance, or the
  readiness gate.
- No retirement of the local sidecar profiles; they remain selectable and
  the Qwen answer-key sidecar's retirement is governed separately under the
  Skriptoteket port epic (EPIC-SKRIPT-39 / ADR-SKRIPT-0090).
- No paid-overage lane: exhaustion is a hard stop, and any future overage
  escape hatch requires explicit human authority in its own decision.
- No provider changes for non-exam lanes.

## Consequences

- Teachers get stronger, cheaper answer-key proposals; Hemma GPU pressure
  from the exam lane drops.
- The lane depends on OpenAI availability; the GLM failover bounds outage
  impact without creating silent quota overruns.
- Remote calls are shared with the provider under the research retainer's
  terms; the teacher-exam-content-only boundary keeps that acceptable.
- The Skriptoteket port (EPIC-SKRIPT-39) carries this configuration over
  instead of redesigning it.
