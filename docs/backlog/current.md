---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-04-19'
related:
  - docs/backlog/programmes/programme-01-sir-convert-a-lot-platform-foundation.md
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-239-split-sir-convert-a-lot-service-dependency-and-app-layers-to-avoid-full-rebuilds-on-code-only-changes.md
  - docs/backlog/tasks/task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes.md
  - docs/backlog/tasks/task-254-harden-sir-convert-production-public-edge-recovery.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - session-log
  - active-work
  - devops
  - hemma
---

## Context

The active implementation context for this session is the Epic 03 / Story 05
DevOps lane for the Hemma-hosted Sir Convert-a-Lot service.

Current governing spine:

- Programme 01: Sir Convert-a-Lot platform foundation.
- Epic 03: Unified conversion service.
- Story 05: Dockerized service hardening with robust persistence.
- Task 254: Production public-edge recovery and detached deploy verification.
- Task 255: Service dependency image extraction from overloaded
  `pyproject.toml` cache keys.

Task 254 remains the immediate production recovery authority. It owns the
detached Hemma deploy/public-edge proof, reserved default-host behavior, and the
canonical `hemma-deploy-and-verify` report evidence.

Task 255 is the follow-up build architecture authority. It owns the dependency
image split, narrow dependency input artifacts, BuildKit pip cache mounts, and
the proof that PDM script-only changes no longer invalidate ROCm torch,
EasyOCR preload, or other heavy dependency work.

Task 239 is retained as the earlier completed partial layering slice. It
narrowed app-source/context invalidation, but Task 255 owns the unresolved
`pyproject.toml` dependency-cache boundary.

The Qwen Task 101 lane is not the active implementation lane for this session.
Its durable status remains in:

- `docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`
- Epic 08 and Story 31/32 backlog docs.
- The Qwen runbook and RULE-095/RULE-096.

The Task 242 Hemma Docker bind-root contract remains operational background
for Qwen runtimes only. Use its `status` and `probe` surfaces before future
Qwen Docker work, but do not let Qwen governance override the current Story 05
DevOps task authority.

## Worklog

- 2026-03-18:
  - Qwen Story 31/32 mechanism work and Task 242 bind-root governance were the
    prior active lane. The detailed task-by-task ledger was compressed into the
    Qwen reference, story docs, and runbooks.
- 2026-04-19:
  - Task 254 became the active production recovery slice after public-edge drift
    on `convert.hule.education`.
  - Production/dev compose ownership was split: `prod-*` uses `compose.yaml`
    and `sir_convert_a_lot_prod`; `dev-*` uses `compose.local.yaml` and
    `sir_convert_a_lot_dev`.
  - Long-running Hemma production deploys and shared public-edge remediation
    were reaffirmed as detached-command workflows.
  - Review feedback identified the remaining durable proof gap: the canonical
    deploy verifier must emit public HTTPS and default-host artifacts, not rely
    on manual curl evidence only.
  - A build-time RCA found that full `pyproject.toml` still invalidates the
    heavy dependency-builder chain, including ROCm torch and EasyOCR preload.
  - Story 05 was promoted as the active DevOps story under Epic 03, and Task
    255 was created as the explicit dependency-image/cache-key follow-up.

## Next Actions

- Finish Task 254 first:
  - make `hemma-deploy-and-verify` deploy-detached-aware;
  - monitor detached Hemma deploy logs as first-class evidence;
  - emit durable public HTTPS, TLS, nginx-proxy, and unknown-host/default-host
    artifacts in the canonical report;
  - run the live Hemma deploy/public curl gate only through detached deploy
    surfaces.
- Then execute Task 255:
  - define the narrow dependency input artifact/hash;
  - add production ROCm dependency image build surfaces;
  - add BuildKit pip cache mounts;
  - update compose/PDM/runbook contracts;
  - prove one dependency rebuild and one cache-hot app/ops-only rebuild on
    Hemma with detached monitoring where work can outlive the local session.
- Keep Task 239 closed as historical partial layering context. Do not reopen it
  for the dependency-image work unless Task 255 explicitly supersedes or amends
  a documented Task 239 acceptance boundary.
- Preserve the Qwen lane without active edits unless the user explicitly
  returns to Epic 08 / Story 31 work.
