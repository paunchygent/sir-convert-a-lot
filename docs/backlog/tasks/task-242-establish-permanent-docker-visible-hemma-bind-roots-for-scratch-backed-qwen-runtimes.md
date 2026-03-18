---
id: task-242-establish-permanent-docker-visible-hemma-bind-roots-for-scratch-backed-qwen-runtimes
title: Establish permanent Docker-visible Hemma bind roots for scratch-backed Qwen runtimes
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/epics/epic-08-qwen3-tts-swedish-language-expansion-fine-tuning-on-hemma-and-colab.md
  - docs/backlog/stories/story-32-consolidate-qwen-experiment-governance-and-surface-taxonomy.md
  - docs/backlog/tasks/task-151-repair-task101-container-output-root-bind-fallback-for-hemma.md
  - docs/backlog/tasks/task-240-split-the-post-t237-downstream-convergence-seam-beneath-layer15-output-before-any-promotion-discussion.md
  - docs/backlog/tasks/task-241-split-the-post-t240-layer15-output-seam-into-residual-output-formation-sub-boundaries-before-any-new-stabilizer-family.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - hemma
  - docker
  - bind-mount
  - infrastructure
  - devops
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the recurring ad hoc home-backed bind fallback for scratch-backed Qwen
Docker workloads on Hemma with one explicit, durable host contract so active
experiments stop rediscovering the same snap-Docker `/srv/scratch` bind-mount
failure on every run.

## PR Scope

- Treat the current runtime truth as explicit evidence:
  - the Hemma reboot restored Docker itself
  - fresh Docker bind mounts from `/srv/scratch/...` still fail with
    `mkdir /srv/scratch: read-only file system`
  - Qwen mechanism runs remain truthful only because the runtime falls back to
    the existing home-backed bind roots under
    `/home/paunchygent/.data/sir-convert-a-lot/`
- Keep `/srv/scratch` as the canonical SSD storage tier for active Qwen build
  and cache state.
- Make the home-backed Docker-visible roots a first-class Hemma contract
  rather than an opportunistic fallback.
- Add one committed operator surface, for example `qwen-docker-bind-roots`,
  with these subcommands:
  - `install`
  - `status`
  - `probe`
- Install one persistent system-level service on Hemma that keeps these
  scratch-backed roots mounted onto their Docker-visible home mirrors:
  - `/srv/scratch/sir-convert-a-lot/build`
    -> `/home/paunchygent/.data/sir-convert-a-lot/build`
  - `/srv/scratch/sir-convert-a-lot/cache`
    -> `/home/paunchygent/.data/sir-convert-a-lot/cache`
- Update the shared Qwen runtime so it prefers the installed persistent
  home-backed bind roots when they are present, rather than probing the
  failing `/srv/scratch` path first every run.
- Keep compatibility with the existing bind-root helper contract:
  dynamic bind fallback may remain as a compatibility escape hatch, but the
  normal Hemma path after this task must be the persistent installed roots.
- Add a fail-closed verification surface so operators can confirm:
  - the service is installed and enabled
  - the home roots are mounted from the expected `/srv/scratch` sources
  - Docker can bind-mount the effective home roots
- Update the Hemma/Qwen runbooks, the Qwen skill, and the session handoff so
  future operators treat this as the standard runtime contract, not as a
  lucky fallback.

## Non-Goals

- Do not change Story 31 mechanism causality or reinterpret any experiment
  results.
- Do not move canonical active build/cache storage off `/srv/scratch`.
- Do not redesign the broader Hemma Docker snap storage root from Task 113.
- Do not reopen recovery work; `T217` remains blocked.

## Why This Slice Exists

`T240` produced truthful mechanism evidence only because the shared runtime
fell back to already-existing home-backed bind roots after Docker again
rejected fresh `/srv/scratch/...` bind mounts. That has become a recurring
operational tax:

- experiments still work, but only by rediscovering the same host quirk
- the fallback obscures the real runtime contract
- repeated probing and ad hoc repair increase operator noise
- the bind-root behavior now belongs in Hemma infrastructure, not in the
  interpretation of Story 31 mechanism runs

## Required Implementation Shape

1. Add one committed Hemma command surface for persistent Qwen Docker bind roots.
   - Prefer `qwen-docker-bind-roots install|status|probe`.
   - Keep the implementation repo-owned and callable via
     `pdm run run-hemma -- pdm run qwen-docker-bind-roots ...`.
1. Install one persistent system-level service that re-establishes the
   scratch-backed home bind roots across reboot.
   - The service must be committed/rendered from repo code, not hand-edited.
   - The service must be installable/refreshable idempotently.
1. Prefer the installed persistent home bind roots inside the shared Qwen
   runtime when they are present and correctly mounted.
   - The runtime must keep returning the canonical root as metadata truth and
     only swap the effective host mount source.
   - The runtime must still fail clearly when no Docker-visible bind source can
     be established.
1. Add focused regression coverage for:
   - persistent build/cache root mapping
   - runtime preference for the installed persistent home roots
   - service render/install/status/probe behavior
1. Update operator docs so the normal preflight becomes:
   - `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
   - `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`

## Deliverables

- [ ] One committed `qwen-docker-bind-roots` command surface exists with
  `install`, `status`, and `probe`.
- [ ] One persistent Hemma service contract keeps the scratch-backed build and
  cache roots mounted onto the Docker-visible home paths across reboot.
- [ ] The shared Qwen runtime prefers the installed persistent home bind roots
  when they are available.
- [ ] Operator docs describe the persistent bind-root contract and verification
  flow.

## Acceptance Criteria

- [ ] Fresh Hemma experiment runs no longer depend on rediscovering the
  `/srv/scratch` bind failure to reach the home-backed mount path.
- [ ] `qwen-docker-bind-roots status` reports whether the installed service is
  enabled/active and whether the expected home roots are mounted from the
  canonical `/srv/scratch` sources.
- [ ] `qwen-docker-bind-roots probe` proves Docker can bind-mount the effective
  home-backed build/cache roots.
- [ ] The shared runtime prefers the persistent home-root mapping for
  scratch-backed Qwen build/cache paths when the service is installed.
- [ ] Story 31 remains mechanism-only; this task does not promote or reinterpret
  any training recipe candidate.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_runtime.py tests/sir_convert_a_lot/test_task242_hemma_qwen_docker_bind_roots.py -q`
- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run run-hemma -- pdm run qwen-docker-bind-roots install`
- [ ] `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
- [ ] `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
