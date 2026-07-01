"""Custom access role API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.models.custom_access_role import CustomAccessRole


class CustomAccessRoleSummary(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool = True
    permission_count: int = 0
    assigned_user_count: int = 0

    @classmethod
    def from_model(cls, role: CustomAccessRole, *, assigned_user_count: int = 0) -> CustomAccessRoleSummary:
        return cls(
            id=role.id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            permission_count=len(role.permissions),
            assigned_user_count=assigned_user_count,
        )


class CustomAccessRoleDetail(CustomAccessRoleSummary):
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, role: CustomAccessRole, *, assigned_user_count: int = 0) -> CustomAccessRoleDetail:
        base = CustomAccessRoleSummary.from_model(role, assigned_user_count=assigned_user_count)
        return cls(
            **base.model_dump(),
            permissions=sorted(entry.permission for entry in role.permissions),
            created_at=role.created_at,
            updated_at=role.updated_at,
        )


class PermissionCatalogResponse(BaseModel):
    permissions: list[str]


class CreateCustomAccessRoleRequest(BaseModel):
    name: str
    description: str | None = None
    permissions: list[str]


class UpdateCustomAccessRoleRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None


class AssignUserAccessRequest(BaseModel):
    access_type: str = Field(pattern="^(builtin|custom)$")
    role: str | None = None
    custom_role_id: int | None = None
