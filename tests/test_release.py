"""Release-package contents & reproducibility (spec tests 24, 25)."""

from __future__ import annotations

import zipfile

import build_release_package as rel
from conftest import REPO_ROOT


def test_release_contents_match_spec(tmp_path):
    zip_path, dist = rel.build(REPO_ROOT, output_dir=str(tmp_path / "dist"))
    names = {p.name for p in (dist).rglob("*") if p.is_file()}
    for required in ("database_manifest.json", "database_changes.csv",
                     "bootstrap_sources.json", "compatibility_matrix.csv",
                     "external_sources.json", "DATABASE_VERSION",
                     "checksums.txt"):
        assert required in names, f"missing {required} from package"
    assert (dist / "database_files").is_dir()
    # no forbidden artifacts
    with zipfile.ZipFile(zip_path) as zf:
        entries = zf.namelist()
    assert not any(e.endswith((".sqlite", ".sqlite3", ".db", ".exe"))
                   for e in entries)
    zip_path.unlink()


def test_release_is_reproducible(tmp_path):
    z1, _ = rel.build(REPO_ROOT, output_dir=str(tmp_path / "d1"))
    b1 = z1.read_bytes()
    z1.unlink()
    z2, _ = rel.build(REPO_ROOT, output_dir=str(tmp_path / "d2"))
    b2 = z2.read_bytes()
    z2.unlink()
    # identical bytes -> identical checksum across rebuilds
    assert b1 == b2
