---
id: task-340-prune-superseded-sir-convert-dependency-image-tags-after-successful-deps-builds
title: Prune superseded Sir Convert dependency image tags after successful deps builds
type: task
status: completed
priority: high
created: '2026-05-30'
last_updated: '2026-06-04'
related:
  - docs/backlog/epics/epic-03-unified-conversion-service.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/tasks/task-255-extract-sir-convert-service-dependency-images-from-overloaded-pyproject-cache-keys.md
  - docs/runbooks/runbook-hemma-service-ops.md
  - scripts/devops/service-deps-image.sh
labels:
  - docker
  - buildkit
  - devops
  - storage
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add automatic cleanup for superseded Sir Convert dependency-image tags after a
successful dependency-image build. The cleanup must reduce local/Hemma Docker
image pressure without turning the dependency-image lane into a broad image
prune command.

The helper must remain repository-agnostic: callers provide the dependency
image repository and keep tags explicitly, and Sir Convert supplies the active
CPU or ROCm dependency-image repository plus the current dependency-image hash.

## PR Scope

- Add a small explicit-input Docker cleanup helper for old tagged dependency
  images.
- Hook `scripts/devops/service-deps-image.sh` so cleanup runs only when the
  dependency image was actually rebuilt.
- Protect running container image IDs and image IDs behind current keep tags.
- Keep cleanup failure non-fatal after a successful dependency-image build.
- Preserve the existing CPU/ROCm lane split; building CPU deps must not prune
  ROCm deps, and building ROCm deps must not prune CPU deps.

## Deliverables

- [x] Repository-agnostic cleanup helper.
- [x] CPU/ROCm dependency-image build hook.
- [x] Focused tests for stale-tag planning and service-deps integration.
- [x] Docs/runbook/handoff updates.

## Acceptance Criteria

- [x] `service-deps-image.sh cpu build` prunes only superseded
  `sir-convert-a-lot-deps-cpu:*` tags after the current image exists.
- [x] `service-deps-image.sh rocm build` prunes only superseded
  `sir-convert-a-lot-deps-rocm:*` tags after the current image exists.
- [x] Running container image IDs and current `local` plus hash tags are
  protected.
- [x] The cleanup helper defaults to dry-run unless `--execute` is supplied.
- [x] Cleanup is opt-out through an environment variable for exceptional local
  debugging.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation

- Red-first focused test:
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_prune_superseded_deps_images.py -q`
  failed before the helper existed with
  `ModuleNotFoundError: No module named 'scripts.sir_convert_a_lot.devops.prune_superseded_deps_images'`.
- Focused proof:
  `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_prune_superseded_deps_images.py tests/sir_convert_a_lot/test_service_image_build_contract.py -q`
  passed with `9 passed`.
- `bash -n scripts/devops/service-deps-image.sh` passed.
- `pdm run run-local-pdm mypy scripts/sir_convert_a_lot/devops/prune_superseded_deps_images.py tests/sir_convert_a_lot/test_prune_superseded_deps_images.py`
  passed.
- `pdm run format-all` passed.
- `pdm run lint-fix` passed.
- `pdm run typecheck-all` passed.
- `pdm run docs-sync` passed.
- `pdm run docs-validate` passed.
- `pdm run skills-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

Follow-up test-contract closeout on 2026-06-04:

- Updated the compose-wrapper fake Docker harness to model
  `docker buildx build --load`, so dependency-image BuildKit behavior is tested
  instead of rejected by the test double.

- Updated the local compose contract test to reflect the existing CPU-only
  hot-reload debug lane: `--reload`, `--reload-dir /app/scripts`, and the
  `./scripts:/app/scripts:delegated` bind mount.

- Focused compose/local proof passed as part of:

  ```bash
  pdm run pytest-root tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_local_compose_contract.py tests/sir_convert_a_lot/test_examnet_qti_package.py tests/sir_convert_a_lot/test_digiexam_migration_answer_key_completion_api_v2.py
  ```
