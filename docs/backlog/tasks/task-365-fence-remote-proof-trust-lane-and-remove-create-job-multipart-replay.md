---
id: task-365-fence-remote-proof-trust-lane-and-remove-create-job-multipart-replay
title: Fence remote-proof trust lane and remove create-job multipart replay
type: task
status: in_progress
priority: high
created: '2026-06-14'
last_updated: '2026-06-14'
related: []
labels:
  - auth
  - gateway
  - remote-proof
  - stt
  - admission
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the create-job multipart replay suspected in the observed 64-second
audio admission delay, and add a fenced Hemma remote-proof lane that lets local
Skriptoteket/HuleEdu browser proof exercise remote hosted STT compute without
bleeding local-auth trust into production Sir Convert.

## PR Scope

- Replace the second create-job request form parse with a typed derivation of
  submitted multipart part names from the already-bound FastAPI parameters.
- Preserve DigiExam companion validation and audio-route companion rejection.
- Add red-first tests proving `POST /v2/convert/jobs` does not need a second
  multipart form parse after FastAPI has bound the request.
- Add a separate `remote-proof` Hemma compose/runtime lane with distinct service
  names, data volume, service profile, port, API key surface, and local-auth
  trust profile inputs.
- Keep production compose on `hemma-production` trust material only; production
  must not reference remote-proof trust variables or data volumes.
- Keep remote-proof off public ingress by default. The lane is for sanctioned
  operator/local proof through a controlled tunnel or internal Hemma surface.
- Use Hemma-hosted STT/model workers for proof; do not require laptop-local
  Whisper, Pyannote, or other heavy model hosting.
- Do not change `proxy_read_timeout`, body-size, trust keys, production public
  ingress, or other environment knobs as part of this task.

## Deliverables

- [ ] Red-first admission regression test for the create-job multipart parser
  replay.
- [ ] Production create-job route admits jobs from bound multipart parameters
  without calling `request.form()` again.
- [ ] Remote-proof compose and wrapper surfaces are governed, deterministic,
  and distinct from production.
- [ ] Compose contract tests prove production and remote-proof trust/data
  surfaces cannot bleed into each other.
- [ ] Local downstream proof uses the fenced remote-proof lane before any
  production proof is claimed.
- [ ] Native Hemma production STT proof runs after local proof passes.

## Acceptance Criteria

- [ ] Current create-job admission no longer performs a second multipart form
  parse after `UploadFile` and `Form` parameters are bound.
- [ ] The admission regression test fails on the pre-fix route and passes after
  the route derives form-part names without replaying request parsing.
- [ ] Remote-proof uses a non-production service profile and non-production
  trusted HuleEdu `local-auth-integration` public profile only.
- [ ] Production compose and production workers keep `hemma-production` trust
  inputs only and do not reference remote-proof variables, ports, or data
  volumes.
- [ ] Remote-proof has no public `VIRTUAL_HOST`, `LETSENCRYPT_HOST`, or public
  reserved-edge service.
- [ ] Local STT E2E proof succeeds against the remote-proof method with remote
  hosted model execution.
- [ ] Production STT E2E proof succeeds natively on Hemma after the local proof.
- [ ] No timeout, ingress, body-size, or trust/key setting is changed without a
  separate explicit approval.

## Test Requirements

- [x] Focused red command for admission parser replay.
- [x] Focused green command for admission parser replay.
- [x] Focused compose contract proof for remote-proof/prod separation.
- [ ] Relevant `pdm run format-all`, `pdm run lint-fix`,
  `pdm run typecheck-all`, and docs gates for touched code/docs.
- [ ] Live local proof artifact path recorded.
- [ ] Native Hemma production proof artifact path recorded.

## Implementation Evidence

- Added `scripts/sir_convert_a_lot/interfaces/http_create_job_form_parts_v2.py`
  and removed the second `await request.form()` call from
  `interfaces/http_routes_jobs_v2.py`; create-job admission now uses the
  already-bound multipart request state to preserve companion part validation
  without replaying the multipart parser after upload bytes are read.
- Added `scripts/sir_convert_a_lot/service_remote_proof.py` so `/readyz` can
  report the fenced `remote-proof` service profile separately from production.
- Added `compose.remote-proof.yaml` with distinct API/worker containers,
  `sir-convert-a-lot-remote-proof-data`, remote-proof API-key env surface,
  local-auth trust-profile/public-key env surfaces, no public ingress labels,
  and existing Hemma STT sidecar consumption for remote hosted model execution.
- Added `scripts/devops/remote-proof-compose.sh` and `remote-proof-*` PDM
  scripts. The wrapper sources only
  `/home/paunchygent/.data/sir-convert-a-lot/remote-proof/remote-proof.env`
  by default, not production `.env`.
- Added `scripts/devops/docker-command.sh` as the shared Docker command
  resolver for compose and dependency-image helpers. Remote-proof sets the
  generic `SIR_CONVERT_A_LOT_DOCKER_USE_SUDO=1`, so compose operations and
  dependency image preparation use the same Hemma Docker privilege path without
  coupling the helpers to each other.
- Updated the remote-proof wrapper to derive and preflight the canonical
  local-auth-integration public-key bind path before compose/dependency-image
  work starts. The default is under the remote-proof trust directory, not a
  caller's ad hoc shell session.
- Routed superseded dependency-image cleanup through the same resolved Docker
  command as dependency-image inspect/build/tag operations, so remote-proof does
  not fall back to plain Docker in child cleanup helpers.
- Added sudo-safe compose env-file handoff: remote-proof requires its sanctioned
  env file, and the shared compose runner copies it into a short-lived temp
  snapshot plus computed compose interpolation values before invoking Compose.

## Red-First Evidence

- Admission replay red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_admission_multipart_replay_v2.py -q`
  failed with `AssertionError: create-job admission must not replay multipart form parsing` at `interfaces/http_routes_jobs_v2.py:254`.
- Remote-proof compose red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py -q`
  failed because `compose.remote-proof.yaml` and
  `scripts/devops/remote-proof-compose.sh` did not exist.
- Remote-proof env-file durability red command:
  `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py::test_remote_proof_wrapper_and_pdm_scripts_are_first_class -q`
  failed because the wrapper did not source
  `SIR_CONVERT_A_LOT_REMOTE_PROOF_ENV_FILE`.
- First Hemma `pdm run remote-proof-start` attempts failed before container
  mutation with Docker socket permission denied. The first patch only routed
  compose through sudo; user feedback correctly rejected that as leaky because
  dependency image preparation still carried Docker access policy separately.
  The follow-up tests now require a shared Docker command resolver rather than
  helper-specific sudo handling.
- The next Hemma `pdm run remote-proof-start` attempt built the ROCm dependency
  image successfully, then failed during compose interpolation because
  `HULEEDU_INTERNAL_IDENTITY_REMOTE_PROOF_PUBLIC_KEY_HOST_PATH` was unset. The
  red wrapper contract failed because `remote-proof-compose.sh` did not own a
  canonical remote-proof trust directory/public-key default.
- The same Hemma attempt also showed superseded dependency-image cleanup still
  used plain Docker internally. Red tests proved the Python cleanup helper had
  no caller-selected Docker command and the remote-proof integration path did not
  route cleanup through `sudo -n docker`.
- After the trust-path default was added, Hemma compose interpolation still lost
  the exported path at the `sudo -n docker compose` boundary. Red tests proved
  remote-proof did not pass a compose env file and compose-actions had no
  env-file handoff.
- Passing the hidden remote-proof env file path directly then failed on Hemma
  with permission denied from Docker Compose. The durable fix is a temporary
  compose env snapshot that the wrapper removes after Compose exits.

## Focused Green Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_admission_multipart_replay_v2.py -q`
  passed with `1 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py::test_digiexam_migration_rejects_generic_resources_companion -q`
  passed with `1 passed`, proving DigiExam companion rejection still uses the
  submitted part names after the parser replay removal.
- `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py -q`
  passed with `4 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_admission_multipart_replay_v2.py tests/sir_convert_a_lot/test_remote_proof_compose_contract.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py::test_digiexam_migration_rejects_generic_resources_companion -q`
  passed with `6 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py::test_remote_proof_wrapper_and_pdm_scripts_are_first_class -q`
  passed after replacing helper-specific sudo handling with the shared Docker
  resolver contract.
- `pdm run pytest-root tests/sir_convert_a_lot/test_dev_compose_wrapper.py::test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker -q`
  passed, proving the remote-proof wrapper routes compose and dependency-image
  Docker calls through the same shared sudo-Docker policy.
- `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py::test_remote_proof_wrapper_and_pdm_scripts_are_first_class tests/sir_convert_a_lot/test_dev_compose_wrapper.py::test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker tests/sir_convert_a_lot/test_dev_compose_wrapper.py::test_remote_proof_wrapper_fails_before_docker_when_trust_key_is_missing -q`
  passed with `3 passed`, proving the wrapper derives the public-key path from
  a canonical trust directory and fails before Docker when the trust key is
  absent.
- `pdm run pytest-root tests/sir_convert_a_lot/test_prune_superseded_deps_images.py::test_docker_output_uses_caller_selected_docker_command tests/sir_convert_a_lot/test_dev_compose_wrapper.py::test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker -q`
  passed with `2 passed`, proving the prune child helper receives and uses the
  same Docker command policy as the dependency-image shell helper.
- `pdm run pytest-root tests/sir_convert_a_lot/test_remote_proof_compose_contract.py::test_remote_proof_wrapper_and_pdm_scripts_are_first_class tests/sir_convert_a_lot/test_dev_compose_wrapper.py::test_remote_proof_wrapper_routes_compose_and_deps_through_shared_sudo_docker -q`
  passed with `2 passed`, proving remote-proof passes explicit env files to
  Docker Compose instead of relying on sudo-preserved shell exports, and uses a
  temporary snapshot rather than the hidden source env path.
- `pdm run pytest-root tests/sir_convert_a_lot/test_dev_compose_wrapper.py -q`
  passed with `11 passed`, proving the Docker policy resolver did not change
  the local/dev compose wrapper behavior.
- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_admission_multipart_replay_v2.py tests/sir_convert_a_lot/test_remote_proof_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_prune_superseded_deps_images.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py::test_digiexam_migration_rejects_generic_resources_companion -q`
  passed with `23 passed`.
- Local compose syntax expansion for `compose.remote-proof.yaml` passed with
  dummy non-secret values via `docker compose -f compose.remote-proof.yaml config`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
