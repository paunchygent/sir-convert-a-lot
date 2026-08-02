---
type: task
id: TASK-SIRCON-REP-0006
title: Repair the Hemma HWE 6.17 package state in an idle window with DKMS evidence and stop rules
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- '- [ ] The repair is attempted only when all of the following are true: - no live Task 174 bundle process/container exists
  - no live Qwen training process/container exists - `/srv/scratch` is writable - Docker is healthy'
- '- [ ] Pre-repair evidence is captured before the first mutating repair command: - `dpkg --audit` - package states for `linux-*`
  and `dkms` - `dkms status` - current `amdgpu-dkms` build log tail'
- '- [ ] First repair step is: - `dpkg --configure --pending`'
- '- [ ] `apt-get -f install` is used only if package dependency repair is explicitly required after the first `dpkg` pass.'
- '- [ ] If the repair stops specifically in DKMS for `6.17.0-14-generic`, the operator does not loop `dpkg` blindly and instead
  captures the DKMS failure evidence before any targeted `dkms autoinstall` attempt.'
- '- [ ] Success means: - `dpkg --audit` is clean - no `iU`, `iF`, or `it` package states remain for the pending `6.17` HWE
  line - `dkms status` is consistent with the repaired package state'
- '- [ ] Failure is still acceptable if it is bounded and documented: - the exact failing DKMS step is captured - package
  state after the attempt is recorded - no uncontrolled repeated repair loop is performed'
retired_ids:
- task-177-repair-the-hemma-hwe-6-17-package-state-in-an-idle-window-with-dkms-evidence-and-stop-rules
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Recover Hemma from the current interrupted HWE `6.17.0-14` package state in one
strict idle maintenance window, using evidence from the live host and the
documented `dpkg` / `apt-get` / `dkms` recovery surfaces instead of ad hoc
repair attempts during active Qwen workload execution.

### Problem Statement

Hemma is currently booted on the stable `6.14.0-37-generic` kernel, but the
package manager is left in an interrupted transition toward the newer HWE
`6.17.0-14` line.

Current audited state:

- running kernel:
  - `6.14.0-37-generic`
- `dpkg --audit` currently reports:
  - unpacked but not configured:
    - `linux-generic-hwe-24.04`
    - `linux-headers-generic-hwe-24.04`
  - half-configured:
    - `linux-headers-6.17.0-14-generic`
  - trigger pending:
    - `linux-image-6.17.0-14-generic`
- the interrupted configuration path is specifically:
  - `linux-headers-6.17.0-14-generic`
  - `/etc/kernel/header_postinst.d/dkms`
  - `amdgpu-dkms`
  - module signing via `kmodsign`

The previous repair attempt was unsafe because it resumed kernel-header DKMS
work while a live Task 174 bundle build was still active and while the host had
already shown `/srv/scratch` read-only failures. This task exists to prevent
that mistake from being repeated.

### PR Scope

- Capture deterministic pre-repair evidence for:
  - `dpkg`
  - `apt`
  - pending HWE kernel packages
  - `dkms`
  - the current `amdgpu-dkms` build log
- Define and execute one strictly ordered repair path only when the host is
  idle and no active Qwen bundle/training workload is running.
- Use the documented command order:
  - `dpkg --configure --pending`
  - `apt-get -f install` only if dependency repair is required
  - `dkms autoinstall -k 6.17.0-14-generic` only if the package repair stops
    specifically in DKMS module build/install for the pending kernel
- Keep the running `6.14` kernel as the active operational baseline during the
  repair.
- Explicitly forbid:
  - `apt upgrade`
  - `dist-upgrade`
  - opportunistic package work during active Qwen jobs
  - kernel-switch or reboot into `6.17` as part of this task

### Deliverables

- [ ] One deterministic pre-repair evidence bundle for the package state.
- [ ] One idle-window runbook sequence for the repair.
- [ ] One completed repair or one bounded stop-state that identifies the exact
  blocking DKMS failure surface.
- [ ] One deterministic post-repair evidence bundle.
- [ ] One docs update that records the exact stop rules for future package
  maintenance on Hemma.

### Acceptance Criteria

- [ ] The repair is attempted only when all of the following are true:
  - no live Task 174 bundle process/container exists
  - no live Qwen training process/container exists
  - `/srv/scratch` is writable
  - Docker is healthy
- [ ] Pre-repair evidence is captured before the first mutating repair command:
  - `dpkg --audit`
  - package states for `linux-*` and `dkms`
  - `dkms status`
  - current `amdgpu-dkms` build log tail
- [ ] First repair step is:
  - `dpkg --configure --pending`
- [ ] `apt-get -f install` is used only if package dependency repair is
  explicitly required after the first `dpkg` pass.
- [ ] If the repair stops specifically in DKMS for `6.17.0-14-generic`, the
  operator does not loop `dpkg` blindly and instead captures the DKMS failure
  evidence before any targeted `dkms autoinstall` attempt.
- [ ] Success means:
  - `dpkg --audit` is clean
  - no `iU`, `iF`, or `it` package states remain for the pending `6.17` HWE
    line
  - `dkms status` is consistent with the repaired package state
- [ ] Failure is still acceptable if it is bounded and documented:
  - the exact failing DKMS step is captured
  - package state after the attempt is recorded
  - no uncontrolled repeated repair loop is performed

### Proposed Repair Procedure

### Precondition Gate

Do not start until:

- Task 174 bundle materialization is complete or intentionally stopped
- no active Qwen training run is consuming GPU/IO resources
- `/srv/scratch` has recovered from any read-only or mount-failure state
- Docker responds normally to read-only status commands

### Pre-Repair Evidence

Capture and persist:

- `uname -r`
- `dpkg --audit`
- `dpkg -l | rg "linux-(headers|image|modules|generic-hwe)|dkms"`
- `dkms status`
- `tail` or archived copy of:
  - `/var/lib/dkms/amdgpu/6.16.13-2278356.24.04/build/make.log`
- relevant package logs:
  - `/var/log/dpkg.log`
  - `/var/log/apt/history.log`
  - readable excerpts from `/var/log/apt/term.log`

### Repair Order

1. `sudo dpkg --configure --pending`
1. If `dpkg` reports broken dependencies rather than a DKMS-only failure:
   - `sudo apt-get -f install`
1. If the failure is specifically the DKMS path for the pending kernel:
   - inspect `dkms status`
   - inspect the `amdgpu-dkms` build log
   - then, and only then:
     - `sudo dkms autoinstall -k 6.17.0-14-generic`
1. Re-run:
   - `sudo dpkg --configure --pending`

### Stop Rules

Stop immediately and record evidence if any of the following happen:

- `/srv/scratch` becomes read-only again
- Docker health degrades while the repair is in progress
- the DKMS path hangs or fails again without a clearer diagnostic
- the running `6.14` kernel appears to become unstable

Do not:

- keep retrying `dpkg` in a loop
- start unrelated package updates
- reboot into `6.17`

### Sources

These are the normative sources for the repair posture:

- `dpkg(1)` Ubuntu Noble manpage:
  - `https://manpages.ubuntu.com/manpages/noble/man1/dpkg.1.html`
- `apt-get(8)` Ubuntu Noble manpage:
  - `https://manpages.ubuntu.com/manpages/noble/en/man8/apt-get.8.html`
- `dkms(8)` Ubuntu Noble manpage:
  - `https://manpages.ubuntu.com/manpages/noble/en/man8/dkms.8.html`

### Validation

- [ ] `pdm run run-hemma -- uname -r`
- [ ] `pdm run run-hemma -- sudo -n dpkg --audit`
- [ ] `pdm run run-hemma -- dpkg -l | rg "linux-(headers|image|modules|generic-hwe)|dkms"`
- [ ] `pdm run run-hemma -- sudo -n dkms status`
- [ ] `pdm run run-hemma -- sudo -n apt-get check`
- [ ] Persist pre/post evidence paths in docs or handoff state

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
