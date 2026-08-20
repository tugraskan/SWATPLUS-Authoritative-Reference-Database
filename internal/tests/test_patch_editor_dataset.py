"""Exit-status behavior for the maintainer Editor patch tool."""

from __future__ import annotations

from types import SimpleNamespace

import patch_editor_dataset


def test_main_returns_nonzero_when_patch_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(patch_editor_dataset, "patch", lambda *args: False)

    result = patch_editor_dataset.main([
        "--editor-repo", str(tmp_path / "editor"),
        "--editor-sqlite", str(tmp_path / "input.sqlite"),
        "--output", str(tmp_path / "output.sqlite"),
        "--repo-root", str(tmp_path / "repo"),
    ])

    assert result == 1


def test_main_returns_zero_when_patch_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(patch_editor_dataset, "patch", lambda *args: True)

    result = patch_editor_dataset.main([
        "--editor-repo", str(tmp_path), "--editor-sqlite", str(tmp_path / "in"),
        "--output", str(tmp_path / "out"), "--repo-root", str(tmp_path),
    ])

    assert result == 0


def test_patch_failure_reaches_outer_transaction_and_returns_false(
        monkeypatch, tmp_path):
    class Atomic:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            self.exc_type = exc_type
            return False

    class Database:
        def __init__(self):
            self.transaction = Atomic()
            self.closed = False

        def init(self, path):
            self.path = path

        def atomic(self):
            return self.transaction

        def is_closed(self):
            return self.closed

        def close(self):
            self.closed = True

    database = Database()
    modules = SimpleNamespace(
        datasets_base=SimpleNamespace(db=database))
    monkeypatch.setattr(
        patch_editor_dataset, "_import_editor_modules", lambda path: modules)
    monkeypatch.setattr(
        patch_editor_dataset, "_apply_jobs", lambda modules, text_dir: (1, 1))

    editor_sqlite = tmp_path / "input.sqlite"
    editor_sqlite.write_bytes(b"original")
    repo_root = tmp_path / "repo"
    (repo_root / "database_files").mkdir(parents=True)
    output = tmp_path / "output.sqlite"

    result = patch_editor_dataset.patch(
        tmp_path / "editor", editor_sqlite, output, repo_root)

    assert result is False
    assert database.transaction.exc_type is patch_editor_dataset._PatchFailed
    assert database.closed is True
    assert output.read_bytes() == b"original"
