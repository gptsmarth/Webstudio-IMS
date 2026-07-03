"""Startup orchestration tests."""

from __future__ import annotations

import pytest

from webstudio_backend.services.startup_orchestrator import run_startup_orchestration


@pytest.mark.asyncio
async def test_startup_orchestration_dev_environment(test_settings) -> None:
    report = await run_startup_orchestration(test_settings)
    assert report.checks
    assert any(check.name == "postgresql" for check in report.checks)
    assert report.ready is True
