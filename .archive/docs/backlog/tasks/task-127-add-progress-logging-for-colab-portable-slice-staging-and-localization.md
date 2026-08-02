---
id: task-127-add-progress-logging-for-colab-portable-slice-staging-and-localization
title: Add progress logging for Colab portable-slice staging and localization
type: task
status: completed
priority: high
created: '2026-03-10'
last_updated: '2026-03-10'
related:
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/backlog/tasks/task-126-fix-colab-portable-slice-notebook-repo-bootstrap-url.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - notebook
  - observability
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add repo-owned progress logging for portable-slice staging and localization so
Colab operators can see archive-level movement, extracted-file counts, and
elapsed timings instead of waiting through silent long-running cells.

## PR Scope

- Emit one progress line for each required archive download/copy.
- Emit localization start/end progress per archive.
- Surface extracted versus reused file counts.
- Emit elapsed time for staging and localization totals.
- Keep the CLI JSON result contract intact.

## Deliverables

- [x] One Task 121 CLI progress surface for required-file staging.
- [x] One Task 121 CLI progress surface for per-archive localization.
- [x] Focused regression coverage for the progress output.
- [x] One completed task doc recording the change.

## Acceptance Criteria

- [x] Colab operators see per-archive staging progress.
- [x] Colab operators see per-archive localization progress.
- [x] Extracted file counts are emitted during localization.
- [x] Elapsed time for staging and localization is visible in CLI output.
- [x] The final JSON result payload remains intact after the progress lines.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
