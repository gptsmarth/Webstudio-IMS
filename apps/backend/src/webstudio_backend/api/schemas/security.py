"""Security and session API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ActiveSessionResponse(BaseModel):
    id: int
    device_label: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    remember_me: bool = False
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime
    is_current: bool = False


class LoginEventResponse(BaseModel):
    id: int
    username: str
    success: bool
    failure_reason: str | None = None
    ip_address: str | None = None
    device_label: str | None = None
    created_at: datetime


class LockedUserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    locked_until: datetime | None = None
    failed_login_count: int = 0


class SecurityDashboardResponse(BaseModel):
    session_timeout_minutes: int
    active_session_count: int
    active_sessions: list[dict]
    locked_users: list[dict]
    failed_logins_24h: int
    password_policy: dict
    recovery: dict
    recent_login_events: list[dict]
    jwt_access_token_ttl_minutes: int
    jwt_refresh_token_ttl_days: int
