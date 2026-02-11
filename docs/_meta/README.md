---
type: meta
id: META-docs-contract
title: Docs Contract
status: active
created: '2026-02-11'
updated: '2026-02-11'
owners:
  - platform
tags:
  - docs-as-code
  - contract
links:
  - docs/\_meta/docs-contract.yaml
---

Documentation in this repository is governed by a strict, machine-validated contract.

## Source of Truth

- `docs/_meta/docs-contract.yaml`

## What Is Enforced

- YAML frontmatter presence and parsing for docs and rules.
- Required metadata keys per docs section and rules.
- Status values, type values, and regex checks for IDs/filenames where configured.
- Unknown frontmatter keys are rejected unless added to the contract.

## Commands

```bash
pdm run validate-docs
pdm run validate-tasks
pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing
```
