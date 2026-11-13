---
type: task
id: TASK-SIRCON-REP-0034
title: Accept equivalent Qwen bind backing and correct private route guidance
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Existing equivalent Qwen build and cache mounts are accepted for device-form and literal-path SOURCE reports, while wrong backing is refused before remount.
  - The installed-home Qwen consumer uses the same backing identity and accepts device-form mounts while refusing wrong backing.
  - The .agents platform codemap names private dev tunnel and prod network routes instead of the retired public host.
  - Focused tests, touched-file lint and typecheck, and docs, skill and handoff validation pass without Hemma commands or a full suite.
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the Qwen bind-root producer's literal `findmnt SOURCE` comparison. An
already-mounted home root is accepted only when the existing sentinel roundtrip
confirms canonical/home backing equivalence. Accept both device-form reports
such as `/dev/sda1[/sir-convert-a-lot/build]` and literal-path reports when the
backing matches. Refuse genuinely wrong backing before any remount; preserve
the ordinary missing-mount installation path and existing report shape.

Expose the existing roundtrip helper and reuse it for producer admission,
status, and the installed-home consumer in `ml/qwen/common/runtime.py`. The
consumer must observe an existing mount and equivalent backing before creating
or preferring the mapped home subpath. Add no second identity rule or protocol.

Replace stale public-route guidance only in the `.agents` platform discovery
overview: dev uses the Mac tunnel `127.0.0.1:28085`, or
`host.docker.internal:28085` for container clients; prod uses
`sir_convert_a_lot_prod:8085` on `hule-network`.

This is Mac-local source work. No Hemma commands, SSH, deployment, restart,
GPU work or live acceptance are authorized during the storage-migration hold.
The two deferred CONV references and shared skill guidance remain other owners'
work. Commit only this unit's paths on the assigned branch; do not push.

## Contract Inputs

- User assignment of 2026-10-15, Units A/B, host hold and proof/commit terms.
- Parent's 2026-10-15 explicit inclusion of the companion consumer defect,
  with the same sentinel identity and focused device-form/wrong-backing tests.
- Accepted ADR-SIRCON-0014 and public-service removal in `be2b7171`.
- Existing roundtrip authority in `qwen_docker_bind_roots_runtime.py`, and
  historical Task 242 status identity correction.
- Closed retained plan in session `01a13ff4-f701-7a9c-85ae-fee3579a6b30`,
  `evidence/planning/TASK-SIRCON-REP-0034/plan.md`; Explorer evidence
  `discovery/explorer/83bf8368-8db6-40e0-8035-5ca48d3db5fa/0001-existing-bind-backing-identity.md`.

## Core Vertical And Performance

Producer repair, status and installed-home resolution share the existing
canonical/home sentinel check. Fresh execution units own producer/test changes,
consumer/test changes, and the named codemap passage; the lead integrates them.
Retain build-subpath mapping and cache behavior. No benchmark is needed for
this bounded existing check. Local filesystem fixtures and mocked host metadata
establish source behavior only; host proof remains held.

## Validation

- Focused operations target:
  `tests/sir_convert_a_lot/operations/test_qwen_docker_bind_roots.py`.
- Focused isolated Qwen target: `qwen/tests/training/test_runtime.py`.
- Adversarial cases: equivalent device-form SOURCE for build/cache,
  device-form wrong filesystem or wrong FSROOT, literal-path equivalent and
  wrong backing, missing mount, and mapped-home preference/refusal.
- Touched-file Ruff lint/format check and focused typecheck through the owning
  root/Qwen environments. Inspect the named `operations` check plan; do not run
  a full suite or repository-wide code check.
- `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check`.
- Retain command evidence in the assigned session. Parent routes independent
  code and agent-prose review before closeout or integration.

Local source proof on 2026-10-15 passed 14 producer tests and 13 isolated Qwen
consumer tests. Touched-file Ruff lint/format and both owning environments'
focused typechecks passed. Pre-fix regressions exposed rejection of equivalent
device-form backing and incorrect admission from a literal SOURCE alone.
The fixtures exercise real local sentinel visibility with synthetic mount
metadata; they establish no live Hemma mount or service acceptance. Recorded
commands are in the assigned session's `operational-output/commands/` lane.

## Stop Conditions

- Preserve the Hemma hold until an explicit parent-relayed release.
- Return any required identity-protocol change, new host operation or ownership
  conflict to the parent; preserve peers' work and deferred CONV references.
- Do not claim live filesystem, systemd or Docker acceptance from local tests.
- Independent reviewers own approval; leave task unfinished pending review.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D01 | Closed: reuse existing sentinel backing identity for mounted producer roots; equivalent SOURCE forms pass and genuinely wrong backing fails closed. |
| D02 | Closed: the named .agents codemap documents the private Mac dev tunnel, container tunnel host, and hule-network prod service (ADR-SIRCON-0014). |
| D03 | Closed: Mac-local work only under the 2026-10-15 Hemma hold; no deferred CONV reference edits. |
| D04 | Closed: focused source proof and docs gates, owned-path branch commit without attribution or push, and parent-routed independent review. |
| D05 | Closed: include the companion installed-home consumer using the exact same sentinel identity, with device-form and wrong-backing tests (parent authorization). |
