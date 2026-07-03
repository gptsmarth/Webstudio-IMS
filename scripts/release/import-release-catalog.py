#!/usr/bin/env python3
"""Import on-disk release bundles into the enterprise release catalog (M13)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps/backend/src"))

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.enums import ReleaseChannel
from webstudio_backend.infrastructure.database.session import close_db, init_db, session_scope
from webstudio_backend.infrastructure.repositories.software_release_repository import (
    SoftwareReleaseRepository,
)
from webstudio_backend.services.release_catalog_loader import (
    default_release_channel_for_env,
    discover_bundle_dirs,
    release_from_bundle_dir,
)


async def _import_catalog(catalog_root: Path, channel: ReleaseChannel) -> int:
    await init_db(get_settings())
    imported = 0
    bundles = discover_bundle_dirs(catalog_root)
    async with session_scope() as session:
        repo = SoftwareReleaseRepository(session)
        for index, bundle_dir in enumerate(bundles):
            release = release_from_bundle_dir(
                bundle_dir,
                channel=channel,
                mark_current=index == len(bundles) - 1,
            )
            if release is None:
                continue
            if release.is_current:
                await repo.clear_current_flags(release.release_channel)
            await repo.upsert_release(release)
            imported += 1
        await session.commit()
    await close_db()
    return imported


def main() -> int:
    parser = argparse.ArgumentParser(description="Import release bundles into software_releases table")
    parser.add_argument(
        "--catalog-root",
        type=Path,
        default=REPO_ROOT / "release",
        help="Directory containing v{version} release bundles",
    )
    parser.add_argument(
        "--channel",
        choices=[item.value for item in ReleaseChannel],
        default="",
        help="Release channel override (defaults from APP_ENV)",
    )
    args = parser.parse_args()
    settings = get_settings()
    channel = (
        ReleaseChannel(args.channel)
        if args.channel
        else default_release_channel_for_env(settings.app_env)
    )
    count = asyncio.run(_import_catalog(args.catalog_root, channel))
    print(f"Imported {count} release bundle(s) into channel '{channel.value}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
