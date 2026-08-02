---
type: task
id: TASK-SIRCON-REP-0010
title: Add auth-aware public-edge access evidence for Sir Convert cutover
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- '- [ ] API-key presence is represented only as `present`, `absent`, or `unavailable`;
  key values are never logged.'
- '- [ ] The evidence window is named with start/end timestamps.'
- '- [ ] Unknown public consumers are either ruled out by evidence or remain an explicit
  Task 263 cutover blocker.'
- '- [ ] The final cutover proof consumes this evidence before declaring `convert.hule.education`
  ready for Gateway-fronted live testing.'
retired_ids:
- task-266-add-auth-aware-public-edge-access-evidence-for-sir-convert-cutover
---


## Context

State the repository problem, current behavior, and why this bounded task is
needed.

## Impact And Escalation

State the affected repository-governance or developer-tooling surface. Escalate
product behavior into an epic and story instead of implementing it here.
Product behavior excludes skill prose, repository-governance prose including
`AGENTS.md`, optimization, bug fixing, and behavior-neutral implementation
details that affect neither producers nor consumers.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

## Plan

State the smallest implementation approach that satisfies the accepted ledger
and acceptance criteria.

## Implementation Steps

List ordered, bounded edits and their integration order. Do not add work that is
not derived from the task contract.

## Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

## Validation

List the exact repository commands required before closeout and retain concise
results after they run.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Readiness

Record ledger closure, authority evidence, permitted next step, and residual
risk. The `readiness_review` frontmatter mapping is the machine authority for
gate status.

## Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

## Source Body Preservation

PR-sized execution unit; may be linked to a story or standalone.
## Objective
Add an auth-aware, redacted public-edge evidence surface before the final Sir Convert Gateway cutover so unknown direct public consumers can be classified without exposing secrets or persisting raw request headers.
## PR Scope
- Define a safe nginx-proxy, app, or sidecar log format that records:
  - host;
  - method;
  - normalized route bucket;
  - status;
  - upstream target;
  - user-agent class;
  - request-id or correlation id when present;
  - API-key presence as a boolean only, never the key value.
- Keep IP addresses, API keys, cookies, bearer tokens, identity headers, query
strings, and artifact/job identifiers out of durable artifacts.
- Capture a defined pre-cutover evidence window after Task 265 reserved public
edge is live.
- Produce redacted route/status/API-key-presence counts for
`convert.hule.education`.
- Feed the result into Task 263 final cutover proof and the caller inventory
reference.
## Deliverables
- [ ] Safe log-format or collector plan.
- [ ] Redacted public-edge evidence artifact with route/status/API-key-presence
counts.
- [ ] Inventory reference update classifying or blocking unknown public
consumers.
- [ ] Proof that no secrets or raw identity material are persisted.
## Acceptance Criteria
- [ ] API-key presence is represented only as `present`, `absent`, or
`unavailable`; key values are never logged.
- [ ] The evidence window is named with start/end timestamps.
- [ ] Unknown public consumers are either ruled out by evidence or remain an
explicit Task 263 cutover blocker.
- [ ] The final cutover proof consumes this evidence before declaring
`convert.hule.education` ready for Gateway-fronted live testing.
## Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

