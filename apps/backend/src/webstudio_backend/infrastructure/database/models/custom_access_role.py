"""Custom access role ORM entities."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.mixins import PrimaryKeyMixin, TimestampMixin


class CustomAccessRole(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "custom_access_roles"

    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_custom_access_roles_created_by"),
        nullable=True,
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.users.id", name="fk_custom_access_roles_updated_by"),
        nullable=True,
    )

    permissions: Mapped[list[CustomAccessRolePermission]] = relationship(
        "CustomAccessRolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CustomAccessRolePermission(Base):
    __tablename__ = "custom_access_role_permissions"

    role_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            f"{DATABASE_SCHEMA}.custom_access_roles.id",
            name="fk_custom_access_role_permissions_role",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    permission: Mapped[str] = mapped_column(String(64), primary_key=True)

    role: Mapped[CustomAccessRole] = relationship("CustomAccessRole", back_populates="permissions")
