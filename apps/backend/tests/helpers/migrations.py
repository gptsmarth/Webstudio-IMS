"""Shared migration test helpers."""

from __future__ import annotations

ALEMBIC_HEAD = "0042_deployment_monitoring"


def assert_at_least_migration(current_revision: str | None, minimum_revision: str) -> None:
    """Assert the test database has applied migrations through at least `minimum_revision`."""
    assert current_revision is not None, "alembic_version is empty"
    assert (
        current_revision >= minimum_revision
    ), f"Expected migration >= {minimum_revision}, got {current_revision}"
