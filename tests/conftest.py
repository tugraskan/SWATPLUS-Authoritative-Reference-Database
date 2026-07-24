"""Shared pytest fixtures and helpers.

Behavioral tests build small synthetic inputs; integration tests run against the
real committed authoritative repository (REPO_ROOT).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from swat_config import EXPECTED_FILES  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


def _stub_contents(name: str, tag: str, with_version: bool) -> str:
    """Minimal but plausible SWAT+ text-DB content, tagged by source."""
    header = (f"{name}: written by SWAT+ editor v2.3.3 on 2023-10-25 08:58 "
              f"for SWAT+ rev.60.5.7\n") if with_version else f"{name}: {tag}\n"
    return header + "name  col1  col2  description\n" + \
        f"rec_{tag}   1.0   2.0   from_{tag}\n"


def make_fake_checkout(tmp: Path, *, osu_only=(), with_version_for=()) -> Path:
    """Create a fake swat-model/swatplus checkout under ``tmp``.

    Every bootstrap-origin expected file is written to Ames_sub1 AND Osu_1hru
    (tagged so the picked source is identifiable), except names in ``osu_only``
    which are written to Osu_1hru only.  ``with_version_for`` names get a real
    version header; others get a plain title (to test null-version handling).
    """
    checkout = tmp / "swatplus"
    ames = checkout / "refdata" / "Ames_sub1"
    osu = checkout / "refdata" / "Osu_1hru"
    ames.mkdir(parents=True)
    osu.mkdir(parents=True)
    for spec in EXPECTED_FILES:
        if spec["origin"] != "bootstrap":
            continue
        name = spec["name"]
        wv = name in with_version_for
        (osu / name).write_text(_stub_contents(name, "osu", wv), encoding="utf-8")
        if name not in osu_only:
            (ames / name).write_text(_stub_contents(name, "ames", wv), encoding="utf-8")
    # a minimal file.cio in each
    for d in (ames, osu):
        (d / "file.cio").write_text(
            "file.cio: test\nhru_parm_db  plants.plt  fertilizer.frt  null\n",
            encoding="utf-8")
    return checkout


@pytest.fixture
def fake_checkout(tmp_path):
    return make_fake_checkout(tmp_path)
