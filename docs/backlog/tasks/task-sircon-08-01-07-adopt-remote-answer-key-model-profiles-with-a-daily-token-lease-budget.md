---
type: task
id: TASK-SIRCON-08-01-07
title: Adopt remote answer-key model profiles with a daily token lease budget
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-28'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Exam-lane answer-key completion defaults to the GPT-5.6 Luna low-reasoning-effort remote profile, with GLM-5.3-flash via OpenRouter as a failover-only backup drawing from the same lease.
- A configurable daily token lease of 5,000,000 tokens (input plus output, non-refundable leases, UTC-midnight reset) fail-closes answer-key completion on exhaustion with operator-visible status while deterministic conversion continues unaffected.
- The exam-lane remote-provider policy decision is recorded with its data boundary of teacher exam content only, superseding the remote-forbidden default for this lane.
story: ST-SIRCON-08-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Replace the exam lane's default answer-key model routing with retained remote
profiles under a hard daily token budget.

- Default remote profile: GPT-5.6 Luna at low reasoning effort. Verify the
  exact model identifier against current provider documentation at
  implementation time; do not hardcode from memory.
- Backup profile: GLM-5.3-flash served via OpenRouter. The backup is
  failover-only, used on provider error or outage, and its tokens draw from
  the same daily lease. Exhaustion never routes to the backup.
- Lease budget: 5,000,000 tokens per day for this lane (input plus output
  combined), configurable. Leases are taken before each call and never
  refunded on failure. The counter resets at UTC midnight. On exhaustion,
  answer-key completion fails closed with an explicit operator-visible status
  until reset; deterministic conversion and all other artifacts are
  unaffected.
- Reuse the lease-counter pattern from the user's research repository; no
  shared cross-repo counter service. The 5M slice keeps headroom inside the
  account-wide 10M-per-day retainer alongside other consumers.
- Record the exam-lane remote-policy decision (amending or superseding the
  ADR-SIRCON-0009 remote-forbidden default for this lane) with the data
  boundary stated: teacher exam content and proposed answer keys only; no
  student data flows through this lane.

Out of scope: retiring the Qwen answer-key sidecar (follows the Skriptoteket
port epic), provider changes for any non-exam lane, and changes to
completion-mode or teacher-review semantics.

## Contract Inputs

- Provider harness: `scripts/sir_convert_a_lot/domain/structured_llm_contracts.py`,
  `infrastructure/structured_llm_provider.py`, `structured_llm_config.py`,
  `structured_llm_hot_settings_runtime.py`,
  `infrastructure/answer_key_openai_model_profiles.py` (existing OpenAI
  profile shape to extend), ADR-SIRCON-0009.
- Retained planning record: session `01a048d5-69f7-7394-93dd-8ff91af608cd`,
  `evidence/planning/TASK-SIRCON-REP-0029/plan.md`, decision ledger rows
  9 through 14.
- Third-party model and API documentation is fetched through the sanctioned
  docs tooling before code changes; exact model IDs come from current
  provider docs.

## Core Vertical And Performance

The core vertical is one answer-key completion request routed through the new
default profile with a lease taken, and the same request fail-closing with a
visible status once the daily lease is exhausted. Material performance
concern: the lease check must not add a network hop; it is a local counter.

## Validation

- `pdm run check --plan exam`, then `pdm run check exam` (provider-profile and
  lease-counter tests included).
- A recorded live completion through the Luna profile, a forced-failover proof
  through the GLM profile, and a forced-exhaustion proof showing fail-closed
  status.
- Docs close-out: `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run handoff-validate`, `git diff --check`.

## Stop Conditions

- The documented Luna or GLM model identifiers cannot be verified in current
  provider documentation: stop and confirm with the user.
- The lease counter would require shared cross-repo state to be correct: stop;
  the accepted design is a fixed local sub-allocation.
- Any pressure to let exhaustion overflow to a paid route: stop; exhaustion is
  a hard stop by decision.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D9  | The exam lane's answer-key completion is remote-API-first, reversing the local-first default for this lane, with the data boundary of teacher exam content only. |
| D10 | GPT-5.6 Luna at low reasoning effort is the default remote model; the exact ID is verified against provider docs at implementation. |
| D11 | The lane's daily budget is a fixed configurable sub-allocation of 5,000,000 tokens (input plus output). |
| D12 | Budgeting is lease-based with no refunds, UTC-midnight reset, and hard fail-closed exhaustion; the backup model is failover-only and draws from the same lease. |
| D13 | GLM-5.3-flash via OpenRouter is the pinned backup profile. |
| D14 | This task lands in sir-convert-a-lot now; the Skriptoteket port carries the configuration over rather than rebuilding it. |
