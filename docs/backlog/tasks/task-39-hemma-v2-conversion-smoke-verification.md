---
id: task-39-hemma-v2-conversion-smoke-verification
title: Hemma v2 conversion smoke verification
type: task
status: proposed
priority: high
created: '2026-02-18'
last_updated: '2026-02-18'
related:
  - docs/backlog/epics/epic-04-converter-suite-parity-with-html-to-pdf-handout-templates.md
  - docs/backlog/stories/story-08-cli-multi-format-routing-and-deterministic-manifests.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - hemma
  - smoke
  - v2
  - devops
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Produce deterministic, written evidence that the **dockerized Hemma runtime** can execute the
service API v2 critical routes end-to-end, including:

- service availability (`healthz`, `readyz`)
- runtime dependencies (Pandoc + WeasyPrint native deps present)
- successful conversions for:
  - `html -> pdf` (WeasyPrint)
  - `md -> pdf` (Pandoc -> HTML -> WeasyPrint)
  - `md -> docx` (Pandoc -> HTML -> Pandoc)
  - `pdf -> docx` (PDF->MD via v1 backends + Pandoc)

This repo is internal today, but Hemma is the canonical execution target; smoke evidence must come
from Hemma, not laptop-local converters.

## PR Scope

- Add a canonical verifier surface (script + PDM command) that can be run repeatedly:
  - new script: `scripts/devops/verify-hemma-v2-conversions.sh`
  - new PDM script: `hemma-verify-v2-conversions`
- The verifier must:
  - assert service profile + revision readiness via `readyz`
  - probe `pandoc --version` in the docker runtime
  - execute one conversion per v2 route class (small fixtures)
  - emit an evidence report under `build/verification/task-39-v2-smoke/`
- Update the Hemma runbook with a short “v2 smoke” section pointing to the script.

## Deliverables

- [ ] Hemma v2 smoke verifier script exists and is documented
- [ ] Evidence report exists under `build/verification/task-39-v2-smoke/`
- [ ] Runbook section exists for repeatable verification

## Acceptance Criteria

- [ ] Running `pdm run run-local-pdm hemma-verify-v2-conversions` completes successfully against the
  docker lane on Hemma.
- [ ] Each of the 4 critical v2 routes produces a non-empty artifact (PDF/DOCX) and records the
  corresponding `job_id` in the report.
- [ ] `pdf -> docx` evidence includes the selected PDF backend + acceleration used in conversion
  metadata (GPU governance is still enforced for that stage).
- [ ] The locked v1 `pdf -> md` route remains operational (smoke includes one v1 submission).

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
