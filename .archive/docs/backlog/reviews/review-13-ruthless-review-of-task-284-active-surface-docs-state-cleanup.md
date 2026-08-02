---
id: review-13-ruthless-review-of-task-284-active-surface-docs-state-cleanup
title: Ruthless review of Task 284 active surface docs-state cleanup
type: review
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/tasks/task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work.md
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - .codex/handoff.md
  - README.md
  - .codex/rules/030-conversion-workflows.md
labels:
  - review
  - task-284
  - docs-state
  - examnet
  - cleanup
  - accepted
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of Task 284's docs-state cleanup.
- Governing authority:
  - `docs/backlog/tasks/task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work.md`
  - `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`
  - `AGENTS.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `.codex/rules/090-documentation-standards.md`
- Files reviewed:
  - `.codex/handoff.md`
  - `.codex/rules/030-conversion-workflows.md`
  - `README.md`
  - `docs/backlog/INDEX.md`
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
  - `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`
  - `docs/backlog/stories/story-45-exam-net-artifact-authoring-bundle-for-qti-and-editable-docx.md`
  - `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md`
  - `docs/backlog/tasks/task-11-pymupdf4llm-backend-deterministic-output-governance-compatibility-rules.md`
  - `docs/backlog/tasks/task-120-flatten-backlog-review-docs-into-single-file-review-artifacts.md`
  - `docs/backlog/tasks/task-154-remediate-t153-checkpoint-compatibility-scratch-guard-sizing-and-docs-proof-drift.md`
  - `docs/backlog/tasks/task-192-add-ml-specific-quality-gates-and-importlib-safe-qwen-test-collection.md`
  - `docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md`
  - `docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md`
  - `docs/backlog/tasks/task-200-refactor-qwen-training-metadata-module-into-bounded-control-plane-modules-without-compatibility-shims.md`
  - `docs/backlog/tasks/task-201-resolve-pytest-import-collision-by-renaming-duplicated-qwen-test-support-module.md`
  - `docs/backlog/tasks/task-202-harden-qwen-auxiliary-codebook-fusion-numerical-stability-and-assertion-contract.md`
  - `docs/backlog/tasks/task-203-audit-the-auxiliary-codebook-fusion-hot-path-against-story-29-mixed-precision-and-proof-lane-contracts.md`
  - `docs/backlog/tasks/task-224-reroute-qwen-operator-docs-through-the-active-surface-matrix-and-demote-legacy-proof-workflows.md`
  - `docs/backlog/tasks/task-232-make-the-story-31-lane-decision-after-the-post-t219-bounded-promotion-result.md`
  - `docs/backlog/tasks/task-253-cut-over-sir-convert-a-lot-agents-to-thin-skill-router.md`
  - `docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md`
  - `docs/backlog/tasks/task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work.md`
  - `docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md`
  - `docs/backlog/tasks/task-286-extract-service-v2-runtime-supervision-telemetry-and-checkpoint-planning-modules.md`
  - `docs/backlog/tasks/task-287-split-cli-route-submission-and-manifest-construction-responsibilities.md`
  - `docs/backlog/tasks/task-288-demote-experiment-lanes-behind-an-active-command-matrix.md`
  - `docs/backlog/tasks/task-289-finish-or-retire-task-200-qwen-metadata-scaffolds.md`
  - `docs/backlog/tasks/task-290-generate-and-validate-compact-service-onboarding-map.md`
  - `docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `scripts/sir_convert_a_lot/README.md`
- Public surfaces affected:
  - Active planning handoff and next-session guidance.
  - Backlog story/task status and generated indexes.
  - Operator-facing local/prod service command documentation.
  - Conversion workflow rule surface.
- Compatibility posture:
  - Docs-state-only cleanup. No runtime behavior changes are in scope.
  - Status and checklist changes must remain synchronized across task, story,
    handoff, and generated index surfaces.
- Evidence reviewed:
  - Current diff via `git diff --name-status` and focused file diffs.
  - Task acceptance grep probes for retired `.agents`,
    `docs/backlog/current.md`, `serve:sir-convert-a-lot`, and nonexistent
    facade names.
  - Lightweight validation gates listed below.

## Findings

1. [x] `blocker` - Task 284 leaves its own active docs state contradictory.

   - Evidence:
     `docs/backlog/tasks/task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work.md`
     is `status: completed`, but `.codex/handoff.md` still says to "Start with
     Task 284 docs-state cleanup, then Task 285 route registry" and repeats the
     same next action. Story 46 also leaves the Task 284 acceptance checkbox
     unchecked.
   - File references:
     - `docs/backlog/tasks/task-284-reconcile-active-surface-docs-state-before-exam-net-runtime-work.md:5`
     - `.codex/handoff.md:40`
     - `.codex/handoff.md:159`
     - `docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md:79`
   - Why it matters:
     Task 284's entire purpose is active-surface reconciliation before Task 285.
     A new agent following `.codex/handoff.md` will restart a completed task,
     while a Story 46 reader sees the exact same Task 284 criterion still open.
     That violates the repo status/checklist synchronization invariant and keeps
     the next runtime slice gated on ambiguous docs truth.
   - Required fix:
     Reconcile the state in one docs slice. Either revert Task 284 to a
     non-terminal state and make the handoff say it is blocked by Review 13, or
     finish the Task 284 closeout by updating handoff next actions to start at
     Task 285 and checking the Story 46 Task 284 criterion only after this
     review is resolved.
   - Proof requirement:
     Add a targeted docs-state check or reviewer probe proving there is no
     active "start Task 284" instruction after Task 284 is terminal. Run
     `pdm run docs-sync`, `pdm run docs-validate`,
     `pdm run skills-validate`, `pdm run handoff-validate`, and
     `git diff --check`.

   Resolved on 2026-05-13. `.codex/handoff.md` now says Task 284 completed,
   points the next Story 46 action at Task 285, and Story 46 checks the Task 284
   acceptance criterion. The targeted handoff probe for active "start Task 284"
   wording returns no matches.

1. [x] `high` - The root README still exposes raw production compose commands as
   active service commands.

   - Evidence:
     `README.md` lists `docker compose up -d sir_convert_a_lot_prod` and
     `docker compose logs -f sir_convert_a_lot_prod` under active "Service &
     Conversion" commands even though the repo has named `pdm run prod-*`
     wrappers and the command policy prefers named script surfaces.
   - File reference:
     - `README.md:55`
   - Why it matters:
     Task 284 claims the conversion workflow command docs agree with
     AGENTS/README command policy. Leaving raw production compose commands in
     the root active command list tells operators to bypass the committed
     `prod-compose.sh` wrappers, where compose file selection, BuildKit-aware
     build/recreate behavior, and repo command grammar are centralized. That is
     exactly the kind of contradictory active service command this task is
     supposed to remove before more runtime work.
   - Required fix:
     Replace the root README's active production compose commands with the
     named wrapper commands, for example `pdm run prod-start` /
     `pdm run prod-logs` for local prod-compose inspection or
     `pdm run run-hemma -- pdm run prod-*` / the Hemma runbook for remote
     operations. Keep direct `docker compose` commands only in debugging
     references where the rule explicitly permits them as diagnostics.
   - Proof requirement:
     Add a grep or docs validator expectation that active root command docs do
     not advertise `docker compose up -d sir_convert_a_lot_prod` or
     `docker compose logs -f sir_convert_a_lot_prod`. Run the docs gates above.

   Resolved on 2026-05-13. The README's active service command list now uses
   `pdm run dev-*` and `pdm run prod-*` wrapper commands, and the targeted grep
   for raw `docker compose up -d/logs -f sir_convert_a_lot_prod` returns no
   matches.

## Decision

approved

## Response

- The diff is docs/rules only; no Python/runtime behavior changes were found in
  the Task 284 patch.
- The two retained findings are resolved. Task 284's terminal state is now
  synchronized across task, story, and handoff surfaces, and the README no
  longer advertises raw production compose commands as active operator commands.
- The acceptance grep probes for retired `.agents`, retired
  `docs/backlog/current.md`, `serve:sir-convert-a-lot`, nonexistent facade
  names, active "start Task 284" wording, and raw root README prod compose
  commands now align with Task 284.
- Review validation:
  - `pdm run docs-sync` -> refreshed generated docs indexes.
  - `pdm run docs-validate` -> `Validated 363 backlog files`;
    `Validated docs=422 rules=11`.
  - `pdm run skills-validate` -> `skills-validate: ok`.
  - `pdm run handoff-validate` -> `handoff-validate: ok`.
  - `git diff --check` -> clean.
- Remediation probes:
  - `rg -n "Start with Task 284|Start Story 46 with Task 284" .codex/handoff.md`
    -> no matches.
  - `rg -n "docker compose (up -d|logs -f) sir_convert_a_lot_prod" README.md`
    -> no matches.

## Follow-up Actions

1. [x] Remediate the two findings above before Task 284 can be approved and before
   Task 285 route-registry work starts.

## Completion

Review 13 is retained as `changes_requested` on 2026-05-13.

Review 13 is closed as `approved` on 2026-05-13 after remediation.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
