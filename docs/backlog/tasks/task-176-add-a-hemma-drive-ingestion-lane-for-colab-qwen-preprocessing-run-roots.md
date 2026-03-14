---
id: task-176-add-a-hemma-drive-ingestion-lane-for-colab-qwen-preprocessing-run-roots
title: Add a Hemma Drive-ingestion lane for Colab Qwen preprocessing run roots
type: task
status: proposed
priority: high
created: '2026-03-14'
last_updated: '2026-03-14'
related:
  - docs/backlog/stories/story-24-swedish-multi-speaker-corpus-preprocessing-and-evaluation-for-qwen3-tts.md
  - docs/backlog/tasks/task-121-add-portable-colab-slice-based-qwen-preprocessing-lane.md
  - docs/backlog/tasks/task-124-add-portable-slice-localization-stage-for-colab-qwen-preprocessing.md
  - docs/backlog/tasks/task-129-prepare-large-portable-colab-slice-for-multi-session-qwen-row-processing.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/backlog/tasks/task-137-implement-canonical-qwen-processed-root-dedupe-and-immutable-shard-allocation.md
  - docs/backlog/tasks/task-138-canonicalize-qwen-pilot-ownership-and-salvage-the-remaining-colab-slice.md
  - docs/reference/ref-qwen3-tts-colab-portable-slice-preprocessing.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - colab
  - hemma
  - drive
  - ingestion
  - preprocessing
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Establish one repo-owned Hemma ingestion lane that can pull completed
Drive-backed Colab Task 103 row-processing run roots into canonical Hemma
storage without relying on ad hoc local downloads or notebook-side recovery.

## Problem Statement

The repo already supports portable Colab row-processing and Drive-backed resume,
but the operational bridge back into Hemma is still manual. That leaves a gap
between:

- completed Colab run roots under Google Drive, and
- canonical Hemma ownership, deduplication, and bundle-building workflows.

Without a committed ingestion lane, we risk:

- manual copy drift,
- uncertain provenance for imported Colab artifacts,
- inconsistent import locations,
- and one-off operator procedures whenever Colab work needs to be absorbed into
  canonical processed-root governance.

## PR Scope

- Define one least-privilege Hemma access model for Drive-backed Colab
  artifacts:
  - preferred: `rclone` remote authenticated through a dedicated service
    account shared only to one Colab-artifacts folder,
  - acceptable fallback: user OAuth remote scoped to the same dedicated folder.
- Define one canonical Hemma import root for synced Colab preprocessing run
  roots:
  - `/srv/storage/sir-convert-a-lot/imports/google-drive/qwen-colab/`
- Add one repo-owned import surface that:
  - lists available remote run roots,
  - syncs one selected run root into the canonical Hemma import root,
  - records a deterministic import summary,
  - and refuses ambiguous destination layouts.
- Add one validation surface that proves the imported run root is shaped like a
  canonical Task 103 row-processing root before it is used for dedupe or
  canonical processed-root absorption.
- Keep the first slice limited to preprocessing row-processing artifacts:
  - `run.json`
  - `status.json`
  - `spool/rows/`
  - `audio_24k/`
  - resume index artifacts when present
- Do not expand this task into training artifact sync, model checkpoint sync,
  or generic whole-Drive automation.

## Deliverables

- [ ] One committed runbook section covering the Hemma-side Drive access model.
- [ ] One deterministic Hemma import root for Colab preprocessing artifacts.
- [ ] One repo-owned command surface to list and sync Colab run roots from
  Drive into Hemma storage.
- [ ] One validation surface to verify imported run-root completeness and
  resume-index readability.
- [ ] One import summary artifact that records:
  - remote locator,
  - imported run root,
  - sync timestamp,
  - file counts,
  - validation result.
- [ ] One documented follow-on rule for absorbing validated imported roots into
  canonical processed-root / dedupe workflows.

## Acceptance Criteria

- [ ] Hemma can read a dedicated shared Google Drive folder without needing the
  local workstation to proxy file transfers.
- [ ] The import lane uses repo-owned command surfaces invoked through canonical
  Hemma wrappers rather than ad hoc shell payloads.
- [ ] A completed Colab run root can be synced into
  `/srv/storage/sir-convert-a-lot/imports/google-drive/qwen-colab/` with a
  deterministic destination path.
- [ ] The validation surface fails closed if an imported root is missing any of:
  - `run.json`
  - `status.json`
  - `spool/rows/`
  - `audio_24k/`
- [ ] If a completed-row resume index exists, it is validated through the
  existing helper surface before the run root is treated as healthy.
- [ ] The imported run root can be referenced by later canonical processed-root
  and dedupe workflows without extra notebook-only steps.
- [ ] The auth model is least-privilege and scoped to one dedicated Colab
  artifacts folder rather than broad whole-Drive access.

## Proposed Design Notes

- Auth posture:
  - prefer one service account shared to a dedicated Drive folder
  - store the service-account JSON outside the repo and reference it from the
    Hemma host runtime
  - use user OAuth only if service-account sharing is blocked by the user’s
    Drive topology
- Remote naming:
  - one dedicated `rclone` remote for this repo workflow, not a generic
    personal-drive remote
- Storage posture:
  - sync hot imports to `/srv/storage`, not `/srv/scratch`
  - treat the imported root as colder retained preprocessing truth until it is
    absorbed into canonical processed-root materialization
- Command posture:
  - one repo-owned CLI or script surface for `list`, `sync`, and `validate`
  - invoke through `pdm run run-hemma -- ...`
- Validation posture:
  - reuse the existing resume-index helper for index validation/rebuild
  - do not silently heal malformed imports without recording the result

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
