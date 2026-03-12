---
id: task-120-flatten-backlog-review-docs-into-single-file-review-artifacts
title: Flatten backlog review docs into single-file review artifacts
type: task
status: proposed
priority: high
created: '2026-03-09'
last_updated: '2026-03-09'
related:
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot.md
  - docs/backlog/reviews/review-02-review-of-qwen3-tts-swedish-finetuning-architecture.md
  - docs/backlog/current.md
labels:
  - docs-as-code
  - reviews
  - validation
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the current folder-plus-`README.md` backlog review contract with a
single-file review shape so the creation surface, validators, and day-to-day
editing model stop fighting each other.

## Why This Exists

The repo currently has a self-inflicted mismatch:

- `new-review` scaffolds `docs/backlog/reviews/<review-id>/README.md`
- `validate_tasks` hardcodes that same folder shape
- the docs contract also allows flat `review-*.md` files

That hybrid model makes nested evidence awkward, creates confusing review paths,
and adds unnecessary `README.md` ceremony to a document type that should just
be one backlog artifact.

## PR Scope

- Change the canonical backlog review shape to:
  - `docs/backlog/reviews/review-<nn>-<slug>.md`
- Update:
  - docs contract,
  - review scaffold generation,
  - task validator location rules.
- Migrate existing reviews to the new flat file shape.
- Repair any repo references that still point at folder-based review paths.

## Non-Goals

- Do not change the semantic sections required for reviews.
- Do not redesign non-review backlog document shapes.
- Do not weaken review validation; only make the location contract sane.

## Deliverables

- [ ] Single-file review contract in docs tooling and validators.
- [ ] Existing reviews migrated to flat review files.
- [ ] Backlog/docs references updated to the new canonical paths.

## Acceptance Criteria

- [ ] `pdm run new-review "<title>"` creates one flat markdown file, not a
  folder with `README.md`.
- [ ] `pdm run validate-tasks` enforces the flat review location consistently.
- [ ] Existing reviews validate without folder-specific exceptions.
- [ ] `pdm run validate-docs` and `pdm run index-tasks ...` both pass after the
  migration.

## Validation

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
