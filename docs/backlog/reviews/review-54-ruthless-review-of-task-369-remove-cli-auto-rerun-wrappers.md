---
id: review-54-ruthless-review-of-task-369-remove-cli-auto-rerun-wrappers
title: Ruthless review of Task 369 remove CLI auto-rerun wrappers
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/audio-transcription-service-api-artifact-contract.md
  - docs/converters/downstream_integration_contract_v2.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - approved
  - task-369
  - cli
  - idempotency
  - service-boundary
---

Structured review artifact for implementation or readiness checks.

## Review Scope

Independent ruthless review for Task 369. This reviewer did not author the
implementation or tests, did not create a worktree, stayed on `main`, did not
deploy or live-proof, and did not modify production/test implementation files.
The only intentional mutations from this review pass are this retained review
artifact and generated docs index refreshes required by docs-as-code.

Instructions and authorities read:

- `AGENTS.md`
- `.codex/handoff.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md`
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `docs/converters/audio-transcription-service-api-artifact-contract.md`
- `docs/converters/downstream_integration_contract_v2.md`
- `docs/converters/sir_convert_a_lot.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`

Task 369 files reviewed:

- `.codex/handoff.md`
- `docs/backlog/INDEX.md`
- `docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md`
- `docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md`
- `docs/converters/sir_convert_a_lot.md`
- `scripts/sir_convert_a_lot/interfaces/cli_app.py`
- `scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py`
- `scripts/sir_convert_a_lot/interfaces/http_client_v2_models.py`
- `tests/sir_convert_a_lot/test_cli_v2_routes.py`
- `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py`
- `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py`

Public/operator surfaces affected:

- `convert-a-lot convert` retry option surface.
- `RetryModeV2` client contract.
- CLI create-job submission orchestration, progress callback, artifact
  download, and manifest entry construction.
- CLI and backlog documentation for Task 63/Task 369 idempotency ownership.

Compatibility posture:

- This is an intentional clean removal of the Task 63 caller-side
  failed-replay compatibility wrapper after Task 368 made retryable failed
  reattempts Service API v2-owned.
- `--replay-only` is removed rather than retained as a legacy alias.
- `--new-job` remains as an explicit independent user-intent affordance only;
  it is not reached from failure handling and does not remediate failed
  replays.

Dirty-tree boundaries:

- Unrelated Task 367 review/task docs and Task 370/Qwen files are present in
  the working tree. I did not edit, revert, normalize, or treat those files as
  Task 369 implementation evidence.
- `docs/backlog/INDEX.md` already includes unrelated generated Task 370 entries
  from the dirty tree. This review preserves that state rather than attempting
  to separate generated index churn manually.

## Findings

No blocking findings.

The Task 369 code path removes the caller-owned second-submit branch. The
client now accepts only `retry_mode in {"auto", "new_job"}`
(`scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py:82`),
submits exactly one create-job request for normal `auto` mode
(`scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py:94`), and
raises `job_not_succeeded` for terminal non-success service responses instead
of salting a new idempotency key
(`scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py:117`).
The only retained key mutation is gated by explicit `retry_mode == "new_job"`
(`scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py:91`).

The CLI surface no longer exposes the old workaround flag. `--replay-only` is
gone, `--new-job` help text states independent conversion intent, and
`convert_command()` maps only that explicit flag to `retry_mode="new_job"`
(`scripts/sir_convert_a_lot/interfaces/cli_app.py:183`,
`scripts/sir_convert_a_lot/interfaces/cli_app.py:249`). The route submission
layer records the service-returned outcome job in the manifest and no longer
prints or stores `rerun_of_job_id`
(`scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py:384`,
`scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py:401`).
`ArtifactOutcomeV2` also no longer has a rerun lineage field
(`scripts/sir_convert_a_lot/interfaces/http_client_v2_models.py:47`).

The docs under current CLI/API authority now point to Task 368 service-owned
reattempts and explicitly forbid CLI remediation by key salting, filename
changes, or a caller-side second create-job request
(`docs/converters/sir_convert_a_lot.md:94`). The old Task 63 file is retained
as historical context only and names Task 368/369 as current authority
(`docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md:23`).

The tests are truthful for the removed DDD violation. The red/green node
proves the old behavior would have converted a strict failed replay into an
unwanted second submit and now raises on the service-returned failed job after
one POST with the original key
(`tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py:35`). The service
owned reattempt case proves a `service_reattempt` response succeeds without a
client rerun
(`tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py:145`). The strict
failed replay test covers terminal failed replay without widening canceled-job
semantics
(`tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py:263`), and the
CLI flag test proves retained `--new-job` maps to independent intent only
(`tests/sir_convert_a_lot/test_cli_v2_routes.py:366`). Manifest tests preserve
the service-returned job id in incremental and terminal entries
(`tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py:172`).

Source search found no active implementation/test references to
`replay_only`, `--replay-only`, `_rerun_`, or `rerun_of_job_id` in the reviewed
code paths. Remaining mentions are historical/governing docs for Task 63,
Task 369, Task 368 review context, or older out-of-scope Task 342 planning
text; the current CLI authority is `docs/converters/sir_convert_a_lot.md` plus
Task 368/369.

Residual risk from skipped mutating gates: the implementation worker
intentionally skipped whole-repo `pdm run format-all` and `pdm run lint-fix`
because unrelated Task 367 and Task 370/Qwen dirty work is present. This review
ran focused tests and scoped whitespace checking, but it did not run mutating
repo-wide format/lint fixers and did not independently rerun the worker's full
`typecheck-all` or `coverage-gate`. Before commit/deploy, the overseer should
either isolate the Task 369 patch or explicitly accept the worker's reported
green `typecheck-all`/`coverage-gate` evidence, then run final non-destructive
or isolated formatting/lint gates without normalizing unrelated dirty work.

## Follow-up Actions

1. Final overseer close-out before commit/deploy must decide how to handle the
   skipped mutating `format-all`/`lint-fix` gates in the dirty tree.
1. Task 369 still requires the post-commit/deploy Hemma live CLI proof named in
   the task: one CLI create-job submission, Task 368 service-owned reattempt
   lineage, terminal success, artifact fetch proof, and bounded log scan.
1. If zero stale backlog wording is required beyond current public/operator
   docs, normalize older Task 342 planning text in a separate governed docs
   cleanup; this review did not edit out-of-scope historical planning docs.

## Decision

approved

## Response

Task 369 is approved for overseer close-out. The reviewed patch removes the
client/CLI failed-replay auto-rerun wrapper, keeps `--new-job` as explicit
independent user intent, preserves one-submit manifest truth, and aligns the
current CLI docs with Task 368 service-owned retryable failed reattempts.

This approval is local-code/docs review only. It does not replace the required
post-deploy Hemma live proof, and it does not claim the skipped mutating
format/lint gates were run in this dirty tree.

## Completion

Reviewer-run evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py -q`
  passed: `17 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py -q`
  passed: `6 passed`.
- `git diff --check -- .codex/handoff.md docs/backlog/INDEX.md docs/backlog/tasks/task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts.md docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md docs/converters/sir_convert_a_lot.md scripts/sir_convert_a_lot/interfaces/cli_app.py scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py scripts/sir_convert_a_lot/interfaces/http_client_v2_models.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py`
  passed.
- Search review:
  `rg -n "replay_only|--replay-only|rerun_of_job_id|_rerun_|auto-rerun|auto rerun|second create-job|salting idempotency|filename hacks|failed/canceled idempotent" ...`
  found no active reviewed code/test retained wrapper references. Remaining
  matches are current prohibition text, Task 369/63 governance text, Task 368
  review context, and older out-of-scope Task 342 planning text.

Worker-reported evidence considered but not independently rerun in full:

- Red evidence recaptured by temporarily reversing only Task 369 production
  diffs: focused node failed with `Failed: DID NOT RAISE ClientErrorV2`.
- Same focused node green.
- `pdm run typecheck-all`: success, `898 source files`.
- `pdm run docs-sync`, `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`: passed.
- `pdm run coverage-gate`: `1748 passed`, `6 skipped`, coverage `95.53%`.

Skipped in this review pass:

- No deploy or live proof, by instruction.
- No production/test/doc implementation fixes, by instruction.
- No `pdm run format-all` or `pdm run lint-fix`, because they are mutating
  whole-repo gates and unrelated Task 367/Task 370 dirty work is present.
- No full `typecheck-all` or `coverage-gate` rerun by this reviewer; the
  focused behavioral gates above were sufficient for retained review, with
  final overseer gates still required before commit/deploy.

## Checklist

- [x] Scope reviewed
- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up actions recorded
- [x] Review closed
