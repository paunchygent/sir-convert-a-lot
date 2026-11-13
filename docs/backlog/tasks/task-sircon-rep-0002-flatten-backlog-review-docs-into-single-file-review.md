---
type: task
id: TASK-SIRCON-REP-0002
title: Flatten backlog review docs into single-file review artifacts
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
- '`pdm run new-review "<title>"` creates one flat markdown file, not a folder with
  `README.md`.'
- '`pdm run validate-tasks` enforces the flat review location consistently.'
- Existing reviews validate without folder-specific exceptions.
- '`pdm run validate-docs` and `pdm run index-tasks ...` both pass after the migration.'
retired_ids:
- task-120-flatten-backlog-review-docs-into-single-file-review-artifacts
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

### Context

State the repository problem, current behavior, and why this bounded task is
needed.

### Impact And Escalation

State the affected repository-governance or developer-tooling surface. Escalate
product behavior into an epic and story instead of implementing it here.
Product behavior excludes skill prose, repository-governance prose including
`AGENTS.md`, optimization, bug fixing, and behavior-neutral implementation
details that affect neither producers nor consumers.

### Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

### Plan

State the smallest implementation approach that satisfies the accepted ledger
and acceptance criteria.

### Implementation Steps

List ordered, bounded edits and their integration order. Do not add work that is
not derived from the task contract.

### Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

### Validation

List the exact repository commands required before closeout and retain concise
results after they run.

### Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

### Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

### Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

### Readiness

Record ledger closure, authority evidence, permitted next step, and residual
risk. The `readiness_review` frontmatter mapping is the machine authority for
gate status.

### Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

PR-sized execution unit; may be linked to a story or standalone.
### Objective
Replace the current folder-plus-`README.md` backlog review contract with a single-file review shape so the creation surface, validators, and day-to-day editing model stop fighting each other.
### Why This Exists
The repo currently has a self-inflicted mismatch:
- `new-review` scaffolds `docs/backlog/reviews/<review-id>/README.md`
- `validate_tasks` hardcodes that same folder shape
- the docs contract also allows flat `review-*.md` files
That hybrid model makes nested evidence awkward, creates confusing review paths, and adds unnecessary `README.md` ceremony to a document type that should just be one backlog artifact.
### PR Scope
- Change the canonical backlog review shape to:
  - `docs/backlog/reviews/review-<nn>-<slug>.md`
- Update:
  - docs contract,
  - review scaffold generation,
  - task validator location rules.
- Migrate existing reviews to the new flat file shape.
- Repair any repo references that still point at folder-based review paths.
### Non-Goals
- Do not change the semantic sections required for reviews.
- Do not redesign non-review backlog document shapes.
- Do not weaken review validation; only make the location contract sane.
### Deliverables
- [ ] Single-file review contract in docs tooling and validators.
- [ ] Existing reviews migrated to flat review files.
- [ ] Backlog/docs references updated to the new canonical paths.
### Acceptance Criteria
- [ ] `pdm run new-review "<title>"` creates one flat markdown file, not a
folder with `README.md`.
- [ ] `pdm run validate-tasks` enforces the flat review location consistently.
- [ ] Existing reviews validate without folder-specific exceptions.
- [ ] `pdm run validate-docs` and `pdm run index-tasks ...` both pass after the
migration.
### Validation
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
### Checklist
- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
