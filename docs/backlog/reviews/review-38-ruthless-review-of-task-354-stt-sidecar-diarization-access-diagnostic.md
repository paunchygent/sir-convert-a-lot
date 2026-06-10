---
id: review-38-ruthless-review-of-task-354-stt-sidecar-diarization-access-diagnostic
title: Ruthless review of Task 354 STT sidecar diarization access diagnostic
type: review
status: completed
priority: high
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md
  - docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md
  - docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md
  - docs/backlog/stories/story-53-audio-transcript-bundle-route-execution-and-json-artifact-persistence.md
  - docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md
  - docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md
labels:
  - review
  - approved
  - task-354
  - stt
  - diarization
  - hugging-face
  - pyannote
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: fixed ruthless implementation review for the Task 354
  diarization-access diagnostic slice.
- Scope under review:
  - new pyannote Hugging Face gated-access diagnostic domain module;
  - new diagnostic command runner and PDM script registration;
  - focused tests for bounded report projection and command registration;
  - Task 354 documentation for the diagnostic runner surface.
- Files reviewed:
  - `scripts/sir_convert_a_lot/devops/audio_transcription_sidecar_diarization_access.py`
  - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py`
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py`
  - `pyproject.toml`
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  - `docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
- Governing authority:
  - `AGENTS.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  - `docs/backlog/tasks/task-352-build-live-hemma-stt-sidecar-benchmark-profile-proof.md`
  - `docs/backlog/tasks/task-353-resolve-hemma-stt-sidecar-live-proof-backend-blockers.md`
  - `docs/decisions/0013-speech-to-text-sidecar-and-audio-ingestion-governance.md`
- Public or operational surfaces affected:
  - `pdm run diagnose:stt-sidecar-diarization-access`
  - generated diagnostic JSON
    `build/verification/stt-sidecar-diarization-access/diarization-access.json`
  - Task 354 retained planning evidence
- Explicit non-scope:
  - This review does not approve Task 352 live proof completion.
  - This review does not unblock Story 53.
  - This review does not approve `audio -> transcript_bundle` route
    registration, OpenAPI/Gateway publication, transcript persistence,
    formatter output, or replacement diarization implementation.
- Compatibility posture:
  - additive operator diagnostic command;
  - no retired command, route, payload, token alias, or compatibility shim is
    accepted by this review;
  - missing pyannote access must remain a typed blocked state, never a false
    ready state.

## Evidence Reviewed

- Current uncommitted diff in `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot`.
- Context7 `/huggingface/huggingface_hub` documentation:
  - `HF_TOKEN` is the standard environment variable for authenticated Hub
    access;
  - `whoami(token=...)` is a supported authentication probe;
  - `hf_hub_download(...)` is the supported single-file Hub download/cache
    surface.
- Context7 `/pyannote/pyannote-audio` documentation:
  - `pyannote/speaker-diarization-community-1` is loaded through
    `Pipeline.from_pretrained(..., token=...)`;
  - exact `num_speakers`, `min_speakers`/`max_speakers`, GPU placement, and
    exclusive speaker diarization are current pyannote surfaces.
- Local import probe:
  - `pdm run python -c "import huggingface_hub; print(hasattr(huggingface_hub, 'whoami'))"`
    returned `True`.
- Focused tests:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
    passed `5 passed`.
- Command import/help smoke:
  - `pdm run python -m scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_diarization_access --help`
    exited `0`.
- Static/type/docs gates:
  - `pdm run typecheck-all` passed with `Success: no issues found in 837 source files`.
  - `pdm run docs-validate` passed before this retained review artifact was
    created with `Validated 461 backlog files` and `Validated docs=536 rules=11`.
  - After this retained review artifact was created, `pdm run docs-validate`
    validated `462 backlog files` and then failed only because
    `docs/backlog/INDEX.md` is stale until `pdm run docs-sync` refreshes the
    generated index.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.
- Not run:
  - `pdm run docs-sync`, `pdm run format-all`, and `pdm run lint-fix` were not
    run by this reviewer because the review instruction only allowed writing a
    retained review artifact.

## Findings

1. [ ] `high` - The public diagnostic runner's exit-code/write contract is not
   directly tested.

   File references:

   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:57`
   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:62`
   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:67`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:99`

   Task 354 documents `pdm run diagnose:stt-sidecar-diarization-access` as an
   operator command that writes `diarization-access.json` and returns exit code
   `0` only for ready access, otherwise `2`. The current tests prove the
   report builder and a string-level pyproject registration, but they never
   call the runner boundary that parses args, merges the operator environment,
   writes the report, prints the path, and turns report status into the process
   decision. A regression that always returned `0`, failed to write the report,
   ignored `--output-root`, or bypassed the env-file path could still pass the
   focused suite while misleading operators into rerunning Task 352 live proof.

   Required fix:
   Add red-first tests for the runner boundary. A sufficient shape is to invoke
   `main([...], environment=...)` in
   `run_audio_transcription_sidecar_diarization_access.py` with a fake
   Hugging Face client or client factory, then assert:

   - ready access returns `0`, writes `diarization-access.json`, and records
     `status=ready`;
   - missing token returns `2`, writes the report, records
     `failure_code=hf_token_missing`, and names
     `configure_hf_token_for_stt_sidecar_operator`;
   - gated artifact access returns `2`, writes the report, records
     `failure_code=gated_model_access_denied`, and does not persist token
     values, private cache paths, or raw model identifiers.

   Proof command:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`

1. [ ] `medium` - The new test module lacks the repo-required domain-purpose
   module docstring.

   File reference:

   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:1`

   `AGENTS.md` and `.codex/rules/090-documentation-standards.md` require a
   Google-style module docstring at the top of new or materially changed Python
   modules describing domain purpose and relationships. This test file starts
   with `from __future__ import annotations`, so the new test module violates
   the repo's discoverability and tree-parsing rule. The missing docstring also
   cuts against the user's explicit instruction that helper and test files must
   be named and documented according to purpose.

   Required fix:
   Add a top-level Google-style module docstring that describes the diagnostic
   behavior under test and its relationship to Task 354/STT sidecar proof. Keep
   it domain-purpose focused; do not add meta commentary about refactors,
   stories, or review mechanics.

   Proof command:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`

1. [ ] `low` - The slice carries unrelated whitespace churn in an already
   accepted retained review.

   File reference:

   - `docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md:23`

   The only change to Review 37 is a blank line after frontmatter. Review 37 is
   already the accepted post-deploy FasterWhisper/codec evidence review, and
   this Task 354 diagnostic slice does not need to rewrite it. Keeping
   unrelated retained-review churn makes the commit harder to audit and can
   blur which artifact records the Task 354 decision.

   Required fix:
   Drop the whitespace-only Review 37 change before commit unless a substantive
   Task 354 cross-link is intentionally added and described.

   Proof command:
   `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
   should be empty or contain a substantive documented update.

## Decision

`changes_requested`

The bounded diagnostic direction is sound: it uses the governed `HF_TOKEN`
name, keeps raw token values/cache paths/model identifiers out of retained
payloads, classifies gated access as blocked, and does not pretend Task 352 live
proof is complete. Approval is blocked until the operator command boundary is
tested at the same surface operators will trust.

## Response

Task 354's diagnostic slice is not approved yet. Implement the runner-boundary
tests and the missing module docstring, remove unrelated Review 37 churn, rerun
the focused tests and non-mutating quality gates, then request another fixed
ruthless review pass.

## Follow-up Actions

1. Add runner-boundary tests for `diagnose:stt-sidecar-diarization-access`
   ready, missing-token, and gated-access outcomes.
1. Add the missing top-level domain-purpose docstring to the diagnostic test
   module.
1. Remove the unrelated Review 37 whitespace-only diff or replace it with a
   substantive governed cross-link if needed.
1. Re-run:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`,
   `pdm run typecheck-all`, `pdm run docs-sync`, `pdm run docs-validate`,
   `pdm run skills-validate`, `pdm run handoff-validate`, and
   `git diff --check`.

## Second Review Pass

Date: 2026-06-10

Decision: `changes_requested`

Second-pass scope remained bounded to the same Task 354 diagnostic runner
slice. This pass reviewed only the current uncommitted remediation for Review
38 and does not approve Task 352 live proof completion, does not unblock Story
53, and does not approve route registration, Gateway publication, transcript
persistence, formatter output, or replacement diarization implementation.

### Second-Pass Evidence Reviewed

- Current implementation:
  - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:43`
    now accepts a typed `HubModelAccessClient` test injection seam while normal
    CLI execution still constructs `HuggingFaceHubModelAccessClient`.
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:1`
    now has the required domain-purpose module docstring.
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:141`
    adds a public runner ready-path test that verifies exit code `0`, stdout
    path, JSON write, `status=ready`, and content-safety metadata.
  - `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
    is empty after the docs-sync blank-line churn was removed.
  - `docs/backlog/INDEX.md` now indexes Review 38.
- Current third-party docs checked through Context7:
  - `/huggingface/huggingface_hub` still documents authenticated Hub access and
    single-file downloads through the supported Hub APIs used by this
    diagnostic.
  - `/pyannote/pyannote-audio` still documents Community-1 diarization with a
    Hugging Face token, GPU placement, exact and min/max speaker constraints,
    and exclusive diarization output.
- Validation run by this reviewer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
    passed `6 passed`.
  - `pdm run typecheck-all` passed with
    `Success: no issues found in 837 source files`.
  - `pdm run docs-validate` passed with `Validated 462 backlog files` and
    `Validated docs=537 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.

### Second-Pass Finding Status

1. [ ] `high` - The public diagnostic runner's blocked exit paths are still
   not directly tested.

   File references:

   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:59`
   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:64`
   - `scripts/sir_convert_a_lot/devops/run_audio_transcription_sidecar_diarization_access.py:69`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:81`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:100`
   - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:141`

   The new ready-path runner test is good as far as it goes, but the original
   high finding was about the operator command's full exit-code/write contract:
   ready must return `0`, while missing-token and gated-access states must
   return `2` after writing a bounded report. The current suite still tests
   missing-token and gated-access behavior only at the report-builder level.
   A regression that made `main(...)` always return `0` for blocked reports, or
   stopped writing blocked reports while keeping the builder correct, would
   still pass the focused tests. That is the current product-risk path because
   Task 354 exists precisely to prove that pyannote access remains fail-closed
   until gated access is available.

   Required fix:
   Add public runner-boundary tests for blocked outcomes, for example:

   - `test_diarization_access_command_writes_report_and_returns_missing_token_exit_code`
     calling `run_diarization_access_diagnostic([...], environment={}, client=...)`
     and asserting exit code `2`, stdout path, JSON write,
     `failure_code=hf_token_missing`, and
     `operator_action=configure_hf_token_for_stt_sidecar_operator`;
   - `test_diarization_access_command_writes_report_and_returns_gated_access_exit_code`
     calling the runner with `GatedHubAccessClient` and asserting exit code `2`,
     stdout path, JSON write, `failure_code=gated_model_access_denied`,
     `operator_action=accept_or_request_pyannote_gated_model_access_for_hf_token_account`,
     and no persisted token values, private cache paths, or raw model
     identifiers.

   Proof command:
   `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`

1. [x] `medium` - The missing test-module domain-purpose docstring is resolved.

   The new docstring at
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:1`
   describes the diagnostic behavior and content-safety relationship without
   meta commentary.

1. [x] `low` - The unrelated Review 37 whitespace churn is resolved.

   `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
   is empty in the current worktree.

1. [ ] `low` - Task 354's local green evidence is stale after the remediation.

   File reference:

   - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md:153`

   Task 354 still records the focused suite as `5 passed`, while the current
   remediated suite reports `6 passed`. The task should also record the
   second-pass red evidence for the new runner-boundary test if that evidence is
   intended to remain the durable implementation record.

   Required fix:
   Update the Task 354 evidence block to reflect the current focused test count
   and the new red/green runner-boundary proof.

   Proof command:
   `pdm run docs-validate`

### Second-Pass Response

The remediation is close, but the diagnostic runner is not accepted yet. Add
the two blocked-path runner tests, update Task 354's stale test evidence, rerun
the focused tests and docs gates, then request the next fixed review pass.

## Third Review Pass

Date: 2026-06-10

Decision: `changes_requested`

Third-pass scope remained bounded to the same Task 354 diagnostic runner slice.
This pass reviewed only the current uncommitted remediation after the second
pass. It does not approve Task 352 live proof completion, does not unblock Story
53, and does not approve route registration, Gateway publication, transcript
persistence, formatter output, or replacement diarization implementation.

### Third-Pass Evidence Reviewed

- Current implementation:
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:160`
    adds the public runner missing-token blocked-path test. It calls the runner
    boundary, verifies exit code `2`, stdout path, JSON write,
    `failure_code=hf_token_missing`, and
    `operator_action=configure_hf_token_for_stt_sidecar_operator`.
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:181`
    adds the public runner gated-access blocked-path test. It calls the runner
    boundary, verifies exit code `2`, stdout path, JSON write,
    `failure_code=gated_model_access_denied`,
    `operator_action=accept_or_request_pyannote_gated_model_access_for_hf_token_account`,
    and retained-payload redaction for token values and raw model identifiers.
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md:153`
    now records the focused suite as `8 passed`.
  - `docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md:23`
    still has a whitespace-only diff in the current worktree.
- Current third-party docs checked through Context7:
  - `/huggingface/huggingface_hub` still documents `HF_TOKEN` for Hub
    authentication and token-aware Hub access.
  - `/pyannote/pyannote-audio` still documents Community-1 diarization with a
    Hugging Face token, GPU placement, exact and min/max speaker constraints,
    and exclusive diarization output.
- Validation run by this reviewer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
    passed `8 passed`.
  - `pdm run typecheck-all` passed with
    `Success: no issues found in 837 source files`.
  - `pdm run docs-validate` passed with `Validated 462 backlog files` and
    `Validated docs=537 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.

### Third-Pass Finding Status

1. [x] `high` - The public diagnostic runner's blocked exit paths are now
   directly tested.

   The new tests at
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:160`
   and
   `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:181`
   cover the operator-command boundary for missing-token and gated-access
   blocked outcomes. They would fail if `main(...)` silently returned ready for
   blocked access or failed to write the bounded diagnostic report.

1. [x] `low` - Task 354's local green evidence is updated.

   Task 354 now records the focused diagnostic suite as `8 passed`, matching
   the current reviewer-run validation.

1. [ ] `low` - The current worktree still contains unrelated Review 37
   whitespace churn.

   File reference:

   - `docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md:23`

   The diff is still only a blank line after Review 37 frontmatter. This is not
   part of the Task 354 diagnostic runner behavior and should not be committed
   with this slice. Because this exact retained-review churn was already a
   Review 38 finding, the current uncommitted slice is not accepted in full
   until it is removed again.

   Required fix:
   Remove the whitespace-only Review 37 diff before commit and rerun
   `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
   to prove it is empty.

### Third-Pass Response

The diagnostic runner itself now has adequate bounded approval evidence: ready,
missing-token, and gated-access command outcomes are tested at the public
runner boundary, and Task 354's focused-suite evidence is current. The overall
current uncommitted slice remains `changes_requested` only because the
unrelated Review 37 whitespace diff is still present.

## Fourth Review Pass

Date: 2026-06-10

Decision: `approved`

Fourth-pass scope remained bounded to the Task 354 diagnostic runner slice. This
pass verified that the only remaining third-pass finding, unrelated Review 37
whitespace churn, is resolved in the current worktree. This approval does not
approve Task 352 live proof completion, does not unblock Story 53, and does not
approve route registration, Gateway publication, transcript persistence,
formatter output, replacement diarization implementation, or any claim that
pyannote diarization has run successfully.

### Fourth-Pass Evidence Reviewed

- `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
  produced no output, proving the unrelated Review 37 whitespace churn is gone.
- Current runner-boundary tests remain present:
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:141`
    covers the ready command outcome.
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:160`
    covers the missing-token blocked command outcome.
  - `tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py:181`
    covers the gated-access blocked command outcome.
- Task 354 still records the focused diagnostic suite as `8 passed` at
  `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md:153`.
- Validation run by this reviewer:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_audio_transcription_sidecar_diarization_access.py -q`
    passed `8 passed`.
  - `pdm run typecheck-all` passed with
    `Success: no issues found in 837 source files`.
  - `pdm run docs-validate` passed with `Validated 462 backlog files` and
    `Validated docs=537 rules=11`.
  - `pdm run skills-validate` passed with `skills-validate: ok`.
  - `pdm run handoff-validate` passed with `handoff-validate: ok`.
  - `git diff --check` passed.
- Rewriting gates were not rerun in this fourth pass because the implementer
  already ran them before the final Review 37 cleanup and reported that reruns
  reintroduce unrelated docs formatting churn. The non-mutating gates above
  provide sufficient review evidence for this bounded diagnostic slice.

### Fourth-Pass Finding Status

1. [x] `low` - The unrelated Review 37 whitespace churn is resolved.

   The current worktree has no diff for Review 37.

### Fourth-Pass Response

Approved for the bounded Task 354 diagnostic runner slice. The command has
truthful runner-boundary coverage for ready, missing-token, and gated-access
outcomes; generated evidence remains content-safe; and the retained docs state
does not claim Task 352 live proof completion or unblock Story 53.

## Hemma Access-Denied Evidence Review

Date: 2026-06-10

Decision: `approved`

This evidence pass reviewed only the bounded Hemma access-denied diagnostic
record for Task 354. It does not approve Task 352 live proof completion, does
not claim pyannote diarization ran, and does not unblock Story 53.

### Evidence Scope

- Committed/deployed runner revision:
  `f7a1eb61f4edbcd9530208d561baf9f59d89cf3d`.
- Ignored deploy verification report reviewed locally:
  `build/verification/hemma-deploy-verify/report.md`.
- Ignored Hemma diagnostic artifact reviewed remotely:
  `build/verification/stt-sidecar-diarization-access-hemma-f7a1eb6/diarization-access.json`.
- Docs updated in this evidence slice:
  - `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  - `.codex/handoff.md`

### Evidence Reviewed

- Local deploy report records `status=passed`, `expected_revision`,
  `remote_revision`, and `service_revision` all equal to
  `f7a1eb61f4edbcd9530208d561baf9f59d89cf3d`.
- Remote `pdm run run-hemma -- git rev-parse HEAD` returned
  `f7a1eb61f4edbcd9530208d561baf9f59d89cf3d`.
- Remote `pdm run run-hemma -- git status --short --branch` reported a clean
  `main...origin/main` checkout.
- Remote diagnostic JSON records:
  - `status=blocked`;
  - `backend_family=pyannote_audio`;
  - `profile_label=diarization_sv_en_primary`;
  - `model_family=pyannote_community_diarization`;
  - `artifact_label=pipeline_config`;
  - `token_env_var_names=["HF_TOKEN"]`;
  - `token_env_vars_present=true`;
  - `authenticated_account_observed=true`;
  - `failure_code=gated_model_access_denied`;
  - `exception_class=GatedRepoError`;
  - `operator_action=accept_or_request_pyannote_gated_model_access_for_hf_token_account`;
  - `secret_values_exposed=false`;
  - `private_cache_paths_exposed=false`;
  - `raw_model_identifiers_exposed=false`.
- `docs/backlog/tasks/task-354-provision-pyannote-diarization-access-and-replacement-decision-for-stt-sidecar.md`
  records the Hemma command, ignored artifact path, bounded JSON fields, and
  operator action.
- `.codex/handoff.md` points to the exact ignored Hemma diagnostic artifact and
  preserves the next action without token values, private cache paths, raw
  model identifiers, transcript text, generated media, or model artifacts.
- `git diff -- docs/backlog/reviews/review-37-ruthless-review-of-stt-sidecar-post-deploy-fasterwhisper-rocm-evidence.md`
  produced no output.

### Findings

No blocking findings.

The evidence proves that the Hemma `HF_TOKEN` variable is present, the
authenticated account is observable, the pyannote artifact request still fails
as gated, and the retained diagnostic payload is content-safe. It does not prove
pyannote diarization execution, exact speaker-count hints, min/max speaker-range
hints, exclusive speaker segments, English/Swedish fixture diarization, or Task
352 profile-proof readiness.

### Response

Approved for the bounded Task 354 access-denied evidence update. The next
product action remains external or governed: accept/request access for the
selected pyannote model family, or govern a real library-backed replacement
diarization decision if that access cannot be provisioned for this lane.

## Completion

Review retained with `approved` after the fourth implementation-review pass and
the Hemma access-denied evidence review. This approval is intentionally bounded
to the Task 354 diarization-access diagnostic runner and access-denied evidence
record. It does not accept Task 352 live proof completion and does not unblock
Story 53.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
