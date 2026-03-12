---
id: 'task-145-repair-hemma-kernel-package-drift-and-disable-auto-applied-tailscale-updates'
title: 'Repair Hemma kernel package drift and disable auto-applied tailscale updates'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-03-12'
last_updated: '2026-03-12'
related:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-144-harden-task-101-bundle-against-unreadable-frozen-freeze-summary.md
labels: []
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Recover Hemma from the long-lived interrupted `dpkg` state by removing the
stale GA `6.8` kernel line, standardizing the host on the active HWE kernel
line, and disabling Tailscale auto-apply updates so background package actions
do not reopen apt transactions on the production GPU host.

## PR Scope

- Capture pre-repair package/runtime evidence from Hemma.
- Disable Tailscale auto-apply updates while preserving manual update
  visibility.
- Remove the stale GA `linux-generic` / `6.8.0-94` package line that keeps
  retriggering the interrupted DKMS path.
- Repair `dpkg` / `apt` and verify the host is clean on HWE only.
- Record the exact recovery evidence and follow-on operator policy.

## Deliverables

- [ ] Hemma package-manager state repaired (`dpkg --audit` clean).
- [ ] Tailscale auto-apply disabled on Hemma.
- [ ] Stale GA `6.8` kernel package line removed.
- [ ] Verification evidence captured in session handoff.

## Acceptance Criteria

- [x] `apt-get check` succeeds on Hemma.
- [x] `dpkg --audit` returns no interrupted packages.
- [x] `tailscale debug prefs` reports `AutoUpdate.Apply=false`.
- [x] Hemma remains on the HWE kernel line after repair.

## Validation

- [x] `pdm run run-hemma -- uname -r`
- [x] `pdm run run-hemma -- sudo -n dpkg --audit`
- [x] `pdm run run-hemma -- sudo -n apt-get check`
- [x] `pdm run run-hemma -- tailscale debug prefs`
- [x] `pdm run run-hemma -- tailscale version`

## Outcome

`T145` repaired the host-level package-manager incident on Hemma.

- Disabled Tailscale auto-apply updates while keeping update checks enabled.
- Removed the stale GA `linux-generic` / `6.8.0-94` transaction that had been
  left unpacked and repeatedly re-entered by later apt actions.
- Purged the remaining GA `6.8.0-90` kernel payload so the host now carries
  only the active HWE `6.14` kernel line.
- Verified that `dpkg --audit` is clean, `apt-get check` is clean, and
  `tailscale` is configured with `AutoUpdate.Apply=false`.
- A follow-on Task 101 bundle retry moved through two later fixes after this
  host repair:
  - the Hemma repo clone was updated to include `T144`
  - the frozen pilot root permissions were normalized in `T146`
- The current remaining Task 101 blocker is therefore no longer host package
  drift; it is `/srv/scratch` exhaustion during bundle materialization, tracked
  in `T147`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
