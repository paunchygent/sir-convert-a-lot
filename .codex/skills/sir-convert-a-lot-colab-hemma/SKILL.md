---
name: sir-convert-a-lot-colab-hemma
description: >-
  Workflow skill for Sir Convert-a-Lot Colab notebook orchestration and
  Hemma-backed preprocessing iteration. Use when the task involves portable
  Colab Qwen slices, notebook-backed row-processing, syncing code between Colab
  and Hemma, or deciding where code edits and git operations should happen for
  a Hemma-executed lane. Trigger especially when a Colab notebook is only the
  operator shell and the real execution, artifacts, or canonical repo state
  live on Hemma.
---

# Sir Convert-a-Lot Colab Hemma

## Purpose

Keep Colab thin, keep Hemma authoritative, and keep repo iteration close to the
runtime that will actually execute the work.

Use this skill together with:

- `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`
- `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md`
- `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`

## Core Rule

If the execution lane is Hemma-backed, do the repo edits on Hemma and push from
Hemma.

Apply that rule to:

- Python/module changes for Hemma-run preprocessing or training
- notebook edits when the notebook is loaded from the Hemma repo
- dependency changes needed by the Hemma execution lane
- commits and pushes for Hemma-owned work

Do not default to editing locally first and then trying to replay the same
changes on Hemma. That adds latency, risks drift, and makes notebook/runtime
debugging slower.

## Workflow

1. Classify the lane.
   - `Hemma-backed lane`: Hemma is the execution truth for preprocessing,
     training, artifact generation, or the notebook source tree.
   - `Colab-only lane`: Colab is disposable compute, but the notebook still
     orchestrates committed repo commands.
1. Decide where repo edits belong.
   - If `Hemma-backed lane`, edit in the Hemma repo clone and push from Hemma.
   - If purely local planning/docs work with no Hemma execution dependency,
     local edits are acceptable.
1. Keep notebooks thin.
   - The notebook may install deps, define paths, and invoke committed CLI or
     module surfaces.
   - Do not move archive resolution, row selection, or preprocessing logic into
     notebook-only cells.
1. Sync in the safe direction.
   - For Hemma-backed work: edit on Hemma, commit on Hemma, push from Hemma,
     then pull locally if a local clone needs the result.
   - For local-only docs or exploratory notes: commit locally only if Hemma is
     not the execution owner for the same slice.

## Colab Rules

- Treat Colab as an operator shell around committed repo surfaces.
- Start from a Hemma-issued portable slice or other committed artifact set.
- Stage only required files.
- Localize the slice through repo-owned commands when needed.
- Run canonical Task 103 row-processing against committed manifests.
- Preserve restartability through repo-owned resume semantics, not notebook
  patches.
- If Colab persists run state into Google Drive and the Drive connector is
  authenticated, inspect `status.json`, spool JSON, and row-processing logs
  directly through Drive before asking the user for manual notebook commands.
- Treat Drive-backed Colab artifacts as part of the operational surface for
  this lane, not as inaccessible notebook-only state.
- If the user provides a direct Drive file or folder link, use that id/path
  first. Do not start with broad search when the precise artifact is already
  known.
- Expect connector quirks:
  - canonical folder URLs work better than `/u/1/` variants
  - metadata lookup by id may succeed even when content fetch or search is weak
  - top-level run-root folders may expose logs immediately while deeper spool or
    status artifacts still need direct links

## Notebook Hygiene

- Expect notebook metadata drift such as kernel display-name changes.
- Do not treat metadata-only notebook edits as meaningful implementation.
- If a Hemma notebook clone picks up metadata-only changes during execution,
  discard them before pull/merge unless the metadata was intentionally changed.

## Command Preference

- Use canonical wrappers for Hemma work:
  - `pdm run run-hemma -- <command> [args]`
- Prefer committed scripts or module surfaces over ad hoc shell payloads.
- Use merge-only git workflow. Never rebase.

## Escalation Guide

Pause and confirm with the user when:

- Hemma has unrelated uncommitted repo changes that are not metadata-only
- the Hemma worktree has diverged from local in ways that would affect runtime
- the fix would require discarding anything beyond obvious notebook metadata
- a change would move logic from repo code back into notebook cells

## Success State

- Hemma remains the source of truth for Hemma-backed execution lanes.
- Colab remains simple enough to "press run."
- Drive-backed Colab artifacts are inspected directly when connector access is
  available.
- The repo history reflects the environment that actually executed the change.
