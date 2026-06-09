---
id: task-170-align-dockerfiles-runbooks-and-backlog-to-domain-centric-structure
title: Align Dockerfiles Runbooks and Backlog to Domain-Centric Structure
type: task
status: proposed
priority: high
created: '2026-03-13'
last_updated: '2026-03-13'
related:
  - docs/backlog/stories/story-27-transition-to-domain-centric-ml-pipeline-structure.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
labels:
  - refactor
  - docs
  - docker
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Complete the domain-centric transition by updating all external references to the
ML pipeline, including Docker entrypoints, runbooks, and active backlog documentation.

## PR Scope

- Update `containers/qwen-finetune-hemma/Dockerfile` with the new in-container paths.
- Update `docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md`
- Update `AGENTS.md` and related system-level docs.
- Move and update `tests/sir_convert_a_lot/task103_*.py` to `tests/sir_convert_a_lot/ml/qwen/preprocessing/`.
- Final audit of all `taskXXX` prefixes in the codebase.

## Deliverables

- [ ] Dockerfiles updated.
- [ ] Runbooks and AGENTS.md updated.
- [ ] Test suite aligned with the new structure.

## Acceptance Criteria

- [ ] `docker buildx build --load` for the Qwen image succeeds with the new
  structure.
- [ ] Runbook steps are verified against the new command names.
- [ ] `pdm run validate-docs` and `pdm run validate-tasks` pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
