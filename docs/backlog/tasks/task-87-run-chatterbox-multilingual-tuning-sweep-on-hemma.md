---
id: task-87-run-chatterbox-multilingual-tuning-sweep-on-hemma
title: Run Chatterbox multilingual tuning sweep on Hemma
type: task
status: in_progress
priority: high
created: '2026-03-07'
last_updated: '2026-03-07'
related:
  - docs/backlog/stories/story-23-swedish-capable-cloning-tts-benchmark-matrix-on-hemma.md
  - docs/backlog/tasks/task-86-benchmark-chatterbox-multilingual-swedish-cloning-sidecar-on-hemma.md
  - docs/runbooks/runbook-chatterbox-multilingual-tuning-on-hemma.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/decisions/0007-reusable-multi-backend-tts-sidecar-capability-contract.md
labels:
  - chatterbox
  - tts
  - tuning
  - hemma
  - swedish
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Execute the first Chatterbox tuning sweep on Hemma using only the documented
knobs in the Chatterbox tuning runbook, with deterministic evidence for every
lane and a conservative-first execution order.

## PR Scope

- Add one committed Hemma sweep command surface for the Chatterbox tuning grid.
- Keep the sweep limited to the documented Chatterbox multilingual controls that
  the repo currently exposes:
  - `cfg_weight`
  - `exaggeration`
- Keep the same approved Swedish teacher reference clip across the sweep.
- Keep one Swedish-only probe text fixed across the sweep.
- Run the combinations in conservative-first order:
  - baseline before deviations
  - lower-guidance lanes before higher-exaggeration lanes
  - `cfg_weight=0` lanes last because they are less conservative for the
    same-language benchmark
- Persist one deterministic evidence bundle per lane under `build/verification/`.
- Mirror the completed Hemma evidence bundles back into the local repo copy.

## Deliverables

- [ ] Committed sweep runner for the Chatterbox tuning grid on Hemma.
- [ ] Deterministic evidence bundles for every documented lane in the sweep.
- [ ] Local copies of the remote Hemma evidence bundles under
  `build/verification/`.
- [ ] Updated Story 23 / Task 87 notes describing:
  - the exact combinations run,
  - the execution order,
  - the recorded runtime truth,
  - the qualitative comparison outcome.

## Acceptance Criteria

- [ ] The sweep uses only repo-supported Chatterbox knobs:
  - `cfg_weight`
  - `exaggeration`
- [ ] The sweep uses one fixed Swedish-only probe text across the same-language
  comparison set.
- [ ] The sweep uses one fixed approved teacher reference clip across the
  same-language comparison set.
- [ ] The sweep runs these value combinations because they are the values
  explicitly documented in the runbook:
  - `exaggeration` in `{0.5, 0.7}`
  - `cfg_weight` in `{0.5, 0.3, 0.0}`
- [ ] The conservative-first execution order is preserved:
  - `(0.5, 0.5)`
  - `(0.5, 0.3)`
  - `(0.7, 0.5)`
  - `(0.7, 0.3)`
  - `(0.5, 0.0)`
  - `(0.7, 0.0)`
- [ ] Each lane writes its own deterministic evidence bundle containing at
  least:
  - `report.json`
  - `report.md`
  - `docker_logs.txt`
  - `artifacts/scenario-a-sv-ref-sv-out.wav`
- [ ] Completed evidence bundles exist both on Hemma and in the local repo copy.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
