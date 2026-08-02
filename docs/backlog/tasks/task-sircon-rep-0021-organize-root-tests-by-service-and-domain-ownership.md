---
type: task
id: TASK-SIRCON-REP-0021
title: Organize root tests by service and domain ownership
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-03'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- "Root tests are organized under seven existing behavior-owned directories: service, conversion, exam, speech, operations, research, and repository."
- "Root Pytest collection completes without errors and retains the pre-move collected item count; focused representative tests pass for every new directory."
- "Test support imports are updated only as required by the moves, while production code, test behavior, Qwen tests, quality facts, and product operations remain unchanged."
- "No broad root aggregate test execution becomes part of implementation or closeout."
---

## Context

ST-SKILL-08-07 requires Sir Convert-a-Lot to replace its flat root test layout
with behavior-owned topology before shared governance derives named service and
domain checks. The completed current-corpus migration and governed archive are
recorded by archived TASK-SIRCON-REP-0001 and TASK-SIRCON-REP-0020. This task is
the next serial consumer slice.

The root project currently collects approximately 1,799 tests from
`tests/sir_convert_a_lot/*.py` plus one repository-docs test. The flat layout
mixes API/service, conversion, exam, speech, operations, research, and
repository-tooling behavior. The shared topology can derive directory scopes;
it cannot truthfully derive those scopes from filename patterns or a maintained
selector matrix.

## Impact And Escalation

This task changes test placement and test-only imports. It does not change
production behavior or shared-package configuration. A test whose ownership is
genuinely ambiguous stops its own move for parent classification; it does not
justify a new taxonomy, product refactor, or explicit selector map.

## Decision And Assumption Ledger

Every material implementation choice must be closed by an accepted source before
the task becomes ready.

| ID | Status | Contract term, decision, or assumption | Recommendation or closed decision | Other highly plausible options | Motivation | Source |
| --- | --- | --- | --- | --- | --- | --- |
| SIR-TOP-001 | closed | What does this task own? | Move all root test modules and their test-only support modules into behavior-owned directories. Keep shared data fixtures under `tests/fixtures`. | Change production modules or quality facts in the same task. | One responsibility keeps the topology correction behavior-neutral and leaves derived configuration to the next slice. | ST-SKILL-08-07 SIR-004F and repository-bounded slice 3; user direction to proceed |
| SIR-TOP-002 | closed | Which directory topology is sufficient? | Use exactly `service`, `conversion`, `exam`, `speech`, `operations`, `research`, and `repository` beneath `tests/sir_convert_a_lot`; place the existing root docs test under `repository`. | Mirror architecture layers; add nested subdomains; maintain a selector manifest. | These seven directories follow existing product behavior, cover the current corpus, and are directly derivable without a second authority surface. | Retained quality-topology discovery; ST-SKILL-08-07 SIR-004F; user anti-overengineering direction |
| SIR-TOP-003 | closed | How is ownership assigned? | Assign each test by its primary behavior under test. Keep its private support module with that behavior. Cross-domain imports do not create duplicate ownership. | Classify by imported production package or allow duplicate tests. | Behavior ownership remains stable when implementation layers overlap. | Retained derived-scope discovery; user service/domain-driven correction |
| SIR-TOP-004 | closed | What changes are permitted inside moved tests? | Update only module paths, test-support imports, and path-sensitive test expectations required by the moves. Preserve assertions, fixtures, parametrization, and runtime behavior. | Opportunistically fix or refactor tests. | The task proves a structural move rather than mixing in test or product redesign. | ST-SKILL-08-07 protected boundary; acceptance criteria |
| SIR-TOP-005 | closed | What happens to Qwen? | Leave `qwen/tests`, Qwen metadata, commands, dependencies, and lock untouched. Root tests that verify Qwen integration remain root-owned under `operations`. | Merge Qwen into root topology. | Qwen is an independently owned PDM project while root integration contracts belong to root operations. | ST-SKILL-08-07 SIR-004B and SIR-004F |
| SIR-TOP-006 | closed | How is equivalence proved without a broad run? | Capture pre-move and post-move collection-only results, require the same collected item count and no collection errors, then run one representative focused test file from each new directory. | Execute the full root aggregate; compare a durable node-ID manifest. | Collection proves discovery/import integrity and focused files prove execution without turning 1,799 tests into a routine gate or creating a new manifest. | ST-SKILL-08-07 SIR-004H; proof-selection behavior-preserving refactor mode; user direction |
| SIR-TOP-007 | closed | Does this task adopt derived quality facts? | No. It leaves `[tool.repository-governance.quality].projects` unchanged; the next serial task derives scopes from the completed directories. | Combine topology and quality adoption. | Separating the physical move from derived configuration keeps failure attribution and review bounded. | ST-SKILL-08-07 repository-bounded slices 3 and 4 |
| SIR-TOP-008 | closed | What is explicitly excluded? | No product code, Docker/Hemma/GPU/deployment behavior, package release work, dependency or lock changes, docs migration, archive work, broad root suite, Qwen suite, or remote mutation. | None. | The cutover must preserve product and operational behavior and reuse the established consumer pattern. | ST-SKILL-08-07 protected boundary and non-goals; user direction |

## Plan

Move the root tests once into seven first-level behavior directories. Update
only import paths and path-sensitive test references broken by those moves.
Retain the shared fixture-data directory. Prove collection integrity and seven
small representative executions. Do not add a mapping file or change quality
facts.

## Implementation Steps

1. Capture the clean-current Git basis and the collection-only baseline for the
   root test project; retain the collected item count and any collection errors.
2. Partition tracked root test and support modules into the seven accepted
   directories by primary behavior. Stop only on a genuinely ambiguous module.
3. Move the files and update only test-package imports and path-sensitive test
   expectations required by the new locations.
4. Run collection-only proof and compare its item count with the baseline.
5. Run one representative test file from each directory:
   `test_service_import_side_effects.py`, `test_specs_v2.py`,
   `test_digiexam_dxe_parser.py`, `test_audio_transcription_route_policy.py`,
   `test_run_hemma_wrapper.py`, `test_benchmark_gpu_governance.py`, and
   `test_docs_as_code_index_docs.py`.
6. Run test-path formatting, lint, and typechecking only where applicable,
   followed by the docs and whitespace gates required for task closeout.

## Proof

- Proof mode: behavior-preserving refactor proof. Behavioral red/green does not
  apply because the task changes placement, not executable behavior.
- Before and after: `pdm run pytest-root --collect-only -q tests`; require no
  collection errors and the same collected item count.
- After: run `pdm run pytest-root` with the seven exact representative test
  paths at their new locations. Require all selected tests to pass.
- Audit: `git diff --summary` must show moves plus only necessary test-only
  edits. `git diff --name-only` must show no production, Qwen, dependency,
  lock, or quality-facts path.

## Validation

- `pdm run format --check tests` if the installed producer accepts a scoped
  target; otherwise use the repository's existing direct Ruff check on the
  changed test paths.
- `pdm run lint` only through a discovered scoped target. Do not run its broad
  repository form merely for this move.
- `pdm run typecheck-all` with the changed test directories only if the
  producer honors path arguments; otherwise record non-applicability rather
  than broadening the task.
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

No root aggregate, coverage aggregate, Qwen suite, Docker, Hemma, GPU, or
remote command is selected.

## Stop Conditions

- A test cannot be assigned by primary behavior without inventing a new domain.
- A move requires production-code, product-behavior, dependency, lock, Qwen,
  shared-package, or quality-facts changes.
- Post-move collection has errors or a different item count.
- A representative failure reveals behavioral change rather than an import or
  path correction caused by the move.
- Completion would require the broad root aggregate.

## Lessons Learned

The flat tree cannot support the accepted derived design. Filename selectors or
a maintained mapping would recreate the explicit design already rejected in
the HuleEdu cutover.

## Notes

The allocator initially proposed the archived identity
`TASK-SIRCON-REP-0020`. The scaffold was corrected to the next unused immutable
identity, `TASK-SIRCON-REP-0021`; the archived task remains unchanged.

## Readiness

The ledger is closed from ST-SKILL-08-07, retained Sir quality discovery, and
the user's explicit approval to proceed with the recommended next slice. The
task remains proposed pending independent plan review. Implementation is not
authorized yet.

Residual risk is limited to a small number of test-support imports and
path-sensitive assertions that may need test-only correction during moves.

## Closeout

Not started.
