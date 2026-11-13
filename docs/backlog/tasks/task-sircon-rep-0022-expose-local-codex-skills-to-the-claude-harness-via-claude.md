---
type: task
id: TASK-SIRCON-REP-0022
title: Expose local codex skills to the Claude harness via claude skills symlink
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-03'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-08-03T01:00:23+02:00'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User opened the symlink lane on 2026-08-03; independent plan-document-reviewer
    subagent approved in round 3 after the markdown-gate deferral was made truthful
    and unconditional.
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-code-review
  decided_at: '2026-08-03T01:58:29+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent closeout subagent (not the implementer) verified the
    symlink resolution, all four SKILL.md reads, the deferred markdown gate, and scope;
    approved with zero blocking findings.
task_kind: repository
acceptance_criteria:
- A committed relative symlink at .claude/skills resolves to .codex/skills so the
  Claude harness discovers local skills at session start
- Every local skill SKILL.md is readable through the symlinked path
- Docs validation passes and git diff --check is clean; the markdown gate is
  deferred unconditionally because repo-wide check-md fails on a missing gfm
  extension and no repair task exists yet — opening one is a named follow-up
  at closeout
---

## Context

The Claude Code harness discovers skills only under `.claude/skills/` and does
not load the repo's four local skills in `.codex/skills/`
(`sir-convert-a-lot-colab-hemma`, `sir-convert-a-lot-devops-hemma`,
`sir-convert-a-lot-qwen-finetuning`, `speech-model-finetuning-on-hemma`). The
shared Discovery Docs And Codemap Placement policy delivers local skills to
such harnesses by symlink from the local skill source into the harness folder.
`.claude/` does not exist yet and is not gitignored.

## Impact And Escalation

The affected surface is one committed symlink under a new `.claude/`
directory. No product behavior, service, or deploy changes. No escalation to
an epic or story is required.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID      | Type      | Status | Question/Assumption                       | Recommendation/Decision                                                                                                                                       | Other highly plausible options                | Motivation                                                                                                                                              | Source                                          |
| ------- | --------- | ------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| SYM-001 | scope     | closed | Which skills are exposed to the harness?  | All local `.codex/skills/` skills, via one link covering the whole folder. The folder's `README.md` index rides along harmlessly.                              | Expose only actively used skills.             | Partial exposure recreates discovery drift; the user opened the lane for local-skill discovery as such.                                                 | User direction in session chat, 2026-08-03       |
| SYM-002 | mechanism | closed | Directory symlink or per-skill symlinks?  | One committed relative symlink `.claude/skills -> ../.codex/skills`.                                                                                          | Per-skill symlinks inside `.claude/skills/`.  | A single durable link keeps one authored source and auto-covers future skills per the delivery policy; per-skill links only matter when sources mix.    | Discovery Docs And Codemap Placement policy       |
| SYM-003 | tracking  | closed | Is the symlink committed?                 | Yes, committed.                                                                                                                                                | Leave it untracked as local machine state.    | `.claude` is unignored; a committed link serves every clone.                                                                                            | Discovery evidence, 2026-08-03                    |
| SYM-004 | proof     | closed | What proves the change?                   | Validator proof: the link resolves, every `SKILL.md` is readable through it, docs validation passes, `git diff --check` clean. The markdown gate is deferred unconditionally: repo-wide `pdm run check-md` fails with a missing `gfm` extension, a pre-existing toolchain defect with no repair task yet; opening that task is a named follow-up at closeout. | Live harness-session discovery proof.         | Harness session start is manual; structural resolution through the link is the automatable observable. Live discovery is confirmed at next session start. | Proof-selection rules; toolchain evidence 2026-08-03 |

## Plan

Create `.claude/` with the relative symlink `.claude/skills ->
../.codex/skills`, commit it, and verify resolution and gates. Live harness
discovery is confirmed by the user's next Claude session in this repo.

## Implementation Steps

1. `mkdir .claude && ln -s ../.codex/skills .claude/skills` from the repo
   root.
2. Verify every local skill's `SKILL.md` is readable through the link.
3. Run the validation commands listed below.

## Proof

- Proof mode: validator proof (SYM-004).
- Pre-change: `.claude/` does not exist.
- Post-change: `ls .claude/skills/` lists the four skills and each
  `SKILL.md` reads through the link.

## Validation

- `pdm run docs-validate docs/backlog/tasks/task-sircon-rep-0022-expose-local-codex-skills-to-the-claude-harness-via-claude-skills-symlink.md`
- `pdm run check-md <changed files>` — deferred unconditionally: it fails
  repo-wide (missing `gfm` extension) and no repair task exists yet. Record
  the deferral in Closeout and open the toolchain-repair task as a named
  follow-up.
- `git diff --check`

## Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to the task owner.

## Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

## Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

## Readiness

- Ledger closure: SYM-001 through SYM-004 closed; no open rows.
- Authority evidence: the user opened the symlink lane in the working session
  of 2026-08-03 (session chat; recorded here as the durable authority).
  Mechanism and delivery direction close on the shared placement policy.
- Plan review: round 1 found the markdown-gate assertion unsatisfiable
  (repo-wide `check-md` fails on a missing `gfm` extension); round 3 approved
  after the deferral was made truthful and unconditional, with the
  toolchain-repair task recorded as a closeout follow-up.
- Permitted next step: delegated implementation by a subagent that is not the
  reviewer, on explicit user implementation authority.
- Residual risk: the repo has no working markdown gate until the follow-up
  repair task is opened and done; live harness discovery is confirmed only at
  the user's next Claude session start in this repo.

## Closeout

- Supplied proof: `readlink .claude/skills` returns `../.codex/skills`; all
  four skills' `SKILL.md` read through the link (with `README.md` riding
  along per SYM-001); scoped `docs-validate` exit 0; `git diff --check`
  exit 0; `git check-ignore` exit 1 proves committability.
- Findings: independent closeout review approved with zero blocking findings.
- Validation not run: the markdown gate, deferred unconditionally per SYM-004.
  The named follow-up is now open: TASK-SIRCON-REP-0023 repairs the
  repo-wide `check-md` `gfm`-extension failure.
- Permitted next step: parent integration and push; live harness discovery
  confirmed at the user's next Claude session in this repo.
- Residual risk: the repo has no working markdown gate until
  TASK-SIRCON-REP-0023 is done.
