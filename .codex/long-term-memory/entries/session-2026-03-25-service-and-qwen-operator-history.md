---
type: agent_session_long_term_memory_entry
id: sir-convert-a-lot-session-2026-03-25-service-and-qwen-operator-history
status: active
created: '2026-04-16'
last_updated: '2026-04-16'
---

# March 2026 Service And Qwen Operator History

## Scope

This entry preserves durable March 2026 service, local runtime, service-image,
and Qwen Task 101 operator context compacted out of `.codex/handoff.md` during
`TASK-0046`. Use this as session history only; current operator truth belongs
in `docs/backlog/current.md`, the active task/story docs, and the Task 101
ledger.

## Local Dev Runtime Slice

`task-250-add-a-cpu-only-local-docker-dev-profile-for-macbook-service-debugging`
landed a CPU-only local Docker dev profile:

- `compose.local.yaml` for the explicit local service surface.
- `Dockerfile.local` with standard CPU torch wheels instead of ROCm wheels.
- `scripts/devops/dev-compose.sh` targeting the local CPU compose surface.
- `scripts/sir_convert_a_lot/service_local.py` exposing `local_cpu_dev`.
- Docs and skills framing Hemma/public as default integration lanes and local
  `:8085` as debug-only Docker infrastructure.

Focused verification passed for the slice, including local compose config,
local image build, service-local tests, docs validation, ruff, and mypy.

## Trusted Bundle Service Slice

`task-249-add-trusted-app-bundle-mode-for-internal-html-to-pdf-exports` landed
and was post-review hardened:

- persisted `owner_auth_lane` and `owner_api_key_scope` on v2 jobs,
- enforced cross-lane ownership checks on job lifecycle/read/artifact/event
  routes,
- narrowed the internal API key back to job-lifecycle surfaces,
- made idempotency replay stable across public and internal key rotation by
  using persisted lane scope,
- made `verify_hemma_v2_conversions.py` fail closed when
  `--internal-api-key` is missing.

The remaining closeout at the time was Hemma proof: deploy the updated service,
run the trusted-bundle verifier with public and internal keys, and capture that
trusted bundled local images render only through the internal lane.

## Qwen Task 101 Operator State

The active research lane was Epic 08 Qwen Swedish language expansion on Hemma,
with Story 31 as the mechanism lane and Story 32 as the experiment governance
surface. The live ledger was:

`docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md`

Key durable facts preserved from the old handoff:

- `RULE-095` governed the Qwen package split and hot-path LoC cap.
- `RULE-096` governed experiment taxonomy, one-question-per-run discipline,
  one-factor-at-a-time interpretation, the promotion ladder, and the single
  ledger contract.
- `T221` closed as negative recreated-control provenance evidence.
- `T225-T226` completed the exact parity contract and committed parity probe.
- `T219` was recorded as negative bounded evidence without promotion.
- `T228-T245` progressively narrowed the mechanism lane, with the fixed
  winner-specific `layer15_out_0p5` attenuation multiply classified as
  `multiply_not_causal`.
- `T246` became the next diagnosis-only mechanism slice to split the
  fp32-scaled layer-15 output result from the final emitted tensor before any
  new stabilizer family.
- `T217` stayed blocked until a mechanism candidate passed the local promotion
  gate.

Future active Qwen runs must declare the Story 32 experiment spec before being
treated as comparable evidence and must avoid causal claims across runs that
changed multiple factors at once.

## Hemma Bind-Root Contract

`T242` established the permanent Hemma bind-root contract for Qwen Docker
runtimes. Before new Hemma Qwen runs, use:

- `pdm run run-hemma -- pdm run qwen-docker-bind-roots status`
- `pdm run run-hemma -- pdm run qwen-docker-bind-roots probe`

The canonical storage truth remains `/srv/scratch/...`, while Docker must use
`/home/paunchygent/.data/sir-convert-a-lot/{build,cache}` as the effective bind
source.

## Service Image Layering Note

A March 18 Hemma deploy attempt for the Exam.net DOCX paragraph-repair service
patch was intentionally aborted when the root service image rebuilt too much of
the dependency stack. The old live service was left healthy. `task-239` became
the canonical next slice for service-image redesign: split stable dependency
layers from the thin app layer, avoid installing CUDA-flavoured torch packages
only to replace them with ROCm wheels, keep the runtime copy surface narrow, and
verify Hemma GPU runtime directly inside the container.

## Historical Validation Evidence

The old handoff recorded passing evidence for ML tests, typecheck, formatting,
lint, docs validation, Qwen parity/stability CLI help, multiple Hemma
Story 31 stability-lab runs, service image contract tests, compose checks, and
the trusted bundle service slice. Treat those commands as historical evidence,
not as the current closeout contract for new changes.
