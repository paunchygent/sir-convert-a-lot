---
type: task
id: TASK-SIRCON-REP-0004
title: Refresh existing Colab repo checkout before portable bundle lookup
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
- "[x] Re-entering the notebook from an already-cloned `/content/sir-convert-a-lot`\n\
  \  path performs `fetch` / `checkout main` / `pull --ff-only`."
- '[x] A newly cloned repo still works without a second manual refresh step.'
- "[x] The portable bundle lookup no longer fails simply because the Colab repo\n\
  \  clone predates the latest committed bundle."
retired_ids:
- task-130-refresh-existing-colab-repo-checkout-before-portable-bundle-lookup
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

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Ensure the Colab portable-slice notebook refreshes an already-present
`/content/sir-convert-a-lot` checkout before it looks for a committed portable
bundle, so a notebook session that started before a later bundle commit does
not fail with a false missing-bundle error.

### PR Scope

- Refresh the existing repo checkout to `origin/main` when the notebook detects
  a usable local clone.
- Preserve the current clone-if-missing behavior.
- Keep the notebook thin and repo-owned; do not move bundle lookup logic into
  ad hoc workaround cells.
- Record the failure mode in the task doc.

### Deliverables

- [x] One notebook bootstrap path that refreshes an existing repo checkout.
- [x] One task doc that records the stale-clone failure mode and fix.

### Acceptance Criteria

- [x] Re-entering the notebook from an already-cloned `/content/sir-convert-a-lot`
  path performs `fetch` / `checkout main` / `pull --ff-only`.
- [x] A newly cloned repo still works without a second manual refresh step.
- [x] The portable bundle lookup no longer fails simply because the Colab repo
  clone predates the latest committed bundle.

### Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
