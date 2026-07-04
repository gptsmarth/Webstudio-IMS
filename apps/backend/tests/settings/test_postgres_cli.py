"""Tests for PostgreSQL CLI resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from webstudio_backend.services.postgres_cli import resolve_postgres_tool


def test_resolve_postgres_tool_from_bin_dir(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe_name = "pg_dump.exe" if os.name == "nt" else "pg_dump"
    (bin_dir / exe_name).write_text("", encoding="utf-8")
    resolved = resolve_postgres_tool("pg_dump", postgres_bin=str(bin_dir))
    assert resolved.endswith(exe_name)


def test_resolve_postgres_tool_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("webstudio_backend.services.postgres_cli.os.name", "posix")
    with pytest.raises(Exception, match="PostgreSQL pg_dump was not found"):
        resolve_postgres_tool("pg_dump", postgres_bin="/does/not/exist")
