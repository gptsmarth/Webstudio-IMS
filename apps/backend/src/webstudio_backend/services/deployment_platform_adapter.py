"""Platform-specific deployment operations — Windows service vs development."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

from loguru import logger

from webstudio_backend.core.config import Settings
from webstudio_backend.services.release_storage_paths import resolve_release_updates_root


class DeploymentPlatformAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    @property
    def install_root(self) -> Path:
        data_root = self._settings.webstudio_data_root.strip()
        if data_root:
            return Path(data_root).parent
        return Path.cwd()

    def snapshot_configuration(self, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        config_dest = dest_dir / "config-snapshot"
        config_dest.mkdir(parents=True, exist_ok=True)
        for env_name in (".env", "config/env/.env", "config/env/.env.local"):
            source = Path.cwd() / env_name
            if source.is_file():
                target = config_dest / source.name
                shutil.copy2(source, target)
        manifest = {
            "app_version": self._settings.app_version,
            "app_env": self._settings.app_env,
        }
        (config_dest / "deployment-config.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return config_dest

    def snapshot_service_configuration(self, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        service_dest = dest_dir / "service-config-snapshot"
        service_dest.mkdir(parents=True, exist_ok=True)
        if self.is_windows:
            script = (
                Path(__file__).resolve().parents[5] / "infra/windows/install-webstudio-service.ps1"
            )
            if script.is_file():
                shutil.copy2(script, service_dest / script.name)
        meta = {
            "platform": platform.system(),
            "service_name": os.getenv("WEBSTUDIO_SERVICE_NAME", "WEBSTUDIO Server"),
        }
        (service_dest / "service-meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return service_dest

    async def stop_backend_service(self) -> dict[str, str]:
        if self._settings.is_test:
            from webstudio_backend.services.shutdown_orchestrator import persist_scheduler_state

            await persist_scheduler_state()
            return {"mode": "dry_run", "success": "true"}
        from webstudio_backend.services.shutdown_orchestrator import run_graceful_shutdown

        report = await run_graceful_shutdown(
            wait_for_sync_seconds=float(self._settings.graceful_shutdown_seconds)
        )
        if self.is_windows:
            self._run_powershell("infra/windows/stop-business-day.ps1")
        return {"mode": "graceful_shutdown", "success": str(report.success)}

    def replace_backend(self, bundle_dir: Path) -> dict[str, str]:
        applied: list[str] = []
        bundle = Path(bundle_dir)
        if not bundle.is_dir():
            raise ValueError(f"Bundle directory not found: {bundle}")

        migrations_src = bundle / "migrations"
        if migrations_src.is_dir():
            migrations_dest = Path.cwd() / "database" / "migrations"
            versions_dest = migrations_dest / "versions"
            versions_dest.mkdir(parents=True, exist_ok=True)
            for item in migrations_src.iterdir():
                if item.is_file():
                    if item.name in {"env.py", "script.py.mako", "README.md", "alembic.ini"}:
                        target = migrations_dest / item.name
                    else:
                        target = versions_dest / item.name
                    shutil.copy2(item, target)
                    applied.append(str(target.relative_to(Path.cwd())))

        manifest_path = bundle / "version-manifest.json"
        if manifest_path.is_file():
            updates_root = resolve_release_updates_root(self._settings)
            active_link = updates_root / "active"
            if active_link.exists() or active_link.is_symlink():
                if active_link.is_symlink():
                    active_link.unlink()
                elif active_link.is_dir():
                    shutil.rmtree(active_link)
            try:
                os.symlink(bundle, active_link, target_is_directory=True)
                applied.append(str(active_link))
            except OSError:
                shutil.copytree(bundle, active_link, dirs_exist_ok=True)
                applied.append(str(active_link))

        return {"applied": applied, "bundle": str(bundle)}

    def run_alembic_migrations(self, bundle_dir: Path | None = None) -> dict[str, str]:
        alembic_ini = Path.cwd() / "database" / "migrations" / "alembic.ini"
        if bundle_dir:
            bundle_ini = Path(bundle_dir) / "migrations" / "alembic.ini"
            if bundle_ini.is_file():
                alembic_ini = bundle_ini
        if not alembic_ini.is_file():
            alembic_ini = Path.cwd() / "database" / "migrations" / "alembic.ini"
        cmd = [
            "python",
            "-m",
            "alembic",
            "-c",
            str(alembic_ini),
            "upgrade",
            "head",
        ]
        env = os.environ.copy()
        env.setdefault("DATABASE_URL", self._settings.database_url.replace("+asyncpg", ""))
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=alembic_ini.parent, env=env, check=False
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Alembic upgrade failed")
        return {"stdout": result.stdout[-2000:] if result.stdout else ""}

    async def restart_backend_service(self) -> dict[str, str]:
        from webstudio_backend.services.scheduler_runtime_service import reset_shutdown_flag

        reset_shutdown_flag()
        if self.is_windows and not self._settings.is_test:
            self._run_powershell("infra/windows/start-business-day.ps1")
        elif self.is_windows and self._settings.is_test:
            return {"mode": "dry_run", "platform": platform.system()}
        return {"mode": "restart", "platform": platform.system()}

    def restore_configuration(self, snapshot_path: str | Path) -> dict[str, str]:
        snapshot = Path(snapshot_path)
        if not snapshot.is_dir():
            return {"mode": "skipped", "reason": "snapshot_missing"}
        restored: list[str] = []
        for item in snapshot.iterdir():
            if item.name == "deployment-config.json":
                continue
            if item.name == ".env":
                target = Path.cwd() / ".env"
            else:
                target = Path.cwd() / "config" / "env" / item.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            restored.append(str(target))
        return {"restored": restored}

    def restore_service_configuration(self, snapshot_path: str | Path) -> dict[str, str]:
        snapshot = Path(snapshot_path)
        if not snapshot.is_dir():
            return {"mode": "skipped", "reason": "snapshot_missing"}
        return {"snapshot": str(snapshot), "platform": platform.system()}

    def _run_powershell(self, relative_script: str) -> None:
        script_path = Path(__file__).resolve().parents[5] / relative_script
        if not script_path.is_file():
            logger.warning("deployment.powershell_script_missing", script=str(script_path))
            return
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            check=False,
            capture_output=True,
            text=True,
        )
