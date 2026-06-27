"""Application entrypoint."""

from __future__ import annotations

import uvicorn

from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "webstudio_backend.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        ssl_keyfile=settings.tls_key_path or None,
        ssl_certfile=settings.tls_cert_path or None,
    )


app = create_app()

if __name__ == "__main__":
    run()
