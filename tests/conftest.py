"""Keep pytest temporary directories off the Hemma storage tiers.

On Hemma, TMPDIR is under /srv/scratch. The storage-tier policy refuses real paths under
/srv/scratch and /srv/storage, so fake tier roots built from ``tmp_path`` would be refused.
When the temp root resolves under one of those tiers, use a private directory under /tmp instead.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

_TIER_ROOTS = (Path("/srv/scratch"), Path("/srv/storage"))
_PRIVATE_DIR: pytest.StashKey[Path] = pytest.StashKey()


def _under_tier(path: Path) -> bool:
    """Return whether the resolved path lies under a Hemma storage tier."""
    resolved = path.resolve()
    return any(resolved.is_relative_to(root) for root in _TIER_ROOTS)


def pytest_configure(config: pytest.Config) -> None:
    """Point pytest's base temp at a private /tmp directory when TMPDIR is a storage tier."""
    if config.option.basetemp is not None or not _under_tier(Path(tempfile.gettempdir())):
        return
    private = Path(tempfile.mkdtemp(prefix="sir-pytest-", dir="/tmp"))
    config.option.basetemp = str(private / "basetemp")
    config.stash[_PRIVATE_DIR] = private


def pytest_unconfigure(config: pytest.Config) -> None:
    """Remove the private temp directory created by ``pytest_configure``."""
    private = config.stash.get(_PRIVATE_DIR, None)
    if private is not None:
        shutil.rmtree(private, ignore_errors=True)
