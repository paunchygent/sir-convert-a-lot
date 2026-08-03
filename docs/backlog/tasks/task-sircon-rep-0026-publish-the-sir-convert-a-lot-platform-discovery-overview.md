---
type: task
id: TASK-SIRCON-REP-0026
title: Publish the Sir Convert-a-Lot platform discovery overview
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-03'
status: in_progress
readiness_review:
  record: inline
  status: approved
  reviewer: user
  decided_at: '2026-08-03T10:00:00+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directive of 2026-08-03 ordered the three remaining ST-SKILL-08-09 conformance slices; every ledger row derives from that accepted parent story (CON-003, CON-004, CON-005) and its Notes on the deferred markdown gate. No independent plan-document-reviewer ran in this session.
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- The .codex/skills/ lane carries a codemap-style skill whose references publish the
  platform discovery overview covering the v2 service layers, conversion routes, sidecars,
  containers, and docs topology
- The overview is reachable from AGENTS.md routing without duplicating route tables
- Docs sync, docs validation, and git diff --check pass; the pre-existing repo-wide
  markdown-gate failure is recorded as deferred, not repaired here
---

## Context

The Discovery Docs And Codemap Placement policy in the shared
`agent-docs-governance` skill requires every governed repo to carry one platform
discovery overview in its repo-local skills lane. Sir Convert-a-Lot carries
none. `.codex/skills/` holds four operational skills (Hemma devops, Qwen
finetuning, speech-model finetuning, Colab/Hemma orchestration) and no map of
the repository itself. `README.md` states conversion routes and commands but not
topology, and the application package sits under `scripts/`, which reads as
tooling rather than product. A fresh agent session has no single entry point.

The cross-repo sequence is organized in skill-repository story ST-SKILL-08-09;
this task executes only the Sir Convert-a-Lot file mutation.

## Impact And Escalation

The affected surfaces are repository-governance prose: a new
`.codex/skills/repo-code-map/` lane and one route line in `AGENTS.md`. No
product behavior, service, container, or deploy change. No escalation to an epic
or story is required.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID      | Type    | Status | Question/Assumption                                     | Recommendation/Decision                                                                                                                                                                                              | Source                                                              |
| ------- | ------- | ------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| SCO-001 | target  | closed | Where does the overview live?                           | A new `.codex/skills/repo-code-map/` skill: `SKILL.md` router plus `references/platform-discovery-overview.md`, mirroring the hub's own lane and HuleEdu's `service-code-map` shape.                                  | Discovery Docs And Codemap Placement policy; ST-SKILL-08-09 CON-003 |
| SCO-002 | depth   | closed | Overview only, or a full codemap lane?                  | Overview only. Sir Convert-a-Lot is one service, not a service fan-out, so the lane carries a single map.                                                                                                            | ST-SKILL-08-09 CON-004                                              |
| SCO-003 | content | closed | What does the overview cover, from where?               | Authored from repository state with an as-of marker: the application layers under `scripts/sir_convert_a_lot/`, conversion routes and the job model, sidecars and container lanes, execution lanes, and docs topology. | Docs Shape rules; discovery evidence 2026-08-03                     |
| SCO-004 | routing | closed | How is the overview reachable?                          | One route line added to the `AGENTS.md` repo-specific route table.                                                                                                                                                  | Entrypoint-design reference; placement policy                       |
| SCO-005 | gate    | closed | What happens to the broken repo-wide markdown gate?     | Defer, do not repair. `check-md` and `format-md` fail repo-wide on the missing `gfm` extension before this change and after it; the failure is named in the overview and here, and repair needs its own task.        | ST-SKILL-08-09 Notes; scope boundary of this slice                  |
| SCO-006 | proof   | closed | What proves this prose-only slice with one gate broken? | Validator proof through the gates that run: `docs-sync`, `docs-validate`, and `git diff --check`, plus a recorded before/after reproduction of the `gfm` failure showing this slice neither caused nor changed it.    | ST-SKILL-08-09 CON-005; proof-selection rules                       |

## Plan

Create `.codex/skills/repo-code-map/` with a minimal `SKILL.md` router and
author `references/platform-discovery-overview.md` from repository state
(topology, conversion routes, execution lanes, ownership boundaries, links to
existing authoritative surfaces instead of restated prose, an as-of marker), add
one `AGENTS.md` route line, and run the gates that run.

## Implementation Steps

1. Reproduce the `gfm` markdown-gate failure on an unchanged file to establish
   it as pre-existing.
2. Create `.codex/skills/repo-code-map/SKILL.md` as a minimal router to the
   overview reference.
3. Author `references/platform-discovery-overview.md` with an as-of marker;
   link to existing authorities rather than duplicating them, and name the two
   current validator gaps.
4. Add one route line to the `AGENTS.md` repo-specific route table.
5. Run the validation commands listed below.

## Proof

- Proof mode: validator proof (SCO-006).
- Pre-change: `.codex/skills/` holds four skills and no discovery overview;
  `pdm run check-md AGENTS.md` exits 1 with
  `The required 'gfm' extension is not available` on the unchanged tree.
- Post-change: the lane and overview exist, are routed from `AGENTS.md`,
  `docs-sync` and `docs-validate` exit 0, `git diff --check` exits 0, and
  `check-md` reproduces the same pre-existing `gfm` failure with the same
  message.

## Validation

- `pdm run docs-sync`
- `pdm run docs-validate`
- `git diff --check`
- `pdm run check-md <changed files>` — expected to fail on the pre-existing
  `gfm` extension error, recorded as deferred by SCO-005, not as a result of
  this change.

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Readiness

- Ledger closure: SCO-001 through SCO-006 all closed against the accepted
  ST-SKILL-08-09 contract, its Notes on the Sir Convert-a-Lot markdown gate, and
  the Discovery Docs And Codemap Placement policy.
- Authority evidence: user directive of 2026-08-03 to run the three remaining
  conformance slices, plus the parent story's approved readiness review.
- Permitted next step: implement the two-file lane and the one-line
  `AGENTS.md` route, then run the gates that run.
- Residual risk: no independent plan-document-reviewer ran in this session, so
  the readiness gate rests on user closure and parent-contract derivation
  alone.

## Closeout

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

- Supplied proof (implementer-reported, pending independent review):
  `.codex/skills/repo-code-map/` created with exactly the two contracted files;
  the `AGENTS.md` diff is one inserted route line; `pdm run docs-sync` exit 0;
  `pdm run docs-validate` exit 0; `git diff --check` exit 0;
  `pdm run check-md` exit 1 with the identical `gfm` extension error observed on
  the unchanged tree before the change.
- Findings: this repository binds no `skills-validate` and no
  `handoff-validate` script, so the new skill lane has no structural validator
  coverage here, and the shared `agent-docs-governance` Sir Convert-a-Lot
  reference names both commands as if they existed. Repo-reference alignment is
  an ST-SKILL-08-09 non-goal, so both facts are recorded in the overview's
  validation section instead of repaired here.
- Validation not run: repository quality gates (`format`, `lint`, `typecheck`,
  `test`, `coverage-gate`) are not applicable — no Python source changed.
- Residual risk: markdown formatting of the three changed prose files is
  unenforced while the `gfm` gate is broken, and the new lane is unvalidated
  structurally. Both need their own repair tasks.
