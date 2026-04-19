---
id: task-263-run-sir-convert-gateway-cutover-proof-and-security-review
title: Run Sir Convert gateway cutover proof and security review
type: task
status: proposed
priority: high
created: '2026-04-19'
last_updated: '2026-04-19'
related:
  - docs/backlog/epics/epic-09-gateway-cutover-and-internal-access-contract-for-sir-convert-a-lot.md
  - docs/backlog/stories/story-33-sir-convert-gateway-fronted-public-access-and-internal-lane-migration.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
labels:
  - proof
  - security
  - gateway
  - public-edge
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the final cutover verification and security review before declaring the
Gateway-fronted Sir Convert access model complete.

## PR Scope

- Verify public anonymous deny behavior.
- Verify that direct public web access to Sir Convert is disabled or
  fail-closed before the final live proof window.
- Re-enable the intended public edge during final live testing and prove that
  only the approved Gateway/internal/operator lanes work.
- Verify Gateway-authenticated product flow.
- Verify direct internal service call flow.
- Verify local operator tunnel/offload flow.
- Verify docs/OpenAPI/metrics/readiness public exposure posture.
- Verify unknown-host/default-host fail-closed behavior.
- Capture durable report artifacts.
- Write proof artifacts under
  `build/verification/gateway-cutover-sir-convert/`.
- Tie public-edge checks to the existing `hemma-deploy-and-verify` proof
  contract where possible.

## Deliverables

- [ ] Public/internal/operator proof report.
- [ ] Pre-final public-web isolation proof showing direct
  `convert.hule.education` access is disabled or fail-closed before final live
  proof.
- [ ] Final public-edge re-enable proof showing the intended Gateway-backed
  public path works while direct non-Gateway traffic remains fail-closed.
- [ ] Security review findings or explicit no-finding record.
- [ ] Final cutover report artifacts.
- [ ] Canonical `report.md` and `report.json` under
  `build/verification/gateway-cutover-sir-convert/`.
- [ ] Handoff/current docs update.

## Acceptance Criteria

- [ ] Public deny, Gateway allow, internal allow, and operator allow are all
  proven.
- [ ] Final live proof includes deliberate re-enable of the intended public
  edge, not an accidental always-on direct public Sir Convert surface.
- [ ] Proof commands and artifacts are reproducible, not narrative-only.
- [ ] No high-severity review finding remains unresolved.
- [ ] Rollback path is documented.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
