---
id: 'task-132-decompose-task103-test-surface-by-domain'
title: 'Decompose Task 103 test surface by domain'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-11'
last_updated: '2026-03-11'
related:
  - docs/backlog/tasks/task-103-build-the-qwen3-tts-swedish-preprocessing-and-manifest-pipeline.md
  - docs/backlog/tasks/task-123-add-resumable-row-processing-for-qwen-preprocessing-runs.md
  - docs/backlog/tasks/task-131-add-backward-compatible-resume-index-for-drive-backed-qwen-row-processing.md
  - docs/reference/ref-qwen3-tts-swedish-preprocessing-and-manifest-spec.md
labels:
  - qwen
  - preprocessing
  - testing
  - modularity
  - srp
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Decompose the monolithic Task 103 preprocessing test surface into
domain-focused test modules so the Qwen preprocessing area is easier to reason
about, easier to refactor safely, and better aligned with SRP and the repo's
modularity standards.

## Problem Statement

`tests/sir_convert_a_lot/test_task103_qwen_preprocessing.py` currently mixes:

- CLI argument parsing
- runner orchestration
- row-processing and resume behavior
- finalization behavior
- source adapter loading
- staged public corpus integration
- ASR runtime behavior

in one oversized file. This is still executable, but it hides the domain seams
that future Task 103 refactors need to rely on, and it makes review and change
scoping less honest than the underlying code deserves.

## PR Scope

- Introduce one shared Task 103 test-support module for reusable fixtures and
  helper builders.
- Split the current monolithic Task 103 test file into multiple domain-focused
  test modules with clear reasons to change.
- Keep test behavior stable; this task is about decomposition, not changing the
  Task 103 runtime contract.
- Preserve discoverability by using module docstrings that explain the purpose
  and relationships of the new test modules.

## Deliverables

- [x] One shared Task 103 test-support module.
- [x] One domain-focused test module for Task 103 runner / orchestration
      behavior.
- [x] One domain-focused test module for preprocessing, row-processing, resume,
      and finalization behavior.
- [x] One domain-focused test module for source adapters and staged-public-corpus
      behavior.
- [x] One domain-focused test module for ASR runtime behavior.
- [x] Updated docs memory that records the decomposition as the next
      preprocessing-quality hardening step.

## Acceptance Criteria

- [x] The old monolithic Task 103 test file is removed or reduced so the domain
      decomposition is real rather than duplicated.
- [x] Each new test module has one clear dominant reason to change.
- [x] Shared helpers live in one support module instead of being copy-pasted
      across the new test files.
- [x] Focused Task 103 tests still pass after the split.
- [x] The decomposition makes the next Task 103 production refactors safer
      without changing user-facing preprocessing behavior.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
