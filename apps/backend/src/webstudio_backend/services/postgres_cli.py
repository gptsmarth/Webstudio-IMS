"""Resolve pg_dump/psql executables for backup and restore."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError


def resolve_postgres_tool(name: str, *, postgres_bin: str = "") -> str:
    """Return an executable path for pg_dump or psql."""
    configured = postgres_bin.strip() or os.environ.get("POSTGRES_BIN", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_dir():
            exe_name = f"{name}.exe" if os.name == "nt" else name
            tool = candidate / exe_name
            if tool.is_file():
                return str(tool.resolve())
        elif candidate.is_file():
            return str(candidate.resolve())

    found = shutil.which(name)
    if found:
        return found

    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        postgres_root = Path(program_files) / "PostgreSQL"
        if postgres_root.is_dir():
            for version_dir in sorted(postgres_root.iterdir(), reverse=True):
                if not version_dir.is_dir():
                    continue
                tool = version_dir / "bin" / f"{name}.exe"
                if tool.is_file():
                    return str(tool.resolve())

    raise RepositoryError(
        f"PostgreSQL {name} was not found. Install PostgreSQL client tools or set "
        f"POSTGRES_BIN to the bin folder (for example "
        f"C:\\Program Files\\PostgreSQL\\18\\bin), then restart WEBSTUDIO Server."
    )
