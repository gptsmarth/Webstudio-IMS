"""Managed-asset directory resolution tests.

Regression coverage for the production 503 where brand logo / product image
uploads failed because the repo-relative ``find_public_assets_dir`` does not
exist on the deployed server. ``resolve_managed_assets_dir`` must honour
``WEBSTUDIO_DATA_ROOT`` (set on office servers) and only fall back to the repo
public assets in dev/test.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import webstudio_backend.core.config as config
from webstudio_backend.services import web_image_scraper


def test_resolve_prefers_data_root_and_creates_dir(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(webstudio_data_root=str(tmp_path))
    )
    result = web_image_scraper.resolve_managed_assets_dir()
    assert result == tmp_path / "assets"
    assert result.is_dir()  # created on demand for the server


def test_resolve_data_root_no_create_does_not_make_dir(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(webstudio_data_root=str(tmp_path))
    )
    result = web_image_scraper.resolve_managed_assets_dir(create=False)
    assert result == tmp_path / "assets"
    assert not result.exists()  # serving must not create directories


def test_resolve_dev_fallback_to_repo_public_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(webstudio_data_root=""))
    # Dev/test: no data root configured -> same behaviour as before.
    assert (
        web_image_scraper.resolve_managed_assets_dir() == web_image_scraper.find_public_assets_dir()
    )


def test_find_managed_product_image_path_tolerates_extension_drift(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assets = tmp_path / "assets"
    product_images = assets / "product-images"
    product_images.mkdir(parents=True)
    stored = product_images / "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.jpg"
    stored.write_bytes(b"fake-jpeg")
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(webstudio_data_root=str(tmp_path))
    )
    monkeypatch.setattr(web_image_scraper, "find_public_assets_dir", lambda: None)

    found = web_image_scraper.find_managed_product_image_path(
        "product-images/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.webp"
    )
    assert found == stored.resolve()


def test_resolve_strips_quoted_data_root(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    quoted = f'"{tmp_path}"'
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(webstudio_data_root=quoted))
    result = web_image_scraper.resolve_managed_assets_dir(create=True)
    assert result == tmp_path / "assets"
    assert result.is_dir()
