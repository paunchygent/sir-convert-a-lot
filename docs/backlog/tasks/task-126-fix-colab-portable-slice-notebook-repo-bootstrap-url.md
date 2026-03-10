---
id: 'task-126-fix-colab-portable-slice-notebook-repo-bootstrap-url'
title: 'Correct Colab portable-slice notebook repo bootstrap URL'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - notebook
  - bugfix
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Fix the portable-slice Colab notebook bootstrap so a press-run Colab session
clones the canonical Sir Convert-a-Lot repo instead of failing on a stale
GitHub owner URL.

## PR Scope

- Replace the stale hardcoded Colab clone URL with the canonical repo URL.
- Allow an environment override for notebook bootstrap when temporary forks are
  intentionally needed.
- Keep the notebook bootstrap thin and deterministic.

## Deliverables

- [x] One notebook bootstrap cell that defaults to the canonical GitHub repo.
- [x] One environment override for explicit alternate clone sources.
- [x] One completed task doc recording the bugfix.

## Acceptance Criteria

- [x] A fresh Colab runtime no longer attempts to clone
      `https://github.com/olofsg/sir-convert-a-lot.git`.
- [x] The notebook defaults to the canonical repo URL and can still be
      overridden intentionally through an environment variable.
- [x] The notebook remains valid JSON after the fix.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
