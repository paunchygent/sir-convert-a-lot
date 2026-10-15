"""Challenge legacy cleanup and tier adapters without touching the Hemma host."""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import (
    hemma_scratch_maintenance_runtime as maintenance,
)
from scripts.sir_convert_a_lot.devops import (
    hemma_scratch_policy_runtime as policy,
)
from scripts.sir_convert_a_lot.devops import (
    hemma_scratch_timer_runtime as timer,
)
from scripts.sir_convert_a_lot.devops import (
    run_hemma_scratch_policy as cli,
)
from scripts.sir_convert_a_lot.devops import (
    run_hemma_storage_remediation as storage_cli,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_reporting import build_timer_settings
from scripts.sir_convert_a_lot.devops.hemma_storage_contracts import (
    DEFAULT_HOT_ARCHIVE_ROOT,
    DEFAULT_HOT_BUILD_ROOT,
    DEFAULT_HOT_QWEN_DATA_ROOT,
    validate_hot_destination,
)

STORAGE_MODULES = (
    "scripts.sir_convert_a_lot.devops.hemma_storage_runtime",
    "scripts.sir_convert_a_lot.ml.qwen.common.storage",
)


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_legacy_cleanup_refuses_before_any_command(
    module_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("command ran"))
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        module.cleanup_non_active_docker_state()


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_storage_cleanup_request_cannot_partially_migrate(
    module_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    settings_type = getattr(module, "HemmaStorageSettings", None) or module.StorageSettings
    settings = settings_type(
        repo_root=tmp_path / "repo",
        repo_build_root=tmp_path / "repo/build",
        scratch_build_root=tmp_path / "hot/build",
        old_qwen_data_root=tmp_path / "old/data",
        new_qwen_data_root=tmp_path / "hot/data",
        migrate_repo_build=True,
        migrate_qwen_data=True,
        cleanup_docker_state=True,
    )
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("probe ran"))
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        module.run_storage_remediation(settings)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", ["remediate", "maintain", "install-timer"])
def test_obsolete_cli_flag_cannot_create_output_or_units(command: str, tmp_path: Path) -> None:
    output = tmp_path / "build/verification/refused"
    with pytest.raises(SystemExit) as exc:
        cli.main([command, "--prune-docker-state", "--output-root", str(output)])
    assert exc.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_direct_scratch_cleanup_requests_refuse_before_probing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for module in (policy, maintenance):
        monkeypatch.setattr(module, "scratch_free_bytes", lambda *_: pytest.fail("probe ran"))
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        policy.run_scratch_remediation(source_paths=[], prune_docker_state=True)
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        maintenance.run_scratch_maintenance(prune_docker_state=True)


def test_obsolete_timer_setting_refuses_before_host_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = build_timer_settings(cli.build_parser().parse_args(["install-timer"]))
    settings = replace(settings, unit_dir=tmp_path / "units", prune_docker_state=True)
    monkeypatch.setattr(timer, "_user_linger_enabled", lambda *_: pytest.fail("host probe ran"))
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        timer.render_service_unit(settings)
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        timer.render_timer_unit(settings)
    with pytest.raises(SystemExit, match="shared weekly hemma-docker-cleanup"):
        timer.install_scratch_timer(settings, enable_linger=True)
    assert not settings.unit_dir.exists()


@pytest.mark.parametrize("destination", ["/srv/storage/sir/archive", "/srv/scratch/sir/build"])
def test_nonvisual_primary_destinations_reject_retired_tiers(destination: str) -> None:
    with pytest.raises(SystemExit, match="requires Hot owner storage"):
        validate_hot_destination(Path(destination))


def test_backup_destination_alias_is_also_refused(tmp_path: Path) -> None:
    alias = tmp_path / "archive"
    alias.symlink_to("/srv/storage/sir/archive")
    with pytest.raises(SystemExit, match="requires Hot owner storage"):
        validate_hot_destination(alias)


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_existing_build_symlink_is_never_retargeted_without_backing_migration(
    module_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    settings_type = getattr(module, "HemmaStorageSettings", None) or module.StorageSettings
    old = tmp_path / "legacy-build"
    old.mkdir()
    (old / "active-proof").write_bytes(b"preserve")
    logical = tmp_path / "build"
    logical.symlink_to(old)
    destination = tmp_path / "hot-build"
    settings = settings_type(
        repo_root=tmp_path,
        repo_build_root=logical,
        scratch_build_root=destination,
        old_qwen_data_root=tmp_path / "legacy-data",
        new_qwen_data_root=tmp_path / "hot-data",
        migrate_repo_build=True,
        migrate_qwen_data=False,
        cleanup_docker_state=False,
    )
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("probe ran"))
    with pytest.raises(SystemExit, match="parent must first migrate and verify"):
        module.run_storage_remediation(settings)
    assert logical.resolve() == old
    assert (logical / "active-proof").read_bytes() == b"preserve"
    assert not destination.exists()


def test_new_defaults_keep_nonvisual_output_on_hot_and_logical_paths_stable() -> None:
    for module_name in STORAGE_MODULES:
        module = importlib.import_module(module_name)
        assert module.DEFAULT_SCRATCH_BUILD_ROOT == DEFAULT_HOT_BUILD_ROOT
        assert module.DEFAULT_NEW_QWEN_DATA_ROOT == DEFAULT_HOT_QWEN_DATA_ROOT
        assert module.DEFAULT_REPO_BUILD_ROOT == Path(
            "/home/paunchygent/apps/sir-convert-a-lot/build"
        )
    assert policy.DEFAULT_STORAGE_ARCHIVE_ROOT == DEFAULT_HOT_ARCHIVE_ROOT
    for path in (DEFAULT_HOT_BUILD_ROOT, DEFAULT_HOT_ARCHIVE_ROOT, DEFAULT_HOT_QWEN_DATA_ROOT):
        assert path.is_relative_to("/home/paunchygent/.local/share/sir-convert-a-lot")
        assert ".orchestration" not in path.parts
    _, settings = storage_cli._parse_args([])
    assert settings.cleanup_docker_state is False


def test_docker_visible_build_path_is_preserved_when_backing_default_changes() -> None:
    from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_contracts import default_settings

    build_root = default_settings().bind_roots[0]
    assert build_root.canonical_root == DEFAULT_HOT_BUILD_ROOT
    assert build_root.home_root == Path("/home/paunchygent/.data/sir-convert-a-lot/build")


def test_archive_refuses_backup_before_touching_source(tmp_path: Path) -> None:
    source = tmp_path / "scratch/active-proof"
    source.mkdir(parents=True)
    (source / "proof").write_bytes(b"keep")
    with pytest.raises(SystemExit, match="requires Hot owner storage"):
        policy.archive_scratch_paths(
            [source],
            scratch_root=tmp_path / "scratch",
            storage_archive_root=Path("/srv/storage/legacy/archive"),
        )
    assert not source.is_symlink()
    assert (source / "proof").read_bytes() == b"keep"


@pytest.mark.parametrize("tier", ["/srv/storage/sir/archive", "/srv/scratch/sir/archive"])
def test_archive_refuses_descendant_alias_before_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tier: str
) -> None:
    scratch = tmp_path / "scratch"
    source = scratch / "sir/build/verification/old-proof"
    source.mkdir(parents=True)
    (source / "proof").write_bytes(b"keep")
    archive = tmp_path / "hot/archive"
    (archive / "sir/build").mkdir(parents=True)
    (archive / "sir/build/verification").symlink_to(tier)
    monkeypatch.setattr(policy, "migrate_tree_to_tier", lambda *_: pytest.fail("migration ran"))
    with pytest.raises(SystemExit, match="requires Hot owner storage"):
        policy.archive_scratch_paths([source], scratch_root=scratch, storage_archive_root=archive)
    assert not source.is_symlink()
    assert (source / "proof").read_bytes() == b"keep"


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
@pytest.mark.parametrize("collision", ["bytes", "file-directory", "dangling-link"])
def test_migration_refuses_late_collision_before_any_payload_mutation(
    module_name: str, collision: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "a-new").write_bytes(b"new")
    (source / "b-identical").write_bytes(b"same")
    (destination / "b-identical").write_bytes(b"same")
    (source / "z-nested").mkdir()
    (destination / "z-nested").mkdir()
    payload = source / "z-nested/checkpoint"
    target = destination / "z-nested/checkpoint"
    payload.write_bytes(b"source")
    if collision == "bytes":
        target.write_bytes(b"target")
    elif collision == "file-directory":
        target.mkdir()
    else:
        target.symlink_to(tmp_path / "missing")
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("sudo ran"))
    with pytest.raises(SystemExit, match="collision"):
        module._migrate_tree(source, destination)
    assert payload.read_bytes() == b"source"
    assert (source / "a-new").read_bytes() == b"new"
    assert (source / "b-identical").read_bytes() == b"same"
    assert not (destination / "a-new").exists()
    assert (destination / "b-identical").read_bytes() == b"same"
    if collision == "bytes":
        assert target.read_bytes() == b"target"
    elif collision == "file-directory":
        assert target.is_dir()
    else:
        assert target.is_symlink()
        assert not target.exists()


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_migration_merges_identical_files_and_preserves_new_symlinks(
    module_name: str, tmp_path: Path
) -> None:
    module = importlib.import_module(module_name)
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    for root in (source, destination):
        (root / "nested").mkdir()
        (root / "nested/same").write_bytes(b"same")
    (source / "new").write_bytes(b"new")
    (source / "link").symlink_to("new")
    module._migrate_tree(source, destination)
    assert not source.exists()
    assert (destination / "nested/same").read_bytes() == b"same"
    assert (destination / "link").is_symlink()
    assert (destination / "link").read_bytes() == b"new"


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_sudo_fallback_cannot_bypass_collision_preflight(
    module_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    source, destination = tmp_path / "source", tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "checkpoint").write_bytes(b"source")
    (destination / "checkpoint").write_bytes(b"target")
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("sudo ran"))
    with pytest.raises(SystemExit, match="collision"):
        module._sudo_rsync_tree(source=source, destination=destination)
    assert (source / "checkpoint").read_bytes() == b"source"
    assert (destination / "checkpoint").read_bytes() == b"target"


def test_archive_batch_preflights_late_collision_before_moving_first_tree(tmp_path: Path) -> None:
    scratch, archive = tmp_path / "scratch", tmp_path / "hot/archive"
    for name in ("first", "last"):
        (scratch / name).mkdir(parents=True)
        (scratch / name / "proof").write_bytes(b"source")
    (archive / "last").mkdir(parents=True)
    (archive / "last/proof").write_bytes(b"target")
    with pytest.raises(SystemExit, match="collision"):
        policy.archive_scratch_paths(
            [scratch / "first", scratch / "last"],
            scratch_root=scratch,
            storage_archive_root=archive,
        )
    assert not (scratch / "first").is_symlink()
    assert (scratch / "first/proof").read_bytes() == b"source"
    assert (scratch / "last/proof").read_bytes() == b"source"
    assert (archive / "last/proof").read_bytes() == b"target"
    assert not (archive / "first").exists()


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_storage_run_preflights_data_collision_before_build_migration(
    module_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    settings_type = getattr(module, "HemmaStorageSettings", None) or module.StorageSettings
    settings = settings_type(
        repo_root=tmp_path,
        repo_build_root=tmp_path / "build",
        scratch_build_root=tmp_path / "hot/build",
        old_qwen_data_root=tmp_path / "old-data",
        new_qwen_data_root=tmp_path / "hot/data",
        migrate_repo_build=True,
        migrate_qwen_data=True,
        cleanup_docker_state=False,
    )
    for root in (
        settings.repo_build_root,
        settings.old_qwen_data_root,
        settings.new_qwen_data_root,
    ):
        root.mkdir(parents=True)
    (settings.repo_build_root / "proof").write_bytes(b"keep")
    (settings.old_qwen_data_root / "checkpoint").write_bytes(b"source")
    (settings.new_qwen_data_root / "checkpoint").write_bytes(b"target")
    monkeypatch.setattr(module, "run_checked", lambda *_a, **_kw: pytest.fail("command ran"))
    with pytest.raises(SystemExit, match="collision"):
        module.run_storage_remediation(settings)
    assert not settings.repo_build_root.is_symlink()
    assert (settings.repo_build_root / "proof").read_bytes() == b"keep"
    assert (settings.old_qwen_data_root / "checkpoint").read_bytes() == b"source"
    assert (settings.new_qwen_data_root / "checkpoint").read_bytes() == b"target"
    assert not settings.scratch_build_root.exists()


def test_archive_accepts_hot_descendant_alias_and_keeps_logical_path(tmp_path: Path) -> None:
    scratch, archive = tmp_path / "scratch", tmp_path / "hot/archive"
    source = scratch / "sir/build/verification/proof"
    source.mkdir(parents=True)
    (source / "payload").write_bytes(b"keep")
    backing = tmp_path / "hot/proofs"
    backing.mkdir(parents=True)
    (archive / "sir/build").mkdir(parents=True)
    (archive / "sir/build/verification").symlink_to(backing)
    result = policy.archive_scratch_paths(
        [source], scratch_root=scratch, storage_archive_root=archive
    )
    assert source.is_symlink()
    assert source.readlink() == archive / "sir/build/verification/proof"
    assert source.resolve() == backing / "proof"
    assert (source / "payload").read_bytes() == b"keep"
    assert result[0].archive_path == (archive / "sir/build/verification/proof").as_posix()
