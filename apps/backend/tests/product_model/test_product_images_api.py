"""Product image proxy API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_product_image_proxy_requires_auth(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
) -> None:
    managed_url = "/assets/product-images/missing-test-image.jpg"

    unauth = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": managed_url},
    )
    assert unauth.status_code == 401

    authed = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": managed_url},
        headers=salesperson_headers,
    )
    assert authed.status_code == 404
