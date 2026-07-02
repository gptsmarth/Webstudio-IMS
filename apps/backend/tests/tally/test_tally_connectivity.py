"""Tally connectivity hardening tests."""

from __future__ import annotations

import pytest

from webstudio_backend.integrations.tally.connectivity import (
    TallyHostValidationError,
    map_exception_to_user_message,
    normalize_tally_host,
    validate_tally_port,
)


def test_normalize_accepts_ipv4() -> None:
    assert normalize_tally_host("192.168.1.25") == "192.168.1.25"


def test_normalize_accepts_hostname() -> None:
    assert normalize_tally_host("LENOVO-TALLY") == "lenovo-tally"


def test_normalize_accepts_mdns_local() -> None:
    assert normalize_tally_host("LENOVO-TALLY.local") == "lenovo-tally.local"


def test_normalize_rejects_invalid_host() -> None:
    with pytest.raises(TallyHostValidationError):
        normalize_tally_host("bad host name!")


def test_validate_port() -> None:
    assert validate_tally_port("9000") == "9000"
    with pytest.raises(TallyHostValidationError):
        validate_tally_port("70000")


def test_map_connection_refused_to_business_message() -> None:
    message = map_exception_to_user_message(OSError(111, "Connection refused"))
    assert "offline" in message.lower()


def test_map_timeout_to_business_message() -> None:
    message = map_exception_to_user_message(TimeoutError("timed out"))
    assert "timed out" in message.lower() or "timeout" in message.lower()
