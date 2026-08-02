---
type: task
id: TASK-SIRCON-REP-0017
title: Restore docx output after pandoc sandbox hardening
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- '`pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py`
  passes.'
- '`pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py`
  passes.'
- '`pdm run run-local-pdm typecheck-all` passes.'
- '`pdm run run-local-pdm coverage-gate` remains >=90%.'
- 'Live operator tunnel lane smoke: - `pdm run run-local-pdm convert-a-lot convert
  <md> --to docx --service-url http://127.0.0.1:28085` succeeds. - `pdm run run-local-pdm
  convert-a-lot convert <pdf> --to docx --service-url http://127.0.0.1:28085` succeeds.'
retired_ids:
- task-62-fix-docx-output-regression-after-pandoc-sandbox-hardening
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

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Restore v2 DOCX output routes (`md -> docx`, `html -> docx`, `pdf -> docx`) in
production after discovering that `pandoc --sandbox` prevents Pandoc's DOCX
writer from accessing its required built-in data files.

Maintain SSRF/LFI protections by enforcing deterministic HTML resource
validation and workdir-bounded resource resolution, rather than relying on
Pandoc sandbox mode for DOCX output.

## PR Scope

- Remove `--sandbox` from Pandoc wrappers that must write DOCX artifacts:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_docx.py`
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_markdown_to_html.py`
- Keep `--sandbox` enforced for Pandoc wrappers that do not require DOCX writer
  data files:
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_docx_to_markdown.py`
  - `scripts/sir_convert_a_lot/infrastructure/pandoc_html_to_markdown.py`
- Add deterministic HTML resource validation for `md -> html -> docx` so that
  any external URLs / invalid local references fail closed with `422` before
  Pandoc is invoked.
- Update tests to reflect the revised security posture and to prevent
  reintroducing the DOCX writer regression.

## Deliverables

- [ ] DOCX output routes succeed again in the operator tunnel lane
  (`http://127.0.0.1:28085`). The public `convert.hule.education` edge remains
  reserved/fail-closed.
- [ ] SSRF/LFI is still blocked for DOCX routes via validation + workdir sandboxing.
- [ ] Tests updated for sandbox flag expectations and DOCX output behavior.

## Acceptance Criteria

- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py` passes.
- [x] `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py` passes.
- [x] `pdm run run-local-pdm typecheck-all` passes.
- [x] `pdm run run-local-pdm coverage-gate` remains >=90%.
- [ ] Live operator tunnel lane smoke:
  - `pdm run run-local-pdm convert-a-lot convert <md> --to docx --service-url http://127.0.0.1:28085` succeeds.
  - `pdm run run-local-pdm convert-a-lot convert <pdf> --to docx --service-url http://127.0.0.1:28085` succeeds.

## Validation Evidence

Local (laptop) validation (2026-03-01):

- Formatting:
  - `pdm run run-local-pdm format-all` (pass; "159 files left unchanged")
- Lint:
  - `pdm run run-local-pdm lint-fix` (pass; "Found 1 error (1 fixed, 0 remaining).")
- Type safety:
  - `pdm run run-local-pdm typecheck-all`
    (pass; "Success: no issues found in 157 source files")
- Coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass; total coverage `95.24%` with required threshold `90.0%`)
- Docs-as-code gates:
  - `pdm run validate-tasks` (pass; "Validated 87 backlog files")
  - `pdm run validate-docs` (pass; "Validated docs=109 rules=9")
- Task-targeted checks:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_cli_v2_routes.py` (pass; 5 passed)
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_pandoc_additional_timeout_wrappers.py` (pass; 6 passed)

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
