"""Tests for recurring Hemma scratch maintenance and timer management.

Purpose:
    Verify the Hemma scratch maintenance selector, runtime orchestration, retired-timer uninstall,
    and CLI reporting without touching real Hemma storage or systemd state.

Relationships:
    - Covers `hemma_scratch_maintenance_selection.py`.
    - Covers `hemma_scratch_maintenance_runtime.py`.
    - Covers `hemma_scratch_timer_runtime.py`.
    - Covers the Hemma scratch maintenance branches in `run_hemma_scratch_policy.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import hemma_scratch_timer_runtime as timer_runtime
from scripts.sir_convert_a_lot.devops import run_hemma_scratch_policy
from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_contracts import (
    DEFAULT_SERVICE_NAME,
    DEFAULT_TIMER_NAME,
    CandidateParent,
    MaintenanceCandidate,
    ScratchMaintenanceReport,
    ScratchTimerStatusReport,
    ScratchTimerUninstallReport,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime import (
    run_scratch_maintenance,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_selection import (
    select_maintenance_candidates,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_runtime import (
    ArchivedScratchPath,
)


def test_select_maintenance_candidates_skips_kept_recent_and_protected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hemma scratch maintenance keeps the newest roots and protected RCA artifacts."""
    scratch_root = tmp_path / "scratch"
    storage_archive_root = tmp_path / "storage" / "archive"
    candidate_root = scratch_root / "runs"
    old_root = candidate_root / "old-run"
    keep_root = candidate_root / "keep-run"
    protected_root = candidate_root / "protected-run"
    for path in (old_root, keep_root, protected_root):
        artifact = path / "artifact.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(path.name, encoding="utf-8")
    now = 1_710_000_000
    os.utime(old_root, (now - 48 * 3600, now - 48 * 3600))
    os.utime(keep_root, (now, now))
    os.utime(protected_root, (now - 72 * 3600, now - 72 * 3600))

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_selection.directory_size_bytes",
        lambda path: 100 if path == old_root else 50,
    )

    candidates = select_maintenance_candidates(
        scratch_root=scratch_root,
        storage_archive_root=storage_archive_root,
        candidate_parents=[
            CandidateParent(
                root=candidate_root,
                category="runs",
                keep_most_recent=1,
            )
        ],
        protected_paths=(protected_root,),
        active_container_names=[],
        candidate_min_age_hours=12.0,
    )

    assert [candidate.source_path for candidate in candidates] == [old_root.as_posix()]


def test_run_scratch_maintenance_blocks_when_qwen_containers_are_active(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hemma scratch maintenance should not archive anything while a Qwen workload is active."""
    scratch_root = tmp_path / "scratch"
    scratch_root.mkdir(parents=True)
    block_file = scratch_root / ".block"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.scratch_free_bytes",
        lambda _: 10,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.active_qwen_container_names",
        lambda: ["qwen-fallback-accumulation"],
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.select_maintenance_candidates",
        lambda **_: pytest.fail("selection should not run while active containers exist"),
    )

    report = run_scratch_maintenance(
        scratch_root=scratch_root,
        storage_archive_root=tmp_path / "storage" / "archive",
        runs_root=tmp_path / "runs",
        verification_root=tmp_path / "verification",
        block_file_path=block_file,
        required_free_bytes=20,
        target_free_bytes=30,
        candidate_min_age_hours=12.0,
        keep_most_recent=2,
        prune_docker_state=False,
    )

    assert report.status == "blocked"
    assert report.blocked_reason == "active-qwen-containers"
    assert report.archived_paths == []
    assert report.pruned_docker_state is False


def test_run_scratch_maintenance_archives_only_until_target_headroom(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hemma scratch maintenance archives enough candidates to reach target headroom."""
    free_bytes_values = iter([10, 120, 120])
    first = MaintenanceCandidate(
        category="runs",
        source_path=(tmp_path / "scratch" / "runs" / "cold-a").as_posix(),
        archive_path=(tmp_path / "storage" / "archive" / "cold-a").as_posix(),
        size_bytes=110,
        age_hours=24.0,
    )
    second = MaintenanceCandidate(
        category="runs",
        source_path=(tmp_path / "scratch" / "runs" / "cold-b").as_posix(),
        archive_path=(tmp_path / "storage" / "archive" / "cold-b").as_posix(),
        size_bytes=90,
        age_hours=24.0,
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.scratch_free_bytes",
        lambda _: next(free_bytes_values),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.active_qwen_container_names",
        lambda: [],
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.select_maintenance_candidates",
        lambda **_: [first, second],
    )

    archived_calls: list[list[Path]] = []

    def fake_archive(
        source_paths: list[Path],
        *,
        scratch_root: Path,
        storage_archive_root: Path,
    ) -> list[ArchivedScratchPath]:
        archived_calls.append(source_paths)
        return [
            ArchivedScratchPath(
                source_path=source_paths[0].as_posix(),
                archive_path=(storage_archive_root / source_paths[0].name).as_posix(),
                size_bytes=110,
            )
        ]

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime.archive_scratch_paths",
        fake_archive,
    )

    report = run_scratch_maintenance(
        scratch_root=tmp_path / "scratch",
        storage_archive_root=tmp_path / "storage" / "archive",
        runs_root=tmp_path / "runs",
        verification_root=tmp_path / "verification",
        block_file_path=tmp_path / "block",
        required_free_bytes=20,
        target_free_bytes=100,
        candidate_min_age_hours=12.0,
        keep_most_recent=2,
        prune_docker_state=False,
    )

    assert archived_calls == [[Path(first.source_path)]]
    assert report.status == "archived"
    assert report.archived_paths[0].source_path == first.source_path


TIMER = DEFAULT_TIMER_NAME
SERVICE = DEFAULT_SERVICE_NAME
RETIRED_STATE = {"LoadState": "not-found", "UnitFileState": "", "ActiveState": "inactive"}


class FakeUserSystemd:
    """A `systemctl --user` stand-in at the subprocess boundary.

    `show` reports `states`; `fail_verbs` makes a verb exit 1 with a bus error;
    `sticky` keeps a unit's state after disable and reload, as a unit that
    refuses to go away would.
    """

    def __init__(self, unit_dir: Path, states: dict[str, dict[str, str]]) -> None:
        self.unit_dir = unit_dir
        self.states = states
        self.fail_verbs: set[str] = set()
        self.sticky: dict[str, dict[str, str]] = {}
        self.calls: list[list[str]] = []

    def run(
        self, command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        assert command[:2] == ["systemctl", "--user"], command
        verb, args = command[2], command[3:]
        if verb in self.fail_verbs:
            return subprocess.CompletedProcess(command, 1, "", "Failed to connect to bus")
        if verb == "show":
            state = self.states.get(args[-1], RETIRED_STATE)
            stdout = "\n".join(f"{key}={value}" for key, value in state.items())
            return subprocess.CompletedProcess(command, 0, stdout, "")
        if verb == "disable":
            for name in args[1:]:
                state = self.states[name]
                state["UnitFileState"] = "disabled"
                if state["ActiveState"] != "failed":
                    state["ActiveState"] = "inactive"
        if verb == "daemon-reload":
            for name, state in list(self.states.items()):
                if not (self.unit_dir / name).exists():
                    # systemd keeps a failed unit loaded until reset-failed.
                    self.states[name] = {**RETIRED_STATE, "ActiveState": state["ActiveState"]}
            self.states.update({name: dict(state) for name, state in self.sticky.items()})
        if verb == "reset-failed":
            for name in args:
                self.states[name] = dict(RETIRED_STATE)
        return subprocess.CompletedProcess(command, 0, "", "")


def _loaded(active: str = "inactive", enabled: str = "enabled") -> dict[str, str]:
    return {"LoadState": "loaded", "UnitFileState": enabled, "ActiveState": active}


def _install_fake(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, states: dict[str, dict[str, str]]
) -> FakeUserSystemd:
    unit_dir = tmp_path / "systemd"
    unit_dir.mkdir()
    for name in (TIMER, SERVICE, "other.service", f"{TIMER}.d"):
        (unit_dir / name).write_text(name, encoding="utf-8")
    fake = FakeUserSystemd(unit_dir, states)
    monkeypatch.setattr(timer_runtime.subprocess, "run", fake.run)
    return fake


def test_uninstall_removes_only_the_retired_units(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The uninstall disables and removes the two retired units and nothing else."""
    fake = _install_fake(
        tmp_path, monkeypatch, {TIMER: _loaded("active"), SERVICE: _loaded("failed", "static")}
    )

    report = timer_runtime.uninstall_scratch_timer(fake.unit_dir)

    assert report.removed_paths == [
        (fake.unit_dir / TIMER).as_posix(),
        (fake.unit_dir / SERVICE).as_posix(),
    ]
    assert sorted(path.name for path in fake.unit_dir.iterdir()) == [
        "other.service",
        f"{TIMER}.d",
    ]
    assert ["systemctl", "--user", "disable", "--now", TIMER, SERVICE] in fake.calls
    assert ["systemctl", "--user", "reset-failed", SERVICE] in fake.calls
    assert report.final_states == {TIMER: RETIRED_STATE, SERVICE: RETIRED_STATE}
    named_units = {
        call[-1] for call in fake.calls if call[2] in ("show", "disable", "reset-failed")
    }
    assert named_units <= {TIMER, SERVICE}


def test_uninstall_is_a_noop_when_the_units_are_already_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second uninstall touches nothing and still proves both units are gone."""
    fake = _install_fake(tmp_path, monkeypatch, {})
    for name in (TIMER, SERVICE):
        (fake.unit_dir / name).unlink()

    report = timer_runtime.uninstall_scratch_timer(fake.unit_dir)

    assert report.removed_paths == []
    assert not any(call[2] in ("disable", "reset-failed") for call in fake.calls)


@pytest.mark.parametrize("verb", ["show", "disable", "daemon-reload", "reset-failed"])
def test_uninstall_fails_on_any_systemctl_error(
    verb: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bus or command failure is never reported as a completed retirement."""
    fake = _install_fake(
        tmp_path, monkeypatch, {TIMER: _loaded(), SERVICE: _loaded("failed", "static")}
    )
    fake.fail_verbs.add(verb)

    with pytest.raises(SystemExit, match="Failed to connect to bus"):
        timer_runtime.uninstall_scratch_timer(fake.unit_dir)
    if verb in ("show", "disable"):
        assert (fake.unit_dir / TIMER).exists()
        assert (fake.unit_dir / SERVICE).exists()


@pytest.mark.parametrize(
    ("unit", "state"),
    [
        (TIMER, _loaded("inactive", "enabled")),
        (TIMER, _loaded("active", "disabled")),
        (SERVICE, _loaded("inactive", "enabled")),
        (SERVICE, _loaded("active", "disabled")),
        (SERVICE, {"LoadState": "not-found", "UnitFileState": "", "ActiveState": "active"}),
    ],
)
def test_uninstall_fails_when_a_unit_survives(
    unit: str, state: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Either unit still enabled, active or loaded after the uninstall is a failure."""
    fake = _install_fake(tmp_path, monkeypatch, {TIMER: _loaded(), SERVICE: _loaded()})
    fake.sticky[unit] = state

    with pytest.raises(SystemExit, match="still present"):
        timer_runtime.uninstall_scratch_timer(fake.unit_dir)


def test_uninstall_cli_has_no_unit_name_options(tmp_path: Path) -> None:
    """The uninstall target set cannot be widened from the command line."""
    for option in ("--timer-name", "--service-name"):
        with pytest.raises(SystemExit) as exc:
            run_hemma_scratch_policy.main(
                ["uninstall-timer", option, "other.service", "--output-root", str(tmp_path / "o")]
            )
        assert exc.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_runner_writes_maintenance_and_timer_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hemma scratch maintenance writes deterministic maintenance and timer artifacts."""
    output_root = tmp_path / "build" / "verification" / "hemma-scratch-maintenance"
    maintenance_report = ScratchMaintenanceReport(
        checked_at="2026-03-16T22:00:00Z",
        scratch_root="/srv/scratch",
        storage_archive_root="/srv/storage/archive",
        required_free_bytes=64,
        target_free_bytes=96,
        candidate_min_age_hours=12.0,
        keep_most_recent=2,
        block_file_path="/srv/scratch/.block",
        block_file_present=False,
        active_container_names=[],
        status="archived",
        blocked_reason=None,
        scratch_free_bytes_before=10,
        scratch_free_bytes_after=120,
        selected_candidates=[
            MaintenanceCandidate(
                category="runs",
                source_path="/srv/scratch/cold-a",
                archive_path="/srv/storage/archive/cold-a",
                size_bytes=99,
                age_hours=36.0,
            )
        ],
        archived_paths=[
            ArchivedScratchPath(
                source_path="/srv/scratch/cold-a",
                archive_path="/srv/storage/archive/cold-a",
                size_bytes=99,
            )
        ],
        pruned_docker_state=False,
        meets_target_after=True,
    )
    uninstall_report = ScratchTimerUninstallReport(
        uninstalled_at="2026-03-16T22:01:00Z",
        unit_dir="/home/user/.config/systemd/user",
        removed_paths=["/home/user/.config/systemd/user/timer.unit"],
        final_states={"timer.unit": {"LoadState": "not-found"}},
    )
    status_report = ScratchTimerStatusReport(
        checked_at="2026-03-16T22:02:00Z",
        service_name="service.unit",
        timer_name="timer.unit",
        unit_dir="/home/user/.config/systemd/user",
        timer_enabled=True,
        timer_active=True,
        lingering_enabled=True,
        timer_list_output="timer output",
    )

    monkeypatch.setattr(
        run_hemma_scratch_policy,
        "run_scratch_maintenance",
        lambda **_: maintenance_report,
    )
    monkeypatch.setattr(
        run_hemma_scratch_policy,
        "uninstall_scratch_timer",
        lambda *_args, **_kwargs: uninstall_report,
    )
    monkeypatch.setattr(
        run_hemma_scratch_policy,
        "status_scratch_timer",
        lambda *_args, **_kwargs: status_report,
    )

    maintain_exit_code = run_hemma_scratch_policy.main(
        ["maintain", "--output-root", output_root.as_posix()]
    )
    uninstall_exit_code = run_hemma_scratch_policy.main(
        ["uninstall-timer", "--output-root", output_root.as_posix()]
    )
    status_exit_code = run_hemma_scratch_policy.main(
        ["status-timer", "--output-root", output_root.as_posix()]
    )

    assert maintain_exit_code == 0
    assert uninstall_exit_code == 0
    assert status_exit_code == 0
    assert (
        json.loads((output_root / "maintain.json").read_text(encoding="utf-8"))["status"]
        == "archived"
    )
    assert "Hemma scratch maintenance Scratch Maintenance" in (
        output_root / "maintain.md"
    ).read_text(encoding="utf-8")
    assert json.loads((output_root / "uninstall-timer.json").read_text(encoding="utf-8"))[
        "removed_paths"
    ] == ["/home/user/.config/systemd/user/timer.unit"]
    assert "timer.unit" in (output_root / "uninstall-timer.md").read_text(encoding="utf-8")
    assert "timer output" in (output_root / "timer-status.md").read_text(encoding="utf-8")
    rendered_output = capsys.readouterr().out
    assert '"status": "archived"' in rendered_output
    assert '"timer_active": true' in rendered_output
