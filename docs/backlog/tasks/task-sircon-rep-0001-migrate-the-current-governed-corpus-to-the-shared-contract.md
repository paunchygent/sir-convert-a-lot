---
type: task
id: TASK-SIRCON-REP-0001
title: Migrate the current governed corpus to the shared contract
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-08-02T10:51:16+0200'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User-approved SIR-001 through SIR-004L authority and inline Plan Document Review follow-up approval at f77f5d78.
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - All 231 current authored governance surfaces, including legacy Task 385, receive one explicit current-contract disposition; the already-current TASK-SIRCON-REP-0001 remains the migration authority rather than a migration source.
  - All 395 terminal or historical records remain byte-for-byte unchanged and remain outside current relationships, indexes, gates, and lifecycle operations.
  - Shared validation is the only current-document authority; historical-validator execution remains disabled and any retained historical inspection is read-only and historical-only.
  - One simple manifest partitions the complete workload across eight disjoint documentation-specialist assignments without becoming a second authority system.
  - Same-repository authored links are repository-relative where possible, while genuine host, container, and cross-repository paths remain explicit.
---

## Context

The completed bootstrap installed the shared routine system, declared the root
and Qwen projects, synchronized generated bindings, and disabled every active
historical-validator route. Sir's current governed corpus still uses the legacy
document contract. The public shared `docs-sync` therefore stops at
`docs/_meta/docs-contract.yaml` because that file lacks the shared `types` and
`frontmatter` blocks.

Fresh discovery from clean current Sir main finds 231 current authored
migration surfaces: 209 governed documents that the shared migration CLI can
inventory and 22 rules, skills, entrypoint, handoff, and contract surfaces that
require explicit parent-owned dispositions. The cohort includes legacy Task
385 and excludes this already-current task. The 395 terminal or historical
records are unchanged from story planning.

This task performs that one current-corpus migration. It changes no conversion,
API, job-state, R2, Docker, Hemma, GPU, deployment, observability, Qwen, test
topology, or quality-scope behavior.

## Impact And Escalation

The write set is the 231 declared current authored surfaces, the migration
profile and run artifacts, focused historical-validator isolation, generated
documentation indexes, and this task record. Package defects discovered at the
real Sir boundary return to the shared producer for the smallest governed
repair; this task may then advance its immutable package pin, lock, and bindings
to consume that repair. Backlog prose does not freeze a package version or
planning SHA.

Product behavior, test relocation, derived quality, broad test execution,
operations changes, and parity-gated retirement belong to later story slices.

## Decision And Assumption Ledger

| ID | Type | Status | Contract term, decision, or assumption | Recommendation or closed decision | Other highly plausible options | Motivation | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SIR-COR-001 | cohort | closed | Which authored surfaces migrate? | Migrate the exact 231-source current cohort: 209 CLI-managed documents plus 22 explicitly assigned non-CLI governance surfaces. Include legacy Task 385; exclude already-current TASK-SIRCON-REP-0001. | Reuse the stale 230 count or omit non-CLI surfaces. | The fresh delta proves Task 385 is the only new legacy source and the accepted story requires every current authoritative surface. | ST-SKILL-08-07 SIR-004C; retained `sir-corpus-refresh` discovery |
| SIR-COR-002 | history | closed | What remains historical? | Keep all 395 terminal or historical records byte-for-byte unchanged and outside current authority. The sole `responded` review remains current. | Rewrite terminal records or classify the responded review as terminal. | Preserves historical truth and avoids reopening completed work. | ST-SKILL-08-07 SIR-004D; retained discovery; user direction |
| SIR-COR-003 | manifest | closed | What does the migration manifest own? | One simple authored 231-row exact-path manifest owns workload partitioning and completeness only. The package's sealed 209-source run manifest is its mechanically derived `docs/` subset, not a second authority. | Encode lifecycle, dependencies, or a second policy model. | The document contract and source records remain semantic authority while the package retains its transactional subset. | ST-SKILL-08-07 SIR-004E; user direction |
| SIR-COR-004 | lanes | closed | How do legacy source lanes map to the shared vocabulary? | Map epic, story, task, review, reference, and runbook to their matching shared lanes; decision to ADR; and programme, converter, and PDR to typed references that preserve their existing purpose. Missing owner, parent, target, reviewer, acceptance, or status semantics stop for parent resolution. | Add new shared document types or silently invent semantics. | Uses the existing shared contract without expanding it and preserves product-contract meaning as documentation. | Shared migration workflow; HuleEdu and Skriptoteket profiles; retained discovery |
| SIR-COR-005 | specialists | closed | How is authoring divided? | Freeze eight disjoint documentation-specialist work orders, the maximum child capacity available under the current nine-slot configuration. Each work order combines one package assignment with a disjoint share of the 22 non-CLI rows. Specialists edit only assigned candidates; the parent owns decisions, shared writes, apply/recovery, indexes, and Git. | Fewer partitions, overlapping shared writes, or a separate manual exception lane. | Maximizes throughput and proves every one of the 231 rows has exactly one authoring owner. | User direction; shared migration runbook |
| SIR-COR-006 | non_cli | closed | How are the 22 surfaces outside CLI inventory handled? | Include the exact paths listed under Non-CLI Workload Rows in the authored manifest and distribute them once across the same eight work orders. Preserve Sir-specific rules and skills; align shared-governance routes and current contract surfaces without retiring overlaps before later parity proof. | Ignore them, keep them as parent-owned exceptions, or retire shared-looking files now. | Completes the accepted corpus boundary without a second assignment system or stealing the later retirement slice. | ST-SKILL-08-07 SIR-004C, SIR-004G, SIR-004I; retained discovery |
| SIR-COR-007 | validator | closed | What authority may the historical validator retain? | Shared validation becomes the sole current-document gate. Keep active historical-validator aliases, hooks, and lifecycle routes absent; any retained inspection is read-only, historical-only, and excluded from indexes and mutation authority. | Run both validators or delete all source before parity-gated retirement. | Keeps history inspectable without preserving competing current authority. | ST-SKILL-08-07 current/historical boundary; TASK-SKILL-08-07-01; user direction |
| SIR-COR-008 | package | closed | Which shared package version governs execution? | At execution start, use the current approved immutable package and retain the exact dependency, lock, runtime, and revision evidence. Advance the package and Sir pin during this task whenever a real Sir requirement needs a shared repair. | Freeze the planning version or implement local compatibility behavior. | Cutover discovery may require producer corrections; stale backlog pins caused prior cutover churn. | ST-SKILL-08-07 SIR-004A; user direction |
| SIR-COR-009 | paths | closed | Which authored paths may remain absolute? | Convert same-repository local-machine paths to repository-relative references where possible; retain genuine host, container, and cross-repository paths when they are operational facts. | Rewrite operational paths inaccurately or preserve avoidable workstation paths. | Makes governance portable without corrupting operations truth. | ST-SKILL-08-07 SIR-004L; user direction |
| SIR-COR-010 | proof | closed | What proves this migration? | Use contract/validator proof: exact cohort and exclusion hashes, plan coverage, eight disjoint assignments, dry-run/apply/report, shared docs sync/validation, focused historical-validator isolation proof, deterministic rerun, and diff hygiene. Do not run product or broad test suites. | Behavioral product proof or full repository tests. | The task changes governance shape and validator authority, not product behavior. | Proof-selection contract; ST-SKILL-08-07 SIR-004H |

## Plan

Install the execution-current shared contract and a Sir-specific version-1
migration profile. Author one simple 231-row workload manifest, derive the
package's 209-source run subset from it, and distribute the remaining 22 rows
across the same eight disjoint work orders as the package assignments. Let
documentation specialists prepare only their combined assigned paths, then
apply and validate the corpus once through the parent-owned transaction. Keep
all 395 historical records unchanged and keep historical validation outside
current execution.

### Non-CLI Workload Rows

The 22 exact non-CLI rows are:

- `.codex/rules/000-rule-index.md`, `.codex/rules/010-foundational-principles.md`, `.codex/rules/030-conversion-workflows.md`, `.codex/rules/035-docling-pdf-conversion.md`, `.codex/rules/046-docker-compose-v2-and-debugging.md`, `.codex/rules/070-testing-and-quality-gates.md`, `.codex/rules/081-pdm-and-dependency-management.md`, `.codex/rules/085-postgresql-and-migrations.md`, `.codex/rules/090-documentation-standards.md`, `.codex/rules/095-qwen-training-architecture-boundaries.md`, and `.codex/rules/096-qwen-experiment-governance.md`;
- `.codex/skills/sir-convert-a-lot-colab-hemma/SKILL.md`, `.codex/skills/sir-convert-a-lot-devops-hemma/SKILL.md`, `.codex/skills/sir-convert-a-lot-qwen-finetuning/SKILL.md`, and `.codex/skills/speech-model-finetuning-on-hemma/SKILL.md`; and
- `AGENTS.md`, `README.md`, `.codex/handoff.md`, `.codex/long-term-memory/index.md`, `docs/DOCS_STRUCTURE_SPEC.md`, `docs/backlog/README.md`, and `docs/_meta/docs-contract.yaml`.

## Implementation Steps

1. Merge current main and record the clean Sir basis plus the execution-current immutable dependency, lock, installed runtime, and source revision. If a shared producer repair is required, complete that bounded repair and advance the Sir pin before freezing the plan.
2. Install the shared current `docs/_meta/docs-contract.yaml` shape and the minimal Sir `docs/_meta/repository-governance-migration.yaml` lanes needed for the ten discovered legacy source types. Add no new document type or local migration engine.
3. Author one 231-row manifest from the 209 CLI-managed sources and the 22 listed non-CLI paths. Derive the package's exact 209-source input subset from those rows. Record one disposition for Task 385, exclude TASK-SIRCON-REP-0001, and hash all 395 historical exclusions before mutation.
4. Resolve only authority-backed owner, relationship, reviewer, acceptance, status, target-lane, and path inputs. Stop rather than invent a missing semantic value.
5. Run package migration planning for the derived 209-source subset with `--specialist-count 8`. Combine each package assignment with a disjoint allocation of the 22 non-CLI rows to form eight complete work orders. Verify their union equals the authored 231-row manifest exactly once and shared outputs remain parent-owned.
6. Dispatch all eight combined work orders to documentation specialists. Specialists edit only their assigned candidates and return unresolved facts to the parent.
7. Reconcile the eight results, run the package dry-run, and apply the sealed plan once. Use package recovery or resume only for a recognized journal state.
8. Align the 22 non-CLI surfaces to their accepted dispositions and enforce historical-validator read-only isolation without retiring parity-unproven surfaces.
9. Regenerate the four required indexes, run shared validation and a clean deterministic rerun, verify the 395 exclusion hashes, and retain the manifest, assignment results, journal, report, and concise proof.
10. Obtain independent implementation review before lifecycle closeout and integration.

## Proof

- Proof mode: contract or validator proof. Behavioral product red/green does not apply because product behavior is unchanged.
- Pre-change proof: the shared docs gate fails at the legacy contract shape; inventory and hashes identify exactly 231 current sources and 395 exclusions.
- Focused executable proof applies only if historical-validator code must change: demonstrate that current paths cannot enter that inspection and that inspection cannot mutate repository files.
- Post-change proof: migration dry-run/apply/validate/report succeeds; the package's 209-source run manifest equals the `docs/` subset of the authored 231-row manifest; the eight combined work orders cover all 231 rows exactly once; the four generated indexes reproduce cleanly; shared `docs-validate` accepts the complete current corpus; all 395 excluded files retain their hashes.
- Code/search audit: no current command, hook, index, or lifecycle route invokes historical validation; no avoidable same-repository absolute workstation path remains in migrated authored governance.

## Validation

- Package migration `inventory`, `classify`, `plan --specialist-count 8`, `dry-run`, `apply`, `validate`, and `report` against one task-owned run directory.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- Focused historical-validator isolation tests only if that source changes.
- Exact cohort coverage, assignment disjointness, exclusion-hash, path-portability, and reproducible-index checks selected from the migration artifacts.
- `git diff --check`

No unscoped product, Qwen, Docker, Hemma, conversion, deployment, or broad
repository suite runs.

## Stop Conditions

- Inventory differs from the 231 current-source boundary or the 395-file exclusion boundary without an authority-backed current-main explanation.
- A source lacks one unique target or a required semantic value cannot be derived from accepted authority.
- A combined work order overlaps another, the eight-work-order union differs from the authored 231-row manifest, the package run manifest differs from its exact 209-row subset, or a specialist requires a shared write.
- The profile, source set, candidate seal, plan digest, dependency revision, or canonical write set changes after freeze.
- Any terminal or historical file changes, or a current relationship targets terminal or ambiguous legacy authority.
- Historical validation regains a current command, hook, index, lifecycle, or mutation route.
- A required producer repair would add a Sir-local compatibility layer or widen product behavior.

## Lessons Learned

- Treat the manifest as a workload checklist, not a second governance model.
- Understand the entire active corpus before authoring mappings; preserve history instead of forcing it through the current lifecycle.
- Let real consumer requirements advance the shared producer, then consume the new immutable result without prose-pinning the cutover.

## Notes

Planning discovery is retained under session
`019fc193-dab6-7e57-8ec8-8df2fa670cc9`. The earlier accepted corpus discovery
and this task's refresh together establish the current and historical boundaries.

The scaffold transaction could not run `docs-sync` because the task exists to
replace the legacy contract that the shared synchronizer rejected. The shared
creator still emitted the current task contract, `git diff --check` passed, and
the proposed scaffold was published from clean current main. This exception
ends when this task's migrated shared docs gate passes.

## Plan Document Review

- Timestamp: `2026-08-02T10:47:30+0200`.
- Reviewer: independent `plan-document-reviewer`.
- Decision: `changes_requested`.
- Reviewed scope: this task at exact committed planning head `23a01520`; ready
  ST-SKILL-08-07 and its user-approved SIR-001 through SIR-004L ledger; retained
  current-corpus refresh `0001`; the shared migration workflow and runbook;
  Sir's docs-governance routes and completed bootstrap boundary; the current
  proof-selection contract; and the HuleEdu and Skriptoteket current-corpus
  precedents needed to check the manifest and assignment boundary.
- Governing authority: the accepted current-corpus slice; the user's directions
  to include Task 385, keep one simple workload/completeness manifest, preserve
  all terminal history, keep historical validation off and read-only, avoid
  same-repository absolute paths, retain rolling package identity as execution
  evidence, and use the maximum eight documentation specialists; and the Scope
  Derivation Gate.
- Finding 1 (high): the acceptance criterion and SIR-COR-003, SIR-COR-005, and
  SIR-COR-006 require one 231-row workload manifest and eight disjoint
  documentation-specialist assignments covering the complete 209 CLI plus 22
  non-CLI cohort exactly once. Implementation steps 5-6 freeze and dispatch the
  package assignments, but the package can inventory only the 209 `docs/`
  sources; step 8 then moves the 22 non-CLI surfaces into a separate
  parent-owned edit after those assignments. The implementer would have to
  invent whether the 22 paths join the eight work orders, remain parent-owned
  exceptions, or require a second assignment artifact, and `manifest.yaml`
  cannot accept those paths under the current package contract. Repair the plan
  by distinguishing the simple 231-row workload/completeness manifest from the
  package's sealed 209-source run manifest, defining their exact subset and
  reconciliation invariant, and stating how all 22 non-CLI dispositions enter
  the same eight disjoint work orders without transferring semantic decisions
  or shared writes from the parent. If a shared non-CLI surface must instead
  remain outside specialist ownership, return that conflict to planning or the
  user rather than silently weakening the complete-workload criterion.
- Permitted next step: repair only the manifest/assignment boundary above and
  return this changed task to the same readiness reviewer. No `proposed ->
  ready` transition or implementation is permitted.
- Validation not run: no migration phase, package/runtime identity check,
  corpus mutation, specialist assignment, docs synchronization, validator
  execution, product test, or broad repository check ran. The supplied clean
  `git diff --check` result and the documented legacy-contract `docs-sync`
  exception were accepted without duplication.
- Residual risk: the exact execution-time immutable package tuple and
  current-main cohort can still drift and must stop implementation under the
  existing plan. Lane mappings, the 395-file exclusion boundary, Task 385
  inclusion, rolling package-repair policy, validator isolation, selected
  contract proof, path policy, and the prohibition on product, quality,
  operations, compatibility, package-freeze, and broad-test expansion otherwise
  align with accepted authority.

The same independent reviewer re-reviewed only the bounded manifest and
assignment repair at exact head `f77f5d78` on
`2026-08-02T10:51:16+0200`.

- Decision: `approved`.
- Reviewed scope: only the changes since prior reviewed head `23a01520` that
  repair Finding 1 in SIR-COR-003, SIR-COR-005, SIR-COR-006, Plan, Non-CLI
  Workload Rows, implementation steps 3 and 5-6, post-change proof, and stop
  conditions. The prior authority and all unchanged plan decisions were reused.
- Findings: none. The repair defines one authored simple 231-row exact-path
  workload/completeness manifest, lists all 22 non-CLI paths, derives the
  package's sealed 209-source `docs/` run manifest mechanically from that
  authored subset, and forms eight combined work orders whose disjoint union
  must equal all 231 rows exactly once. Semantic decisions, shared writes,
  apply/recovery, generated indexes, and Git remain parent-owned. No product,
  quality-topology, operations, package-freeze, compatibility, or broad-test
  scope was added.
- Permitted next step: the parent may transition TASK-SIRCON-REP-0001 from
  `proposed` to `ready` in a separate lifecycle patch. Implementation may begin
  only after that transition through the ordinary governed task/worktree lane.
- Validation not run: no migration phase, package/runtime identity check,
  corpus mutation, specialist assignment, docs synchronization, validator
  execution, product test, or broad repository check ran. `git diff --check`
  passed for the committed repair; the documented legacy-contract `docs-sync`
  exception remains applicable until migration installs the shared contract.
- Residual risk: the execution-time immutable package tuple, current-main
  231/209/22 cohort split, and 395 exclusion hashes remain implementation-time
  facts. The existing stop conditions require a halt if any of them drift or if
  the combined work-order and package-subset invariants fail.

## Readiness

SIR-COR-001 through SIR-COR-010 are closed, and the bounded repair resolves the
only readiness finding. Decision: `approved`. The task remains `proposed`; the
parent may apply the separate `proposed -> ready` transition.

## Closeout

Not started.
