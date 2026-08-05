"""Shared pytest fixtures.

All tests run as integration tests against the real committed authoritative
repository (REPO_ROOT) — there is no synthetic swat-model/swatplus checkout to
build, since the one-time bootstrap/inventory/external-import scripts (and the
fixtures that fed them) were retired once the initial import was complete.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
