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
- Updated shared compose actions with an explicit `SIR_CONVERT_A_LOT_COMPOSE_USE_SUDO`
  mode and enabled it only for remote-proof, matching Hemma's Docker socket
  privilege boundary without hand-running `sudo docker compose`.

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
- First Hemma `pdm run remote-proof-start` attempt failed before container
  mutation with Docker socket permission denied. The follow-up red test failed
  because the remote-proof wrapper did not declare the sanctioned sudo compose
  path.

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
  passed after adding remote-proof sudo compose mode.
- `pdm run pytest-root tests/sir_convert_a_lot/test_dev_compose_wrapper.py -q`
  passed with `9 passed`, proving the sudo mode did not change the local/dev
  compose wrapper behavior.
- `pdm run pytest-root tests/sir_convert_a_lot/test_create_job_admission_multipart_replay_v2.py tests/sir_convert_a_lot/test_remote_proof_compose_contract.py tests/sir_convert_a_lot/test_dev_compose_wrapper.py tests/sir_convert_a_lot/test_digiexam_migration_access_control_api_v2.py::test_digiexam_migration_rejects_generic_resources_companion -q`
  passed with `15 passed`.
- Local compose syntax expansion for `compose.remote-proof.yaml` passed with
  dummy non-secret values via `docker compose -f compose.remote-proof.yaml config`.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
