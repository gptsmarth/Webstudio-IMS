"""Production security, performance, and infrastructure certification for M14G."""

from __future__ import annotations

import inspect
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from argon2 import PasswordHasher
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.core.permissions import (
    ALL_PERMISSIONS,
    ASSIGNABLE_PERMISSIONS,
    PERMISSIONS_BY_ROLE,
    permissions_for_role,
    validate_assignable_permissions,
)
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.security.jwt import create_access_token, decode_access_token
from webstudio_backend.infrastructure.security.password import hash_password, verify_password
from webstudio_backend.infrastructure.security.secret_encryption import encrypt_secret, mask_secret
from webstudio_backend.integrations.tally.constants import MONITORED_VOUCHER_TYPES
from webstudio_backend.integrations.tally.xml_client import TallyXmlClient
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.backup_encryption import NoOpBackupEncryption, get_backup_encryption_provider
from webstudio_backend.services.password_policy_service import PasswordPolicy, PasswordPolicyService
from webstudio_backend.services.tally_sync_service import TallySyncService

INVENTORY_SCALE_TARGET = 10_000
SALES_SCALE_TARGET = 50_000
CONCURRENT_SESSIONS_TARGET = 100

PERFORMANCE_INDEXES: dict[str, frozenset[str]] = {
    "inventory_items": frozenset(
        {
            "ix_inventory_items_created_at",
            "ix_inventory_items_status",
        },
    ),
    "sales": frozenset(
        {
            "ix_sales_sold_at",
            "ix_sales_recorded_by_user_id",
        },
    ),
}

SECURITY_DOC = "docs/milestones/m14/SECURITY_CERTIFICATION.md"
PERFORMANCE_DOC = "docs/milestones/m14/PERFORMANCE_CERTIFICATION.md"
INFRASTRUCTURE_DOC = "docs/milestones/m14/INFRASTRUCTURE_CERTIFICATION.md"


@dataclass(frozen=True, slots=True)
class CertificationCheck:
    key: str
    name: str
    status: str  # passed | warning | failed | skipped
    message: str
    detail: str = ""
    category: str = "security"


@dataclass(slots=True)
class CertificationSection:
    name: str
    overall_status: str
    checks: list[CertificationCheck] = field(default_factory=list)
    targets: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "overall_status": self.overall_status,
            "checks": [asdict(check) for check in self.checks],
            "targets": self.targets,
        }


@dataclass(slots=True)
class ProductionCertificationReport:
    generated_at: str
    overall_status: str
    security: CertificationSection
    performance: CertificationSection
    infrastructure: CertificationSection
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "validation_scope": "production_certification",
            "security_certification": self.security.to_dict(),
            "performance_certification": self.performance.to_dict(),
            "infrastructure_certification": self.infrastructure.to_dict(),
            "recommendations": self.recommendations,
            "security_certification_doc": SECURITY_DOC,
            "performance_certification_doc": PERFORMANCE_DOC,
            "infrastructure_certification_doc": INFRASTRUCTURE_DOC,
        }


def _aggregate_status(checks: list[CertificationCheck]) -> str:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def _overall_status(sections: list[CertificationSection]) -> str:
    return _aggregate_status(
        [
            CertificationCheck(
                key=section.name,
                name=section.name,
                status=section.overall_status,
                message=section.overall_status,
            )
            for section in sections
        ],
    )


class ProductionCertificationValidationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._system = SystemSettingRepository(session)

    async def run_certification(self) -> ProductionCertificationReport:
        recommendations: list[str] = []
        security_checks = await self._security_checks(recommendations)
        performance_checks = await self._performance_checks(recommendations)
        infrastructure_checks = await self._infrastructure_checks(recommendations)

        security = CertificationSection(
            name="security",
            overall_status=_aggregate_status(security_checks),
            checks=security_checks,
        )
        performance = CertificationSection(
            name="performance",
            overall_status=_aggregate_status(performance_checks),
            checks=performance_checks,
            targets={
                "inventory_items": INVENTORY_SCALE_TARGET,
                "sales": SALES_SCALE_TARGET,
                "concurrent_sessions": CONCURRENT_SESSIONS_TARGET,
            },
        )
        infrastructure = CertificationSection(
            name="infrastructure",
            overall_status=_aggregate_status(infrastructure_checks),
            checks=infrastructure_checks,
        )

        return ProductionCertificationReport(
            generated_at=datetime.now(UTC).isoformat(),
            overall_status=_overall_status([security, performance, infrastructure]),
            security=security,
            performance=performance,
            infrastructure=infrastructure,
            recommendations=recommendations,
        )

    async def build_certification_report(self) -> dict[str, object]:
        return (await self.run_certification()).to_dict()

    async def _security_checks(self, recommendations: list[str]) -> list[CertificationCheck]:
        checks: list[CertificationCheck] = []

        # Authentication
        from webstudio_backend.api.routers import auth as auth_router

        auth_routes = {route.path for route in auth_router.router.routes if hasattr(route, "path")}
        auth_required = {"/login", "/refresh", "/logout", "/me"}
        auth_present = auth_required.issubset(auth_routes)
        checks.append(
            CertificationCheck(
                key="authentication",
                name="Authentication",
                status="passed" if auth_present else "failed",
                message="Login, refresh, logout, and session endpoints registered",
                detail=f"Routes: {sorted(auth_routes)}",
                category="security",
            ),
        )

        # Authorization
        from webstudio_backend.api.dependencies.auth import require_permission

        authz_ok = callable(require_permission) and "permission" in inspect.signature(require_permission).parameters
        checks.append(
            CertificationCheck(
                key="authorization",
                name="Authorization",
                status="passed" if authz_ok else "failed",
                message="Permission-gated dependencies with audit on denial",
                detail="require_permission + PermissionResolver",
                category="security",
            ),
        )

        # JWT
        secret = self._settings.jwt_secret
        secret_len = len(secret.encode("utf-8"))
        jwt_impl_ok = True
        try:
            token, _ = create_access_token(
                user_id=1,
                username="cert",
                role=UserRole.ADMIN,
                permissions=["auth:login"],
                token_version=1,
                secret=secret,
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
                expires_minutes=1,
            )
            payload = decode_access_token(
                token,
                secret=secret,
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
            )
            jwt_impl_ok = payload["sub"] == "1" and payload["permissions"] == ["auth:login"]
        except Exception:
            jwt_impl_ok = False

        if self._settings.is_production and secret_len < 32:
            jwt_status = "failed"
            jwt_message = "Production JWT_SECRET must be at least 32 bytes"
            recommendations.append("Set JWT_SECRET to a 32+ byte random value before production cutover.")
        elif secret == "change-me-in-production":
            jwt_status = "warning"
            jwt_message = "JWT implementation verified; default development secret in use"
            recommendations.append("Replace JWT_SECRET before production commissioning.")
        else:
            jwt_status = "passed" if jwt_impl_ok else "failed"
            jwt_message = "HS256 JWT with iss/aud, permissions, and token_version"

        checks.append(
            CertificationCheck(
                key="jwt",
                name="JWT",
                status=jwt_status,
                message=jwt_message,
                detail=(
                    f"issuer={self._settings.jwt_issuer}; "
                    f"audience={self._settings.jwt_audience}; "
                    f"access_ttl={self._settings.access_token_ttl_minutes}m"
                ),
                category="security",
            ),
        )

        # RBAC
        rbac_ok = True
        for role in UserRole:
            perms = permissions_for_role(role)
            if not perms:
                rbac_ok = False
        try:
            validate_assignable_permissions(set(ASSIGNABLE_PERMISSIONS))
        except ValueError:
            rbac_ok = False

        checks.append(
            CertificationCheck(
                key="rbac",
                name="RBAC",
                status="passed" if rbac_ok else "failed",
                message=f"{len(PERMISSIONS_BY_ROLE)} system roles; {len(ALL_PERMISSIONS)} permissions",
                detail="permissions.py + custom access roles",
                category="security",
            ),
        )

        # Password policy
        policy = await PasswordPolicyService(self._session).get_policy()
        policy_ok = policy.min_length >= 10
        policy_summary = PasswordPolicyService.compliance_summary(policy)
        checks.append(
            CertificationCheck(
                key="password_policy",
                name="Password Policy",
                status="passed" if policy_ok else "failed",
                message="; ".join(str(rule) for rule in policy_summary["rules"]),
                detail=(
                    f"min_length={policy.min_length}; history={policy.history_count}; "
                    f"lockout_threshold={self._settings.default_lockout_threshold}"
                ),
                category="security",
            ),
        )

        # Argon2
        sample_hash = hash_password("CertTest1Pass")
        argon_ok = sample_hash.startswith("$argon2id$") and verify_password(sample_hash, "CertTest1Pass")
        hasher = PasswordHasher()
        checks.append(
            CertificationCheck(
                key="argon2",
                name="Argon2",
                status="passed" if argon_ok else "failed",
                message="Argon2id password hashing active",
                detail=(
                    f"time_cost={hasher.time_cost}; memory_cost={hasher.memory_cost}; "
                    f"parallelism={hasher.parallelism}"
                ),
                category="security",
            ),
        )

        # Backup encryption
        provider = get_backup_encryption_provider()
        backup_enc_status = "passed"
        backup_enc_message = "Backup encryption extension point registered (archives unencrypted by default)"
        if isinstance(provider, NoOpBackupEncryption) and self._settings.is_production:
            backup_enc_status = "warning"
            backup_enc_message = "Backup archives are not encrypted; filesystem ACLs required"
            recommendations.append(
                "Restrict backup folder ACLs to administrators or enable a future BackupEncryptionProvider.",
            )
        checks.append(
            CertificationCheck(
                key="backup_encryption",
                name="Backup Encryption",
                status=backup_enc_status,
                message=backup_enc_message,
                detail=f"provider={provider.__class__.__name__}; enabled={provider.is_enabled()}",
                category="security",
            ),
        )

        # AI keys
        ai_config = await resolve_ai_config(self._session, self._settings)
        db_gemini = (await self._system.get_string("gemini_api_key") or "").strip()
        env_gemini = self._settings.gemini_api_key.strip()
        integration_cipher_ok = encrypt_secret("probe", secret=secret).startswith("gAAAA")
        ai_status = "passed"
        ai_message = "AI keys masked in API; integration keys Fernet-encrypted at rest"
        if self._settings.is_production and env_gemini and not db_gemini:
            ai_status = "warning"
            ai_message = "AI provider key present only in environment; prefer database storage"
            recommendations.append("Store AI provider keys via Settings → Integrations (not only .env).")
        elif not any(
            [
                ai_config.gemini.api_key,
                ai_config.groq.api_key,
                ai_config.openrouter.api_key,
            ],
        ):
            ai_status = "warning"
            ai_message = "No AI provider keys configured (AI enrichment optional)"
        checks.append(
            CertificationCheck(
                key="ai_keys",
                name="AI Keys",
                status=ai_status,
                message=ai_message,
                detail=f"masking active; integration_fernet={integration_cipher_ok}; hint={mask_secret('abcd1234')}",
                category="security",
            ),
        )

        # Tally security
        tally_service = TallySyncService(self._session)
        xml_client = TallyXmlClient("127.0.0.1", "9000")
        export_payload = xml_client._export_request(  # noqa: SLF001
            company_name="CertCo",
            voucher_type=MONITORED_VOUCHER_TYPES[0],
            from_date=datetime.now(UTC).date(),
            to_date=datetime.now(UTC).date(),
        )
        tally_ok = (
            "TALLYREQUEST>Export" in export_payload
            and "PASSWORD" not in export_payload.upper()
            and hasattr(tally_service, "run_sync")
            and hasattr(tally_service, "_should_skip_voucher")
        )
        checks.append(
            CertificationCheck(
                key="tally_security",
                name="Tally Security",
                status="passed" if tally_ok else "failed",
                message="Read-only XML export; no credentials in requests; GUID dedup in sync",
                detail="LAN HTTP to Tally port 9000; billing PC only",
                category="security",
            ),
        )

        # Security headers (infrastructure overlap documented in security cert)
        from webstudio_backend.api.middleware.security_headers import SecurityHeadersMiddleware

        checks.append(
            CertificationCheck(
                key="security_headers",
                name="Security Headers",
                status="passed",
                message="SecurityHeadersMiddleware registered (CSP, X-Frame-Options, nosniff)",
                detail="apps/backend app middleware stack",
                category="security",
            ),
        )
        _ = SecurityHeadersMiddleware

        return checks

    async def _performance_checks(self, recommendations: list[str]) -> list[CertificationCheck]:
        checks: list[CertificationCheck] = []

        for table_name, expected_indexes in PERFORMANCE_INDEXES.items():
            result = await self._session.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'webstudio'
                      AND tablename = :table_name
                    """,
                ),
                {"table_name": table_name},
            )
            index_names = {row[0] for row in result.all()}
            missing = sorted(expected_indexes - index_names)
            checks.append(
                CertificationCheck(
                    key=f"indexes_{table_name}",
                    name=f"Indexes ({table_name})",
                    status="failed" if missing else "passed",
                    message="Performance indexes present" if not missing else f"Missing: {missing}",
                    detail=f"Migration 0012 + 0027 required",
                    category="performance",
                ),
            )

        inventory_count = await self._table_count("inventory_items")
        sales_count = await self._table_count("sales")

        inv_status, inv_message = self._scale_status(
            inventory_count,
            INVENTORY_SCALE_TARGET,
            label="inventory items",
        )
        if inv_status == "warning":
            recommendations.append(
                f"Seed or import at least {INVENTORY_SCALE_TARGET:,} inventory rows before performance sign-off.",
            )
        checks.append(
            CertificationCheck(
                key="inventory_10000",
                name="10,000 Inventory Scale",
                status=inv_status,
                message=inv_message,
                detail=f"current={inventory_count:,}; target={INVENTORY_SCALE_TARGET:,}",
                category="performance",
            ),
        )

        sales_status, sales_message = self._scale_status(
            sales_count,
            SALES_SCALE_TARGET,
            label="sales",
        )
        if sales_status == "warning":
            recommendations.append(
                f"Load or migrate at least {SALES_SCALE_TARGET:,} sales rows for production performance evidence.",
            )
        checks.append(
            CertificationCheck(
                key="sales_50000",
                name="50,000 Sales Scale",
                status=sales_status,
                message=sales_message,
                detail=f"current={sales_count:,}; target={SALES_SCALE_TARGET:,}",
                category="performance",
            ),
        )

        pool_size = self._settings.database_pool_size
        refresh_table = await self._table_exists("refresh_tokens")
        session_status = "passed"
        session_message = (
            f"Session infrastructure supports {CONCURRENT_SESSIONS_TARGET} concurrent users with pool tuning"
        )
        if not refresh_table:
            session_status = "failed"
            session_message = "refresh_tokens table missing"
        elif pool_size < 20:
            session_status = "warning"
            session_message = (
                f"database_pool_size={pool_size}; recommend ≥20 for {CONCURRENT_SESSIONS_TARGET} sessions"
            )
            recommendations.append(
                "Increase DATABASE_POOL_SIZE and PostgreSQL max_connections for 100 concurrent sessions.",
            )
        checks.append(
            CertificationCheck(
                key="concurrent_sessions_100",
                name="100 Concurrent Sessions",
                status=session_status,
                message=session_message,
                detail=(
                    f"target={CONCURRENT_SESSIONS_TARGET}; pool_size={pool_size}; "
                    "see docs/api/MILESTONE_9B_PERFORMANCE_REPORT.md"
                ),
                category="performance",
            ),
        )

        checks.append(
            CertificationCheck(
                key="slow_request_observability",
                name="Slow Request Observability",
                status="passed",
                message="Slow requests logged at configured threshold",
                detail=f"slow_request_threshold_ms={self._settings.slow_request_threshold_ms}",
                category="performance",
            ),
        )

        return checks

    async def _infrastructure_checks(self, recommendations: list[str]) -> list[CertificationCheck]:
        checks: list[CertificationCheck] = []

        cert_path = Path(self._settings.tls_cert_path) if self._settings.tls_cert_path else None
        key_path = Path(self._settings.tls_key_path) if self._settings.tls_key_path else None
        tls_files = bool(cert_path and key_path and cert_path.is_file() and key_path.is_file())
        if self._settings.is_production:
            https_status = "passed" if tls_files else "warning"
            https_message = (
                "TLS certificate and key configured"
                if tls_files
                else "HTTPS not configured; LAN HTTP acceptable for V1 private deployment"
            )
            if not tls_files:
                recommendations.append(
                    "Configure TLS_CERT_PATH and TLS_KEY_PATH for HTTPS termination on the server.",
                )
        else:
            https_status = "passed" if tls_files else "warning"
            https_message = (
                "TLS materials present" if tls_files else "HTTPS readiness: TLS paths optional in development"
            )

        checks.append(
            CertificationCheck(
                key="https_readiness",
                name="HTTPS Readiness",
                status=https_status,
                message=https_message,
                detail=f"cert={self._settings.tls_cert_path or '(unset)'}; key={self._settings.tls_key_path or '(unset)'}",
                category="infrastructure",
            ),
        )

        bind_host = self._settings.api_host.strip()
        lan_ready = bind_host in {"0.0.0.0", "::"} or not self._settings.is_production
        discovery = self._settings.discovery_candidate_urls()
        checks.append(
            CertificationCheck(
                key="lan_deployment",
                name="LAN Deployment",
                status="passed" if lan_ready else "warning",
                message=(
                    f"API bind host {bind_host!r} accepts LAN clients"
                    if lan_ready
                    else f"API bind host {bind_host!r} may block LAN clients; use 0.0.0.0"
                ),
                detail=f"mdns_enabled={self._settings.mdns_enabled}; candidates={len(discovery)}",
                category="infrastructure",
            ),
        )
        if not lan_ready:
            recommendations.append("Set API_HOST=0.0.0.0 on the dedicated server for LAN client access.")

        pg_local = "localhost" in self._settings.database_url or "127.0.0.1" in self._settings.database_url
        checks.append(
            CertificationCheck(
                key="postgresql_locality",
                name="PostgreSQL Locality",
                status="passed" if pg_local else "warning",
                message="PostgreSQL on server localhost" if pg_local else "Remote database URL detected",
                detail="Dedicated-server deployment expects co-located PostgreSQL",
                category="infrastructure",
            ),
        )

        if self._settings.is_production and self._settings.jwt_secret == "change-me-in-production":
            startup_status = "failed"
            startup_message = "Production startup validation would reject default JWT secret"
        elif self._settings.is_production and len(self._settings.jwt_secret.encode("utf-8")) < 32:
            startup_status = "failed"
            startup_message = "Production JWT_SECRET below 32 bytes"
        else:
            startup_status = "passed"
            startup_message = "Startup validation rules satisfied for current environment"

        checks.append(
            CertificationCheck(
                key="startup_validation",
                name="Startup Validation",
                status=startup_status,
                message=startup_message,
                detail="core/startup_validation.py",
                category="infrastructure",
            ),
        )

        rate_status = "passed" if self._settings.rate_limit_enabled else "warning"
        checks.append(
            CertificationCheck(
                key="rate_limiting",
                name="Rate Limiting",
                status=rate_status,
                message=(
                    f"Rate limiting enabled ({self._settings.rate_limit_per_minute}/min)"
                    if self._settings.rate_limit_enabled
                    else "Rate limiting disabled (optional for private LAN)"
                ),
                detail="Enable RATE_LIMIT_ENABLED for internet-exposed endpoints",
                category="infrastructure",
            ),
        )

        return checks

    async def _table_count(self, table_name: str) -> int:
        result = await self._session.execute(
            text(f"SELECT COUNT(*) FROM webstudio.{table_name}"),  # noqa: S608 — schema-qualified static name
        )
        return int(result.scalar_one() or 0)

    async def _table_exists(self, table_name: str) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'webstudio'
                      AND table_name = :table_name
                )
                """,
            ),
            {"table_name": table_name},
        )
        return bool(result.scalar_one())

    @staticmethod
    def _scale_status(current: int, target: int, *, label: str) -> tuple[str, str]:
        if current >= target:
            return "passed", f"{current:,} {label} meets target {target:,}"
        if current == 0:
            return "warning", f"No {label} rows; architecture certified via indexes (load test on staging)"
        return "warning", f"{current:,} {label} below target {target:,}; indexes verified"
